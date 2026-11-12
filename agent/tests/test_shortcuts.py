"""Voice shortcuts: stop, wait, continue, repeat, help, said at any moment of the conversation."""

import asyncio
import os
from types import SimpleNamespace

os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
os.environ.pop("WEB_RISK_API_KEY", None)

import pytest
from google.genai import types

from copilot import cloud, guardian, injection, shortcuts


@pytest.fixture(autouse=True)
def no_cloud(monkeypatch, tmp_path):
    monkeypatch.setattr(injection, "_token", lambda: None)
    monkeypatch.setattr(cloud, "_token", lambda: None)
    monkeypatch.setenv("COPILOT_RECEIPTS", str(tmp_path / "r.jsonl"))


def msg(text, role="user"):
    return types.Content(role=role, parts=[types.Part(text=text)])


def event(author, text, inv):
    return SimpleNamespace(author=author, invocation_id=inv, partial=False, content=msg(text, "user" if author == "user" else "model"))


def say(state, text, inv="inv-9", events=()):
    """Runs the plugin's before_agent_callback for one user message; returns the reply text or None."""
    ctx = SimpleNamespace(state=state, invocation_id=inv, user_content=msg(text), session=SimpleNamespace(events=list(events)))
    out = asyncio.run(shortcuts.Shortcuts().before_agent_callback(agent=SimpleNamespace(name="orchestrator"), callback_context=ctx))
    return shortcuts.content_text(out) if out else None


def tool(state, name, args=None):
    ctx = SimpleNamespace(state=state)
    return asyncio.run(shortcuts.Shortcuts().before_tool_callback(tool=SimpleNamespace(name=name), tool_args=args or {}, tool_context=ctx))


@pytest.mark.parametrize("text,command", [
    ("Stop!", "stop"), ("Arrête-toi s’il te plaît", "stop"), ("ARRÊTE TOUT !", "stop"),
    ("ok, attends une seconde", "pause"), ("Hey Compass, wait a minute", "pause"),
    ("Continue.", "resume"), ("continuez s'il vous plaît", "resume"),
    ("Répète", "repeat"), ("Pardon ?", "repeat"), ("help", "help"), ("Qu'est-ce que je peux dire ?", "help"),
])
def test_shortcut_phrases_match(text, command):
    assert shortcuts.match(text)[0] == command


@pytest.mark.parametrize("text", ["Stop the payment to Jane", "Pay my rent", "wait until the page loads then click pay", "", None])
def test_sentences_are_not_shortcuts(text):
    assert shortcuts.match(text) is None


def test_stop_halts_actions_and_drops_the_pending_yes():
    state = {"guardian:pending": {"sig": "abc"}, "guardian:approved": "abc"}
    reply = say(state, "Arrête !")
    assert reply.startswith("J'arrête")
    assert state["shortcut:paused"] == "stop"
    assert state["guardian:pending"] is None and state["guardian:approved"] is None
    for name in ("click", "fill", "fill_form", "press_key", "navigate_page", "new_page"):
        assert tool(state, name)["status"] == "paused_by_user"
    assert tool(state, "take_snapshot") is None  # reading the page stays allowed


def test_wait_keeps_the_pending_yes_and_continue_lets_the_agent_resume():
    state = {"guardian:pending": {"sig": "abc"}}
    assert "Paused" in say(state, "wait", inv="1")
    assert state["guardian:pending"] == {"sig": "abc"}
    assert tool(state, "click")["say_to_user"].startswith("I'm paused")
    assert say(state, "continue", inv="2") is None  # no canned reply: the agent hears "continue"
    assert state["shortcut:paused"] is None
    assert tool(state, "click") is None


def test_paused_navigation_does_not_move_the_guardian():
    state = {"shortcut:paused": "pause", "guardian:url": "https://quickpay.example/transfer"}
    t, ctx = SimpleNamespace(name="navigate_page"), SimpleNamespace(state=state)
    args = {"url": "https://elsewhere.example"}
    result = asyncio.run(shortcuts.Shortcuts().before_tool_callback(tool=t, tool_args=args, tool_context=ctx))
    asyncio.run(guardian.Guardian().after_tool_callback(tool=t, tool_args=args, tool_context=ctx, result=result))
    assert state["guardian:url"] == "https://quickpay.example/transfer"


def test_repeat_says_the_last_reply_word_for_word():
    events = [
        event("user", "what is on this page", "1"),
        event("reader", "This is QuickPay. There is a form with recipient and amount.", "1"),
        event("user", "répète", "2"),
    ]
    assert say({}, "répète", inv="2", events=events) == "This is QuickPay. There is a form with recipient and amount."
    assert say({}, "repeat", inv="1", events=[]) == "I haven't said anything yet."


def test_ambiguous_word_answers_in_the_users_language():
    events = [event("user", "Payer mon loyer à Jane, au plus 1200 dollars", "1"), event("orchestrator", "D'accord.", "1")]
    assert say({}, "stop", inv="2", events=events).startswith("J'arrête")
    assert say({}, "stop", inv="2", events=[event("user", "Pay my rent to Jane", "1")]).startswith("Stopped")


def test_help_lists_the_commands_and_a_turn_is_handled_once():
    state = {}
    assert "« répète »" in say(state, "aide", inv="7")
    assert say(state, "aide", inv="7") is None  # the sub-agent of the same turn does not answer again


def test_non_shortcut_message_passes_through():
    state = {"shortcut:paused": "stop"}
    assert say(state, "pay my rent to Jane") is None
    assert state["shortcut:paused"] == "stop"
