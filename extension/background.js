import { check, classify } from "./policy.js";

const DEFAULT_BACKEND = "http://localhost:8080";

async function state() {
  const s = await chrome.storage.local.get(["policy", "backend", "log"]);
  return { policy: s.policy || null, backend: s.backend || DEFAULT_BACKEND, log: s.log || [] };
}

async function record(entry) {
  const { log } = await state();
  log.unshift({ at: Date.now(), ...entry });
  await chrome.storage.local.set({ log: log.slice(0, 50) });
}

// Web Risk lookup through the backend; a failure never blocks, it only skips the check.
async function riskOf(url, backend) {
  try {
    const r = await fetch(`${backend}/risk?url=${encodeURIComponent(url)}`);
    return r.ok ? (await r.json()).threats || [] : [];
  } catch { return []; }
}

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  (async () => {
    const { policy, backend } = await state();
    if (msg.type === "check") {
      const action = { kind: classify(msg.fields), url: msg.url, fields: msg.fields };
      const v = check(policy, action);
      const threats = await riskOf(msg.url, backend);
      if (threats.length) { v.allow = false; v.reasons.push(`Google Web Risk flags this destination: ${threats.join(", ")}`); }
      await record({ type: v.allow ? "allowed" : "blocked", url: msg.url, kind: action.kind, reasons: v.reasons });
      reply(v);
    } else if (msg.type === "injection") {
      let verdicts = null;
      try {
        const r = await fetch(`${backend}/scan`, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({ url: msg.url, snippets: msg.snippets }),
        });
        verdicts = r.ok ? await r.json() : null;
      } catch {}
      await record({ type: "injection", url: msg.url, snippets: msg.snippets, verdicts });
      if (sender.tab?.id) chrome.action.setBadgeText({ tabId: sender.tab.id, text: String(msg.snippets.length) });
      reply({ ok: true });
    }
  })();
  return true; // async reply
});
