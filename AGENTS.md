# Compass

Voice browser agent for blind and low-vision users, built on Google ADK with Gemini on Vertex AI. A Guardian plugin checks every tool call against the user's spoken mandate (recipient, amount, site, expiry) before it reaches Chrome.

Google Cloud project `copilot-gdg-11111801`, region `us-central1`. Cloud Run service `copilot` at https://copilot-embrfilgsa-uc.a.run.app.

Before working, read `docs/CONTEXT.md` (project state and decisions) and `TEAM.md` (your role, how to ask the owner). Work on a branch and open a PR. For a deploy, Google Cloud access, a decision or a live test, open an issue with the Request form (`gh issue create --label request`), then continue with what you can do without it.

## Layout

| Path | Contents |
|---|---|
| `agent/copilot/agent.py` | Orchestrator, reader and navigator agents, Chrome DevTools MCP wiring |
| `agent/copilot/guardian.py` | Guardian ADK plugin, runs before and after every tool call |
| `agent/copilot/policy.py` | Mandate checks per recipient, amount, site, forbidden fields |
| `agent/copilot/mandate.py` | Sentence to mandate with Gemini structured output |
| `agent/copilot/injection.py` | Model Armor screening and local injection patterns |
| `agent/copilot/cloud.py` | Web Risk and Firestore receipts |
| `agent/tests/` | pytest suite and the recorded snapshot in `fixtures/` |
| `agent/demo/`, `backend/demo/` | Demo bank pages with a planted instruction |
| `extension/`, `test/` | Chrome extension and its Node tests |
| `deploy.sh` | Owner script: enables APIs, creates Model Armor template and Firestore, deploys |
| `scripts/` | `grant-teammate.sh`, `teammate-setup.sh` |

## Setup

1. The project owner runs `scripts/grant-teammate.sh <your-google-email>`.
2. You run `scripts/teammate-setup.sh`. It checks gcloud, uv, node and Chrome, signs in, sets the project and the Model Armor endpoint override, writes `agent/copilot/.env` if absent, then runs `uv sync` and `uv run pytest -q`. It creates no cloud resources.

Do not run `deploy.sh` unless you are the owner; it creates cloud resources and changes IAM.

## Run locally

```bash
cd agent && uv run adk web                                  # http://localhost:8000, pick "copilot"
python3 -m http.server 8765 --directory agent/demo          # demo page at http://localhost:8765
```

Chrome 144+ with remote debugging on (`chrome://inspect/#remote-debugging`), or `COPILOT_OWN_CHROME=1` in `agent/copilot/.env` to start a separate Chrome. `COPILOT_MODEL=gemini-3.8-live` enables voice. `COPILOT_HEADLESS=1` and `CHROME_PATH` are set by the Dockerfile for Cloud Run.

## Test

```bash
cd agent && uv run pytest -q     # Guardian, no network
npm install && npm test          # extension policy; the first run needs the install
```

## Redeploy

```bash
gcloud run deploy copilot --source agent --region us-central1 --project copilot-gdg-11111801
```

Needs the deploy roles from `grant-teammate.sh`.

## Rules

- Every Guardian check in `policy.py` and `guardian.py` has a test in `agent/tests`. A new or changed check ships with its test.
- Never commit `agent/copilot/.env`, API keys, or service account files.
- Commit messages are one lowercase past-tense line, for example "added expiry check to policy".
