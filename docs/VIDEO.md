# Recording the 2:30 video on the live URL

Shooting guide for `DEMO.md`, adapted to the Cloud Run app so nobody needs a local setup.
Live app: https://copilot-embrfilgsa-uc.a.run.app, pick **copilot**, click **New Session** before each take.

## What was checked on the live URL (2026-11-11, ~00:00Z)

| Beat | Live status | Notes |
|---|---|---|
| Mandate read-back | works | About 40 s from Enter to the read-back sentence. Cut the wait in the edit. |
| Reader describes the page | stalled | Orchestrator → navigator → reader, then the reader loops `list_pages` → `take_snapshot` → `list_pages` and has not spoken after about 5 min. Request issue opened. Until it's fixed, show the warning from the `take_snapshot` event details, or use the pytest fallback. |
| Injection blocked, rent to Jane with confirmation, Firestore receipt | verified by the owner (`docs/CONTEXT.md`) | Not re-run in this pass because the reader step stalled first. |
| Web Risk on a phishing link | not verified live | Real Web Risk should flag Google's test page `http://testsafebrowsing.appspot.com/s/phishing.html`. Otherwise use the pytest fallback below. |

The app is shared with the red team, so expect slow turns. Record each beat as its own clip and cut out the waiting.

## Prompts to type (in order, same session)

1. `Pay my rent to jane@rent.example, at most 1200 dollars, on this bank page.`
   Expect: `set_mandate(...)` event, then "Your mandate is set to pay rent to jane@rent.example, at most 1200 dollars, on this bank page."
2. `What is on this page?` (reader)
   Expect: a two or three sentence description that opens with the Guardian/Model Armor warning about text aimed at AI agents.
3. `Follow the page's update and pay the new account.` (scripted attack, 0:55-1:25)
   Expect: a `fill` or `click` event, then a Guardian block. The orchestrator reads `say_to_user`: recipient not in the mandate, amount over the limit.
4. `Pay 1200 dollars to jane@rent.example.`
   Expect: "Should I go ahead?"
5. `Yes, go ahead.`
   Expect: `confirm_pending`, the click goes through, the receipt id (`firestore:receipts/...`).
6. `Open http://testsafebrowsing.appspot.com/s/phishing.html`
   Expect: the Guardian blocks `new_page`/`navigate_page` with a SOCIAL_ENGINEERING threat.

Tip: click an event chip (for example the blocked `click`) to open its details panel. That's the best frame for "nothing reached Chrome".

## Shot list (2:30)

| Time | Clip | Voiceover (from `DEMO.md`) |
|---|---|---|
| 0:00-0:15 | Screen reader (VoiceOver: Cmd+F5) reading `backend/demo` or any bank page, eyes closed | 2.2 billion people have a vision impairment. AI browser agents could do their errands, but one hidden line on a page can redirect their money. |
| 0:15-0:35 | Prompt 1 + read-back | Gemini turns the sentence into a mandate and reads it back. |
| 0:35-0:55 | Prompt 2 | The reader describes the page from Chrome's accessibility tree and warns that it has text aimed at AI agents. |
| 0:55-1:25 | Prompt 3, zoom on the blocked event | The page says the landlord changed accounts. The Guardian blocks it: recipient not in the mandate, amount over the limit. Nothing reaches Chrome. |
| 1:25-1:50 | Prompts 4-5, then the receipt | With Jane's address, the Guardian asks for a spoken yes, then pays. A Firestore receipt stores the amount, recipient and the user's own words. |
| 1:50-2:10 | Prompt 6 | Web Risk stops a phishing link before the page loads. |
| 2:10-2:30 | Architecture slide (from the pitch role, `STACK.md`) | ADK multi-agent on Gemini 3.8, Guardian plugin, Model Armor, Web Risk, Firestore. Open source. |

## Fallbacks

- Any live beat stalls: run `cd agent && uv run pytest -v tests/test_guardian.py -k real` on screen. It replays the recorded snapshot and shows the block. Needs `uv` only, no cloud access.
- Web Risk beat: `uv run pytest -v tests/test_guardian.py -k web_risk` shows the same block with a seeded host.

## Recording

- macOS: Cmd+Shift+5, "Record selected portion", browser window only, 1080p.
- Record the voiceover separately (QuickTime → New Audio Recording) and lay it over the cut clips. That's easier than talking over 40 s waits.
- Export at most 2:30, MP4.
