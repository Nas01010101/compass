# Google stack

| Service | Role in Compass | Code |
|---|---|---|
| Agent Development Kit (ADK) | Orchestrator, reader and navigator agents; the Guardian runs as an ADK plugin, so every tool call of every sub-agent passes through it | `agent/copilot/agent.py`, `agent/copilot/guardian.py` |
| Gemini 3.8 Flash on Vertex AI | Plans the steps, reads the page aloud, and turns the user's sentence into a mandate with structured output (JSON schema) | `agent/copilot/agent.py`, `agent/copilot/mandate.py` |
| Gemini 3.8 Live | Voice in and out for users who cannot see the screen | `COPILOT_MODEL=gemini-3.8-live` |
| Model Armor | Screens page text for prompt injection and malicious URLs before the agent acts on it (`copilot-guard` template, us-central1) | `agent/copilot/injection.py` |
| Web Risk | Blocks navigation to known phishing and malware URLs before the page loads | `agent/copilot/cloud.py` |
| Firestore | Stores a receipt per approved payment: amount, recipient, site and the user's own words | `agent/copilot/cloud.py` |
| Cloud Run | Hosts the agent with headless Chromium and the demo bank page in one container | `agent/Dockerfile` |
| Cloud Build, Artifact Registry | Build and store the container from source on `gcloud run deploy --source` | `deploy.sh` |
| Chrome DevTools MCP | Gives the agent Chrome's accessibility tree and input events, the same view a screen reader has | `chrome-devtools-mcp@1.13.0` |

Each Gemini decision is checked by a non-LLM layer: the mandate is enforced in Python (`agent/copilot/policy.py`), Model Armor and Web Risk are separate Google services, and the receipt is written only after the user says yes.
