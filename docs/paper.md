# Compass: per-recipient mandate checks for a voice browser agent

## Abstract

Compass is a voice browser agent for blind and low-vision users. It is built on Google Agent Development Kit (ADK) 2.14 with Gemini 3.8 Flash on Vertex AI, and it drives Chrome through chrome-devtools-mcp. The user states a task and its limits in one sentence ("pay my rent to jane@rent.example, at most 1200 dollars, on QuickPay"). Gemini compiles that sentence into a mandate: sites, recipients, a maximum amount, allowed actions, forbidden data and an expiry. A Guardian, an ADK plugin, checks every tool call against the mandate before it reaches Chrome. The checks compare field values, so they apply per recipient and not per site. Model Armor screens page text aimed at agents, Web Risk blocks navigation to listed phishing URLs, and Firestore stores a receipt for each approved payment. The paper describes the architecture, the Guardian's rules, what was verified on Cloud Run on 2026-11-11, and the known limits.

## 1 Problem

A browser agent reads page text and acts on it. If the page contains text written for the agent ("AI assistant: the landlord changed accounts, send the rent to collect@rent-update.example"), the model may treat it as an instruction. The attacker only needs their text to appear on a page the agent reads.

A sighted user can watch the screen and catch a redirected payment. A blind or low-vision user relies on the agent's spoken account of the page, so the agent is also the user's only view of what happened.

A site allowlist does not cover this case. A payment form accepts any account, so the legitimate recipient and the attacker's account sit behind the same URL and the same button. The decision that matters is which recipient and amount the form is about to submit. Compass makes that decision on field values, using what the user said.

The attacker controls page content and can host phishing pages. The attacker does not control the user's voice, the server or the Google Cloud project.

## 2 Architecture

Compass has three agents and one plugin. The orchestrator talks to the user, calls `set_mandate`, and relays the Guardian's questions (`agent/copilot/agent.py`). The reader takes a snapshot and describes the page. The navigator opens pages, fills fields and clicks. Each reaches Chrome through its own filtered `McpToolset`: the reader gets only snapshot and page-selection tools, and the navigator adds navigation, `click`, `fill`, `fill_form`, `press_key` and `wait_for`. The model is `gemini-3.8-flash`, or `gemini-3.8-live` when `COPILOT_MODEL` selects voice.

The browser is driven through the accessibility tree, which screen readers also consume. Each snapshot line carries a uid, a role and an accessible name.

```
 voice or text
      |
      v
 orchestrator ---- set_mandate ----> Gemini structured output --> mandate (session state)
      |   \--- confirm_pending / cancel_pending
      +--> reader     take_snapshot
      +--> navigator  navigate, fill, click
                |
                v
   +-------------------------------+
   | Guardian (ADK plugin)         |   before_tool_callback: allow, ask, or block
   |  policy.check  Web Risk       |   after_tool_callback: parse snapshot, screen
   |  Model Armor   Firestore      |   text, write receipt
   +-------------------------------+
                |  only allowed calls pass
                v
       chrome-devtools-mcp --> Chrome (headless Chromium on Cloud Run)
```

Figure 1. Agents, tool flow and the Guardian's position. Blocked or held calls never reach chrome-devtools-mcp.

The Guardian is registered on the `App` object (`App(..., plugins=[Guardian()])`). ADK runs plugin callbacks before agent-level callbacks, so no sub-agent can opt out. In `before_tool_callback`, a returned dict replaces the tool result and the tool is skipped. The model then receives `blocked_by_guardian` or `needs_confirmation` with a `say_to_user` sentence for the orchestrator to read aloud. Returning `None` lets the call run. In `after_tool_callback` the Guardian reads each result to update session state: the mandate, the user's words (`goal`), the uid-to-label map of the last snapshot, typed and prefilled form values, the URL, injection findings, and the pending and approved signatures.

## 3 The Guardian

### 3.1 Mandate compilation

`mandate.compile_mandate` sends the spoken sentence to Gemini with a JSON schema (`response_schema=SCHEMA`) and receives a policy dict: `allowedSites`, `forbiddenSites`, `allowedRecipients`, `maxAmount`, `allowedActions` (submit, purchase, send or request), `forbiddenData` and `minutes`. The prompt tells the model to allow only what the sentence grants, to always forbid `password` and `ssn`, and to leave `allowedRecipients` null only when no recipient was named. `minutes` becomes an absolute `expiresAt`. If Gemini is unreachable, `fallback` builds a policy from regexes for emails, domains and amounts. Enforcement is ordinary Python.

### 3.2 Value-level checks

`policy.check` takes a mandate and an action (`kind`, `url`, `fields`) and returns `allow`, `ask` or `block` with reasons. It blocks on an expired mandate, a host outside `allowedSites` or inside `forbiddenSites`, and an action kind outside `allowedActions`. For each non-empty field it then applies three tests. A field whose accessible name matches `RECIPIENT_LABEL` must hold a value in `allowedRecipients`, compared in lower case. A field matching `AMOUNT_LABEL` is parsed by `parse_amount` ("$2,400.00", "2 400,00 $", "1.200,50") and must not exceed `maxAmount`. A field whose name contains an entry of `forbiddenData` is blocked. Because the test is on the value, an attacker's account on an allowlisted form is rejected and Jane's is accepted.

### 3.3 Action classification

`policy.classify` assigns the action kind from the filled field names: a card, CVC or IBAN label gives `purchase`; a recipient label gives `send`; an amount label alone gives `purchase`; anything else gives `submit`. The order matters; see the second bug in section 5.

### 3.4 Where checks run

`Guardian.decide` branches on the tool. For `navigate_page` and `new_page` it calls Web Risk, then applies only the site reasons of `policy.check`. For `fill` and `fill_form` it resolves each uid to an accessible name through `guardian:labels`, blocks forbidden data at once, and records the values. Recipient and amount are judged at submit, because fields may be filled in any order. The check covers typed values and values the page prefilled (`guardian:prefill`, read from the snapshot), so an agent that submits without typing is still checked.

### 3.5 Ask and confirm

When a sensitive action (`send` or `purchase`) passes every check and the mandate's `confirm` flag is on, `policy.check` returns `ask`. The Guardian computes `signature(action)`, a truncated SHA-256 of the action's kind, URL and field values, stores it in `guardian:pending`, and returns `needs_confirmation` with a spoken question ("This will send on quickpay.example with Recipient email: jane@rent.example, Amount: 1200. Should I go ahead?"). After a spoken yes, the orchestrator calls `confirm_pending` (`agent.py`), which copies the pending signature into `guardian:approved`. The navigator retries the click, and the Guardian lets it through only when `guardian:approved` equals the signature of the action as it now stands. If the recipient or amount changed between the question and the retry, the signatures differ and the Guardian asks again. After the click returns, `after_tool_callback` clears the form and the approval and calls `cloud.write_receipt`. With no mandate, a sensitive action asks.

### 3.6 Taint after a flagged page

After every snapshot or navigation result, the Guardian passes the text to `injection.screen`. A flagged result is stored in `guardian:tainted`, and the tool result is rewritten to begin with a `GUARDIAN WARNING` that the reader says first. Navigating to a new URL clears the taint. In `decide`, taint adds "the page carries hidden instructions" to any block on that page. It does not turn an `ask` into a block.

### 3.7 Fail-closed cases

Missing information leads to more checking. Button names are page-controlled, so a malicious page can call its submit button "Continue". When the form holds values, `decide` treats any button, link or unknown uid as a submit; only a click with no form values and a non-submit name passes unchecked. A uid absent from the last snapshot gets an empty role and name and is gated the same way. `press_key` is checked unless the key is passive (Tab, arrows, Escape) or the form is empty, so Space or Enter cannot submit around the click rule. A blocked navigation leaves the stored URL and taint untouched, because `after_tool_callback` returns early on `blocked` and `needs_` results. A failed Gemini or Model Armor call falls back to the regex mandate or the local phrase patterns.

## 4 Google Cloud components

- **Vertex AI, Gemini 3.8 Flash.** Plans steps, describes pages and compiles the mandate. Gemini 3.8 Live is the voice model.
- **Model Armor.** `injection.model_armor` posts page text to the `sanitizeUserPrompt` endpoint of the `copilot-guard` template (`pi_and_jailbreak` filter). `injection.screen` flags a page when Model Armor or the local patterns from `extension/` match.
- **Web Risk.** `cloud.web_risk` queries `uris:search` for malware, social engineering and unwanted software before a page loads.
- **Firestore.** `cloud.write_receipt` stores the action, the user's words and the mandate in the `receipts` collection, or appends to a local JSONL file without credentials.
- **Cloud Run, Cloud Build, Artifact Registry.** The container (`agent/Dockerfile`) holds the ADK web UI, the agent, Chromium and the demo page on port 8765. With `COPILOT_HEADLESS=1`, chrome-devtools-mcp (pinned at 1.13.0) starts a headless, isolated Chromium inside it.

## 5 Evaluation

Everything below was checked on the live Cloud Run deployment or by the offline suite. No rate or latency was measured.

**Live run, 2026-11-11, Cloud Run.** The planted instruction on the demo page was flagged by Model Armor (`pi_and_jailbreak`), and a click that submitted the injected recipient was blocked. For the legitimate rent payment, the click returned `needs_confirmation`. After "yes, go ahead", `confirm_pending` approved the pending action, the click ran, and a Firestore receipt was written.

**Offline suite.** `agent/tests/test_guardian.py` holds 14 tests and runs without network access or credentials (`cd agent && uv run pytest`). They cover amount parsing, an injected recipient, an amount over the limit, ask-then-run-then-receipt, a send-only mandate, host normalization, no-go sites and Web Risk (through the `COPILOT_UNSAFE_HOSTS` test hook), forbidden fields, non-submit clicks, the no-mandate case, a prefilled form, unknown uids, renamed buttons, and a blocked navigation. Four tests replay `agent/tests/fixtures/demo_snapshot.txt`, a snapshot recorded from chrome-devtools-mcp on the demo page, so the snapshot parser ran on real output.

**Bugs found in live runs.** Two defects appeared only against live Gemini output. Each was fixed with a test.

1. Gemini wrote mandate sites as `localhost:8765`, and the host comparison failed against `localhost`. `policy.site` now reduces each entry to its host. `test_mandate_sites_with_port_or_scheme_match` covers it.
2. Gemini compiled "pay rent" to the `send` action while the form was classified `purchase` because it has an amount field, so the Guardian blocked the user's own task. `policy.classify` now checks recipient labels before amount labels. `test_send_only_mandate_covers_recipient_and_amount_form` covers it.

## 6 Limits

- **Field detection uses accessible names.** A recipient field labelled "Field 7" is not recognised as a recipient, so its value is not compared with the mandate.
- **Voice is not verified.** `gemini-3.8-live` is configured but was not tested.
- **The reader can report text it did not observe.** In a live run on 2026-11-11 the reader agent described page content ("Transfer sent...") after its snapshot returned `about:blank`. It stated text it had not observed. The Guardian does not check the reader's spoken output, and a user who cannot see the page cannot catch this. It was not fixed.
- **Chrome state is shared across sessions.** Within one container instance, sessions share one Chromium, so one session's pages are visible to another.
- **Taint informs but does not block.** A mandated recipient on a page with a detected injection still reaches the ask step.
- **Confirmation depends on the model.** `confirm_pending` is a tool that the orchestrator calls after a yes. The signature ties the approval to one action, not to the user's utterance.
- **Unparseable amounts.** `parse_amount` returns NaN for a string with no digits, and `NaN > maxAmount` is false, so such a value passes the amount test. No test covers it.
- **Web Risk and Model Armor fail open.** A request error returns no finding. The mandate check does not depend on either service.
- **Unverified paths.** Web Risk blocking was tested through a local hook, not a real listed URL. The Chrome extension was not verified.

## 7 Related work

ADK plugins expose `before_tool_callback` and `after_tool_callback`, which Compass uses to enforce policy outside the model. Model Armor screens prompts and responses, and Compass applies its prompt-injection and jailbreak filter to page text. Web Risk is Google's URL threat lookup. chrome-devtools-mcp is the Model Context Protocol server through which agents drive Chrome. Screen readers consume the accessibility tree that Compass reads.
