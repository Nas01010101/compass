# Team

Deadline 19:45 EST (00:45Z). Deliverable: a video of at most 2:30, plus the repo.

| Member | Role | Needs Google Cloud access |
|---|---|---|
| Nas01010101 | Owner: approves requests, merges PRs, deploys, grants access | yes |
| pierreduh | Video: record the 2:30 demo from `DEMO.md` on the live URL | no |
| maryambani | Pitch: submission text and the architecture slide from `STACK.md` | no |
| will13cb | Red team: try new page injections on the live URL, report what gets through | no |
| benhoangquan | Voice: run `gemini-3.8-live` locally, report whether the spoken flow works | yes |
| Alex64-1149 | Second demo page: a shop checkout with a planted instruction, plus its Guardian test | no |

Swap roles among yourselves if that suits you better; edit this table in your PR.

## Set up your agent

1. Accept the GitHub invite, then `git clone https://github.com/Nas01010101/compass && cd compass`.
2. Open Claude Code, Codex or Gemini CLI in the repo and paste:

   > I'm `<github-handle>` on the Compass team. Read AGENTS.md, TEAM.md and docs/CONTEXT.md, then do my role. Work on a branch and open a PR when done. For anything that needs the owner (a deploy, Google Cloud access, a decision, a live test), open a GitHub issue with the "Request" form.

3. If your role needs Google Cloud, send your Google email to the owner, then run `scripts/teammate-setup.sh`.

## Asking the owner for something

- **Work done:** open a PR. Fill in "How to test". `main` accepts merges only after the owner approves.
- **Anything else** (test this live, deploy, access, a decision): open an issue with the **Request** form. The owner gets a notification and replies on the issue.
- Live app, no setup needed: https://copilot-embrfilgsa-uc.a.run.app (pick "copilot").
