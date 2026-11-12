# Demo UI

`index.html` is a scripted replay of Compass in one page: the spoken mandate, the page the agent drives, the Guardian's verdict on each tool call, and the spoken replies as captions. Verdict text is the Guardian's own wording from `agent/copilot/guardian.py` and `agent/copilot/policy.py`. It calls no backend.

Open it in Chrome. Two scenarios: rent on QuickPay (planted instruction to pay another account) and headphones on the shop (hidden 150 CAD tip). Space plays or pauses, the right arrow steps one call. `#autoplay` plays the rent scenario on a fixed timeline in dark mode; `docs/video/compass-demo.mp4` is a recording of it with the voiceover in `docs/video/voiceover.md`.
