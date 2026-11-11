// Turns one sentence into an enforceable policy. Gemini writes the fields; this file
// normalises them so the extension never trusts free-form model output.
import { generateJson, Type } from "./gemini.js";

const ACTIONS = ["submit", "purchase", "send", "request"];

export const POLICY_SCHEMA = {
  type: Type.OBJECT,
  properties: {
    allowedSites: { type: Type.ARRAY, items: { type: Type.STRING }, description: "bare hostnames, e.g. quickpay.example" },
    allowedRecipients: { type: Type.ARRAY, items: { type: Type.STRING }, nullable: true,
      description: "emails, account ids or IBANs money or messages may go to; null if the user named none" },
    maxAmount: { type: Type.NUMBER, nullable: true },
    currency: { type: Type.STRING, nullable: true },
    allowedActions: { type: Type.ARRAY, items: { type: Type.STRING, enum: ACTIONS } },
    forbiddenData: { type: Type.ARRAY, items: { type: Type.STRING },
      description: "form field name fragments that must never be submitted, e.g. password, ssn, card" },
    expiresInMinutes: { type: Type.NUMBER, nullable: true },
    summary: { type: Type.STRING, description: "one sentence restating the mandate for the user" },
  },
  required: ["allowedSites", "allowedRecipients", "maxAmount", "allowedActions", "forbiddenData", "summary"],
};

const PROMPT = (mandate, currentUrl) => `You convert a user's instruction to their browser AI agent into a least-privilege policy.
Grant only what the sentence asks for. When in doubt, deny.
- allowedSites: hostnames the agent may submit to. If the user says "this site", use the current page host.
- allowedRecipients: exact recipients named. If money or messages are mentioned but no recipient is named, return [] (nobody).
  Return null only when the task involves no recipient at all.
- allowedActions: submit (ordinary forms), purchase (payments, checkout), send (messages, transfers to a person), request (API writes).
- forbiddenData: always include "password" and "ssn" unless the user explicitly allows them.
- expiresInMinutes: default 30.
Current page: ${currentUrl || "unknown"}
User instruction: """${mandate}"""`;

const host = (s) => String(s).trim().toLowerCase().replace(/^https?:\/\//, "").replace(/^www\./, "").split(/[/:]/)[0];

export function normalise(raw, now = Date.now()) {
  const p = {
    allowedSites: [...new Set((raw.allowedSites || []).map(host).filter(Boolean))],
    allowedRecipients: raw.allowedRecipients == null ? null : raw.allowedRecipients.map((r) => String(r).trim()),
    maxAmount: Number.isFinite(raw.maxAmount) && raw.maxAmount >= 0 ? raw.maxAmount : null,
    currency: raw.currency || null,
    allowedActions: (raw.allowedActions || []).filter((a) => ACTIONS.includes(a)),
    forbiddenData: [...new Set([...(raw.forbiddenData || []), "password", "ssn"].map((f) => String(f).toLowerCase()))],
    summary: String(raw.summary || "").slice(0, 300),
  };
  const mins = Number.isFinite(raw.expiresInMinutes) && raw.expiresInMinutes > 0 ? Math.min(raw.expiresInMinutes, 24 * 60) : 30;
  p.expiresAt = now + mins * 60_000;
  return p;
}

export async function compile(mandate, currentUrl) {
  if (typeof mandate !== "string" || !mandate.trim() || mandate.length > 1000) throw new RangeError("mandate must be 1-1000 chars");
  return normalise(await generateJson(PROMPT(mandate, currentUrl), POLICY_SCHEMA));
}
