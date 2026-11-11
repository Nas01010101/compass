# Compass

Live: https://copilot-embrfilgsa-uc.a.run.app (pick "copilot"). Google services used: [STACK.md](STACK.md).

A voice browser agent for blind and low-vision users. You say what you want done ("pay my rent to jane@rent.example, at most 1200 dollars, on QuickPay"); the agent reads the page from Chrome's accessibility tree, fills the form and clicks for you. A Guardian checks every action against what you said before it runs, so a hidden instruction on the page cannot redirect the money.

Built on Google ADK with Gemini on Vertex AI (Gemini Enterprise Agent Platform), Model Armor, Web Risk and Firestore.

## How it works

```
voice / text ──> orchestrator (gemini-3.8-flash, or gemini-3.8-live for voice)
                   ├─ set_mandate: Gemini structured output turns your sentence into a policy
                   ├─ reader:    take_snapshot -> spoken page summary
                   └─ navigator: click / fill / navigate via chrome-devtools-mcp
                                    │
                         Guardian plugin (before/after every tool call)
                           ├─ recipient, amount, site, no-go zones, forbidden fields, expiry
                           ├─ "ask": money or data moves only after a spoken yes
                           ├─ Model Armor + local patterns: flags page text aimed at AI agents
                           ├─ Web Risk: blocks navigation to known phishing and malware
                           └─ Firestore receipt: what was paid, to whom, and the user's reason
```

| Piece | File |
|---|---|
| Agents and tools | `agent/copilot/agent.py` |
| Guardian plugin | `agent/copilot/guardian.py` |
| Mandate checks (value level, per recipient) | `agent/copilot/policy.py` |
| Sentence to mandate | `agent/copilot/mandate.py` |
| Model Armor screening | `agent/copilot/injection.py` |
| Web Risk, receipts | `agent/copilot/cloud.py` |
| Chrome extension (form and fetch guard for any agent) | `extension/` |
| Demo bank page with a planted instruction | `backend/demo/index.html` |

The Guardian is an ADK plugin, so it runs before agent callbacks and no sub-agent can skip it. A blocked tool call never reaches Chrome; the model receives the Guardian's reasons and reads them to the user.

The checks are per recipient, not per site. An allowlist of sites lets "pay the attacker" through when the attacker's account sits behind the same bank form as the landlord's.

## Run it

Requirements: Chrome 144+, Node 20+, [uv](https://docs.astral.sh/uv/), a Google Cloud project.

```bash
gcloud auth login && gcloud auth application-default login
PROJECT=<gcp-project> ./deploy.sh local     # enables APIs, Model Armor template, Firestore, writes agent/copilot/.env
cd agent && uv run adk web                   # http://localhost:8000, pick "copilot"
```

In Chrome open `chrome://inspect/#remote-debugging` and turn remote debugging on; the agent attaches to your open browser (`--autoConnect`). Set `COPILOT_OWN_CHROME=1` to have it start a separate Chrome instead.

Voice: set `COPILOT_MODEL=gemini-3.8-live` in `agent/copilot/.env` and use the microphone button in `adk web`.

Demo page: `python3 -m http.server 8765 --directory backend/demo`, then ask the agent to pay the rent on `http://localhost:8765`.

Tests (no network): `cd agent && uv run pytest` (Guardian, including a snapshot recorded from chrome-devtools-mcp) and `npm test` (extension policy).

## Limits

- Field and button detection reads accessible names. A recipient field labelled "Field 7" is not recognised as a recipient.
- The Cloud Run deploy drives its own headless Chromium inside the container, so it can only reach pages that container can load (the bundled demo page at `http://localhost:8765` and public sites). Driving the user's own Chrome needs the local setup above.
- With no Google Cloud credentials, the mandate compiler falls back to a regex parse and injection screening falls back to local patterns.

## License

MIT
