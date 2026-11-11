const $ = (id) => document.getElementById(id);

function chips(p) {
  if (!p) return "<span class='mut'>No mandate: Mandat only watches.</span>";
  const c = [];
  (p.allowedSites || []).forEach((s) => c.push(`site: ${s}`));
  (p.allowedRecipients || []).forEach((r) => c.push(`to: ${r}`));
  if (p.maxAmount != null) c.push(`max: ${p.maxAmount} ${p.currency || ""}`);
  (p.allowedActions || []).forEach((a) => c.push(`may: ${a}`));
  (p.forbiddenData || []).forEach((f) => c.push(`never: ${f}`));
  if (p.expiresAt) c.push(`until ${new Date(p.expiresAt).toLocaleTimeString()}`);
  return c.map((t) => `<span class="chip">${t.replace(/</g, "&lt;")}</span>`).join("");
}

function logItem(e) {
  const what = e.type === "injection" ? `hidden instruction: “${e.snippets[0].slice(0, 80)}”`
    : `${e.kind} → ${new URL(e.url).hostname}${e.reasons?.length ? ": " + e.reasons.join("; ") : ""}`;
  const li = document.createElement("li");
  li.className = e.type;
  li.textContent = `${new Date(e.at).toLocaleTimeString()} ${e.type}: ${what}`;
  return li;
}

async function render() {
  const s = await chrome.storage.local.get(["policy", "backend", "log", "mandate"]);
  $("chips").innerHTML = chips(s.policy);
  $("backend").value = s.backend || "http://localhost:8080";
  $("mandate").value = s.mandate || "";
  $("log").replaceChildren(...(s.log || []).map(logItem));
}

$("compile").onclick = async () => {
  const mandate = $("mandate").value.trim();
  if (!mandate) return;
  const backend = $("backend").value.trim();
  $("status").textContent = "Gemini is compiling your mandate…";
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    const r = await fetch(`${backend}/compile`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ mandate, currentUrl: tab?.url || "" }),
    });
    if (!r.ok) throw new Error(await r.text());
    const policy = await r.json();
    await chrome.storage.local.set({ policy, mandate, backend });
    $("status").textContent = policy.summary || "Mandate set.";
  } catch (e) {
    $("status").textContent = `Could not reach the backend: ${e.message}`;
  }
  render();
};

$("clear").onclick = async () => {
  await chrome.storage.local.remove(["policy", "mandate", "log"]);
  $("status").textContent = "";
  render();
};

$("backend").onchange = () => chrome.storage.local.set({ backend: $("backend").value.trim() });
render();
