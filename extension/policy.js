// Pure mandate enforcement. No chrome.* calls, so node:test can import it.
// A mandate is the JSON policy Gemini compiles from one sentence (see backend/compile.js).
// Checks are per recipient and per amount, not per site: an origin allowlist cannot tell
// "pay my landlord" from "pay the attacker" when both go through the same bank form.

export const RECIPIENT_KEY = /^(to|recipient|recipients|payee|beneficiary|iban|account|send_?to|destinataire|email_to)$/i;
export const AMOUNT_KEY = /(amount|total|price|montant|sum)/i;

export function host(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; }
}

export function hostAllowed(h, allowed) {
  return allowed.some((a) => h === a || h.endsWith("." + a));
}

export function parseAmount(v) {
  // "1 250,50 $" -> 1250.5 ; "$1,250.50" -> 1250.5
  let s = String(v).replace(/[^\d.,-]/g, "");
  if (/,\d{1,2}$/.test(s)) s = s.replace(/\./g, "").replace(",", ".");
  else s = s.replace(/,/g, "");
  const m = s.match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : NaN;
}

const low = (s) => String(s).trim().toLowerCase();

// action: { kind: "submit"|"purchase"|"send"|"request", url, fields: {name: value} }
export function check(policy, action, now = Date.now()) {
  if (!policy) return { allow: true, reasons: [] };
  const reasons = [];
  if (policy.expiresAt && now > policy.expiresAt) reasons.push("mandate expired");
  const h = host(action.url);
  if (policy.allowedSites?.length && !hostAllowed(h, policy.allowedSites)) {
    reasons.push(`site ${h} is outside the mandate`);
  }
  if (policy.allowedActions?.length && !policy.allowedActions.includes(action.kind)) {
    reasons.push(`action "${action.kind}" is not in the mandate`);
  }
  const recipients = policy.allowedRecipients?.map(low);
  for (const [k, v] of Object.entries(action.fields || {})) {
    if (v === "" || v == null) continue;
    if (recipients && RECIPIENT_KEY.test(k) && !recipients.includes(low(v))) {
      reasons.push(`recipient ${v} is not in the mandate`);
    }
    if (policy.maxAmount != null && AMOUNT_KEY.test(k)) {
      const a = parseAmount(v);
      if (a > policy.maxAmount) reasons.push(`amount ${a} exceeds the limit of ${policy.maxAmount}`);
    }
    if (policy.forbiddenData?.some((f) => low(k).includes(low(f)))) {
      reasons.push(`field "${k}" carries data the mandate forbids`);
    }
  }
  return { allow: reasons.length === 0, reasons };
}

// Infer the action kind from field names so "submit" on a payment form counts as "purchase".
export function classify(fields) {
  const keys = Object.keys(fields);
  if (keys.some((k) => /card|cvc|cvv|iban/i.test(k)) || keys.some((k) => AMOUNT_KEY.test(k))) return "purchase";
  if (keys.some((k) => RECIPIENT_KEY.test(k))) return "send";
  return "submit";
}
