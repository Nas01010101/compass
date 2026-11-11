"""Mandate checks, ported from extension/policy.js.

The agent sees fields by their accessible name ("Recipient email", "Montant"), not by the
HTML name attribute, so the recipient and amount patterns search the label instead of
matching it whole.
"""

from __future__ import annotations

import re
import time
from urllib.parse import urlparse

RECIPIENT_LABEL = re.compile(
    r"^to$|\b(recipient|recipients|payee|beneficiary|iban|account( number)?|send ?to|"
    r"destinataire|b[ée]n[ée]ficiaire|email ?to)\b",
    re.I,
)
AMOUNT_LABEL = re.compile(r"amount|total|price|montant|sum|somme", re.I)
CARD_LABEL = re.compile(r"card|carte|cvc|cvv|iban", re.I)
SENSITIVE_KINDS = {"purchase", "send"}


def host(url: str) -> str:
    try:
        h = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return h.removeprefix("www.")


def host_allowed(h: str, allowed: list[str]) -> bool:
    return any(h == a or h.endswith("." + a) for a in allowed)


def parse_amount(v) -> float:
    """Parses "$2,400.00", "2 400,00 $" and "1.200,50" the way a person reads them."""
    s = re.sub(r"[^\d.,-]", "", str(v))
    if re.search(r",\d{1,2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else float("nan")


def classify(fields: dict[str, str]) -> str:
    keys = list(fields)
    if any(CARD_LABEL.search(k) or AMOUNT_LABEL.search(k) for k in keys):
        return "purchase"
    if any(RECIPIENT_LABEL.search(k) for k in keys):
        return "send"
    return "submit"


def _low(s) -> str:
    return str(s).strip().lower()


def check(policy: dict | None, action: dict, now: float | None = None) -> dict:
    """Returns {"verdict": "allow"|"ask"|"block", "reasons": [...]}.

    "ask" means nothing in the mandate forbids the action but it moves money or data and the
    mandate asks for a spoken yes first (policy["confirm"], on by default).
    """
    if not policy:
        kind = action.get("kind", "submit")
        if kind in SENSITIVE_KINDS:
            return {"verdict": "ask", "reasons": [f"no mandate covers this {kind}"]}
        return {"verdict": "allow", "reasons": []}

    now = time.time() if now is None else now
    reasons: list[str] = []
    if policy.get("expiresAt") and now > policy["expiresAt"]:
        reasons.append("mandate expired")

    h = host(action.get("url", ""))
    sites = policy.get("allowedSites") or []
    if sites and not host_allowed(h, sites):
        reasons.append(f"site {h or '?'} is outside the mandate")
    for f in policy.get("forbiddenSites") or []:
        if host_allowed(h, [f]):
            reasons.append(f"site {h} is a no-go zone")

    kinds = policy.get("allowedActions") or []
    kind = action.get("kind", "submit")
    if kinds and kind not in kinds:
        reasons.append(f'action "{kind}" is not in the mandate')

    recips = policy.get("allowedRecipients")
    recips = None if recips is None else [_low(r) for r in recips]
    for k, v in (action.get("fields") or {}).items():
        if v in ("", None):
            continue
        if recips is not None and RECIPIENT_LABEL.search(k) and _low(v) not in recips:
            reasons.append(f"recipient {v} is not in the mandate")
        if policy.get("maxAmount") is not None and AMOUNT_LABEL.search(k):
            a = parse_amount(v)
            if a > policy["maxAmount"]:
                reasons.append(f"amount {a:g} exceeds the limit of {policy['maxAmount']:g}")
        if any(_low(f) in _low(k) for f in policy.get("forbiddenData") or []):
            reasons.append(f'field "{k}" carries data the mandate forbids')

    if reasons:
        return {"verdict": "block", "reasons": reasons}
    if kind in SENSITIVE_KINDS and policy.get("confirm", True):
        return {"verdict": "ask", "reasons": [f"{kind} within the mandate, needs a spoken yes"]}
    return {"verdict": "allow", "reasons": []}
