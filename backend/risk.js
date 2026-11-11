// Google Cloud Web Risk Lookup API (uris.search). Uses WEB_RISK_API_KEY if set, else
// the Cloud Run service account through Application Default Credentials.
import { GoogleAuth } from "google-auth-library";

const TYPES = ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "SOCIAL_ENGINEERING_EXTENDED_COVERAGE"];
const cache = new Map();
let auth;

export async function risk(url) {
  const u = new URL(url); // throws on garbage
  if (!/^https?:$/.test(u.protocol)) return [];
  const key = u.origin + u.pathname;
  if (cache.has(key)) return cache.get(key);
  const qs = TYPES.map((t) => `threatTypes=${t}`).join("&") + `&uri=${encodeURIComponent(u.href)}`;
  const endpoint = `https://webrisk.googleapis.com/v1/uris:search?${qs}`;
  let data;
  if (process.env.WEB_RISK_API_KEY) {
    const r = await fetch(`${endpoint}&key=${process.env.WEB_RISK_API_KEY}`);
    if (!r.ok) throw new Error(`web risk ${r.status}`);
    data = await r.json();
  } else {
    auth ||= new GoogleAuth({ scopes: ["https://www.googleapis.com/auth/cloud-platform"] });
    data = (await (await auth.getClient()).request({ url: endpoint })).data;
  }
  const threats = data.threat?.threatTypes || [];
  cache.set(key, threats);
  return threats;
}
