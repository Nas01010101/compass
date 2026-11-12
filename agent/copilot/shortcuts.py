"""Voice shortcuts: short commands the user can say at any moment, in French or English.

  stop      "stop", "arrête", "annule tout"         halts browser actions, drops the pending yes
  pause     "attends", "wait", "une seconde"        halts browser actions, keeps the pending yes
  resume    "continue", "reprends", "go on"         lifts stop or pause, the agent picks up again
  repeat    "répète", "say that again", "quoi ?"     says the last reply again, word for word
  help      "aide", "help", "raccourcis"             lists these commands

A typed or transcribed message that is only one of these phrases is answered by this plugin before
any model call, so it works at once and the same way every time. The Live voice model hears audio,
not text, so it gets the same actions as tools (stop_actions, pause_actions, resume_actions in
agent.py). Either way the pause is enforced here, in before_tool_callback: while paused, no tool
that acts in the browser runs. Reading the page stays allowed.

State keys:
  shortcut:paused   None, "stop" or "pause"
  shortcut:lang     "fr" or "en", the language of the last command
  shortcut:seen     invocation id already handled, so sub-agents of the same turn skip it
"""

from __future__ import annotations

import re
import unicodedata

from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

from .guardian import FILL_TOOLS, NAV_TOOLS, SUBMIT_TOOLS

ACTION_TOOLS = NAV_TOOLS | FILL_TOOLS | SUBMIT_TOOLS
MAX_WORDS = 6

# Phrases are written folded: lowercase, no accents, hyphens as spaces. "any" is both languages.
PHRASES = {
    "stop": {
        "fr": {"arrete", "arretez", "arrete toi", "arretez vous", "arrete tout", "stoppe", "halte",
               "annule tout", "on arrete", "stop stop"},
        "en": {"stop everything", "stop it", "cancel everything", "abort", "halt"},
        "any": {"stop"},
    },
    "pause": {
        "fr": {"attends", "attendez", "attends une seconde", "attends une minute", "attends un peu",
               "une seconde", "une minute", "un instant", "un moment", "minute"},
        "en": {"wait", "hold on", "hang on", "wait a second", "wait a minute", "one second",
               "one moment", "just a moment", "just a second"},
        "any": {"pause"},
    },
    "resume": {
        "fr": {"continuez", "reprends", "reprenez", "on reprend", "on continue", "tu peux continuer",
               "vous pouvez continuer"},
        "en": {"resume", "go on", "carry on", "keep going", "you can continue"},
        "any": {"continue"},
    },
    "repeat": {
        "fr": {"repete", "repetez", "repete ca", "tu peux repeter", "vous pouvez repeter", "quoi",
               "comment", "hein", "encore une fois"},
        "en": {"repeat", "repeat that", "say that again", "say again", "come again", "what did you say"},
        "any": {"pardon"},
    },
    "help": {
        "fr": {"aide", "aide moi", "raccourcis", "commandes", "quels sont les raccourcis",
               "qu'est ce que je peux dire"},
        "en": {"help", "shortcuts", "commands", "what can i say"},
        "any": set(),
    },
}
PREFIXES = ("ok ", "okay ", "d'accord ", "hey compass ", "compass ", "euh ", "um ", "uh ")
SUFFIXES = (" s'il te plait", " s'il vous plait", " please", " compass", " maintenant", " now")
RESUME_WORDS = re.compile(r"\b(continu\w*|repren\w*|resume|go on|carry on|keep going|vas y|allez y|go ahead)\b")
FRENCH = re.compile(r"\b(je|j'|mon|ma|mes|le|la|les|des|du|pour|payer|paye|paie|est|sur|cette|avec|oui|non|bonjour|merci)\b")

REPLIES = {
    "fr": {
        "stop": "J'arrête. Je ne fais plus rien dans le navigateur, et la confirmation en attente est annulée. Dites « continue » pour reprendre.",
        "pause": "Je fais une pause. Rien ne bouge. Dites « continue » quand vous êtes prêt.",
        "resume": "Je reprends.",
        "repeat_none": "Je n'ai encore rien dit à répéter.",
        "help": "Vous pouvez dire à tout moment : « stop » pour tout arrêter, « attends » pour une pause, « continue » pour reprendre, « répète » pour réentendre ma dernière phrase, et « aide » pour cette liste.",
        "paused_stop": "Je suis arrêté parce que vous avez dit stop. Dites « continue » pour reprendre.",
        "paused_pause": "Je suis en pause. Dites « continue » quand vous êtes prêt.",
    },
    "en": {
        "stop": "Stopped. I won't do anything else in the browser, and the pending confirmation is cancelled. Say continue to resume.",
        "pause": "Paused. Nothing will move. Say continue when you're ready.",
        "resume": "Resuming.",
        "repeat_none": "I haven't said anything yet.",
        "help": "At any time you can say: stop to halt everything, wait to pause, continue to resume, repeat to hear my last sentence again, and help for this list.",
        "paused_stop": "I'm stopped because you said stop. Say continue to resume.",
        "paused_pause": "I'm paused. Say continue when you're ready.",
    },
}


def fold(text: str) -> str:
    """Lowercase, no accents, no punctuation, hyphens as spaces, fillers and politeness removed."""
    s = str(text).replace("’", "'").replace("-", " ").replace("_", " ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^\w' ]+", " ", s)
    s = " ".join(s.split())
    changed = True
    while changed:
        changed = False
        for p in PREFIXES:
            if s.startswith(p):
                s, changed = s[len(p):], True
        for x in SUFFIXES:
            if s.endswith(x):
                s, changed = s[: -len(x)], True
    return s.strip()


def match(text: str | None) -> tuple[str, str] | None:
    """Returns (command, "fr"|"en"|"any") when the whole message is a shortcut, else None."""
    s = fold(text or "")
    if not s or len(s.split()) > MAX_WORDS:
        return None
    for command, by_lang in PHRASES.items():
        for lang, phrases in by_lang.items():
            if s in phrases:
                return command, lang
    return None


def is_french(text: str) -> bool:
    return len(FRENCH.findall(fold(text))) >= 1


def content_text(content) -> str:
    parts = getattr(content, "parts", None) or []
    return " ".join(p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False)).strip()


def apply(state, command: str, lang: str) -> str:
    """Changes state for a command and returns what to say. Shared by the plugin and the tools."""
    lang = lang if lang in REPLIES else "en"
    state["shortcut:lang"] = lang
    if command == "stop":
        state["shortcut:paused"] = "stop"
        state["guardian:pending"] = None
        state["guardian:approved"] = None
    elif command == "pause":
        state["shortcut:paused"] = "pause"
    elif command == "resume":
        state["shortcut:paused"] = None
    return REPLIES[lang].get(command, "")


def paused_result(state) -> dict:
    lang = state.get("shortcut:lang") if state.get("shortcut:lang") in REPLIES else "en"
    return {
        "status": "paused_by_user",
        "say_to_user": REPLIES[lang]["paused_" + (state.get("shortcut:paused") or "pause")],
    }


class Shortcuts(BasePlugin):
    def __init__(self, name: str = "shortcuts"):
        super().__init__(name=name)

    @staticmethod
    def _earlier(session, invocation_id: str, author_is_user: bool):
        for e in reversed(getattr(session, "events", None) or []):
            if getattr(e, "invocation_id", None) == invocation_id or getattr(e, "partial", False):
                continue
            if (getattr(e, "author", "") == "user") != author_is_user:
                continue
            text = content_text(getattr(e, "content", None))
            if text:
                yield text

    def _lang(self, state, session, invocation_id: str, lang: str) -> str:
        if lang != "any":
            return lang
        if state.get("shortcut:lang") in REPLIES:
            return state["shortcut:lang"]
        for text in self._earlier(session, invocation_id, author_is_user=True):
            if not match(text):
                return "fr" if is_french(text) else "en"
        return "en"

    async def before_agent_callback(self, *, agent, callback_context):
        state = callback_context.state
        inv = callback_context.invocation_id
        if state.get("shortcut:seen") == inv:
            return None
        hit = match(content_text(callback_context.user_content))
        if not hit:
            return None
        state["shortcut:seen"] = inv
        command, lang = hit
        session = getattr(callback_context, "session", None)
        lang = self._lang(state, session, inv, lang)
        if command == "resume":
            apply(state, command, lang)
            return None  # the agent hears "continue" and picks the task up again
        if command == "repeat":
            state["shortcut:lang"] = lang
            say = next(self._earlier(session, inv, author_is_user=False), None) or REPLIES[lang]["repeat_none"]
        else:
            say = apply(state, command, lang)
        return types.Content(role="model", parts=[types.Part(text=say)])

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        state = tool_context.state
        if state.get("shortcut:paused") and tool.name in ACTION_TOOLS:
            return paused_result(state)
        return None
