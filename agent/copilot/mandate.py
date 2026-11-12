"""Turns one spoken sentence into a mandate (policy dict) with Gemini structured output.

Falls back to a regex parse (emails, domains, amounts) when Gemini is not reachable, so the
Guardian always has a policy to enforce.
"""

from __future__ import annotations

import json
import os
import re
import time

from google.genai import types

DEFAULT_MODEL = "gemini-3.8-flash"


def mandate_model(agent_model: str | None = None) -> str:
    """Model for the one-shot structured-output call that compiles the mandate.

    Voice mode sets COPILOT_MODEL to a Live model, which is meant for the bidirectional Live API
    rather than generate_content with a JSON schema. If that call fails, compile_mandate drops to
    the regex fallback, and the fallback reads nothing from a spoken sentence ("jane at rent dot
    example, at most twelve hundred dollars"): no recipient, no limit. So a Live model never
    compiles mandates; COPILOT_MANDATE_MODEL overrides the choice.
    """
    override = os.getenv("COPILOT_MANDATE_MODEL")
    if override:
        return override
    agent_model = agent_model or os.getenv("COPILOT_MODEL", DEFAULT_MODEL)
    return DEFAULT_MODEL if re.search(r"live|native-audio", agent_model, re.I) else agent_model


MODEL = mandate_model()

SCHEMA = {
    "type": "object",
    "properties": {
        "allowedSites": {"type": "array", "items": {"type": "string"}},
        "forbiddenSites": {"type": "array", "items": {"type": "string"}},
        "allowedRecipients": {"type": "array", "items": {"type": "string"}, "nullable": True},
        "maxAmount": {"type": "number", "nullable": True},
        "allowedActions": {"type": "array", "items": {"type": "string", "enum": ["submit", "purchase", "send", "request"]}},
        "forbiddenData": {"type": "array", "items": {"type": "string"}},
        "minutes": {"type": "number"},
    },
    "required": ["allowedSites", "allowedActions", "forbiddenData"],
}

PROMPT = """Compile the user's instruction into a browsing mandate for an AI agent acting for them.
Only allow what the sentence grants. Domains without scheme or www. allowedRecipients is null
only if the user named no recipient. forbiddenData always includes password and ssn plus
anything the user says must not be shared. forbiddenSites lists places the user says to avoid.
minutes defaults to 30.
Instruction: """


def fallback(sentence: str) -> dict:
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", sentence)
    domains = [d for d in re.findall(r"\b(?:[\w-]+\.)+[a-z]{2,}\b", sentence, re.I) if not any(d in e for e in emails)]
    amounts = re.findall(r"\$?\s?(\d[\d,. ]*)\s?\$?", sentence)
    from .policy import parse_amount

    nums = [parse_amount(a) for a in amounts if parse_amount(a) == parse_amount(a)]
    return {
        "allowedSites": domains,
        "forbiddenSites": [],
        "allowedRecipients": emails or None,
        "maxAmount": max(nums) if nums else None,
        "allowedActions": ["submit", "purchase", "send"],
        "forbiddenData": ["password", "ssn"],
        "minutes": 30,
    }


def compile_mandate(sentence: str) -> dict:
    try:
        from google import genai

        client = genai.Client()
        r = client.models.generate_content(
            model=MODEL,
            contents=PROMPT + sentence,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=SCHEMA),
        )
        policy = json.loads(r.text)
        policy["source"] = "gemini"
    except Exception as e:  # no credentials, quota, network: keep a policy anyway
        policy = fallback(sentence)
        policy["source"] = f"fallback ({type(e).__name__})"
    policy["expiresAt"] = time.time() + 60 * float(policy.pop("minutes", 30) or 30)
    policy["text"] = sentence
    return policy
