// Isolated-world content script: intercepts form submissions, relays page-hook questions to
// the service worker, scans for hidden agent-directed instructions, and shows the verdict.
(() => {
  const H = globalThis.MandatHeuristics;

  function formFields(form) {
    const out = {};
    for (const el of form.elements) {
      if (!el.name || el.type === "hidden" && !el.value) continue;
      if ((el.type === "checkbox" || el.type === "radio") && !el.checked) continue;
      out[el.name] = el.value;
    }
    return out;
  }

  function banner(text, ok) {
    const b = document.createElement("div");
    b.textContent = (ok ? "Mandat: " : "Mandat blocked this: ") + text;
    b.setAttribute("role", "alert");
    b.style.cssText = `position:fixed;z-index:2147483647;left:16px;right:16px;bottom:16px;padding:14px 18px;
      border-radius:10px;font:600 15px system-ui;color:#fff;background:${ok ? "#1e6b3a" : "#b3261e"};
      box-shadow:0 6px 24px rgba(0,0,0,.3)`;
    (document.body || document.documentElement).appendChild(b);
    setTimeout(() => b.remove(), 7000);
  }

  const decide = (url, fields) =>
    chrome.runtime.sendMessage({ type: "check", url, fields }).catch(() => ({ allow: true, reasons: [] }));

  // Capture phase so we run before the page's own handlers. We cancel, ask, then resubmit.
  document.addEventListener("submit", async (e) => {
    const form = e.target;
    if (form.dataset.mandatOk) { delete form.dataset.mandatOk; return; }
    e.preventDefault();
    e.stopImmediatePropagation();
    const v = await decide(new URL(form.action || location.href, location.href).href, formFields(form));
    if (!v.allow) return banner(v.reasons.join(" · "), false);
    form.dataset.mandatOk = "1";
    form.requestSubmit ? form.requestSubmit() : form.submit();
  }, true);

  window.addEventListener("message", async (e) => {
    if (e.source !== window || e.data?.mandat !== "ask") return;
    const v = await decide(e.data.url, e.data.fields);
    if (!v.allow) banner(v.reasons.join(" · "), false);
    window.postMessage({ mandat: "verdict", id: e.data.id, allow: v.allow }, location.origin === "null" ? "*" : location.origin);
  });

  function scanHidden() {
    const bg = getComputedStyle(document.body).backgroundColor;
    const found = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n && found.length < 20; n = walker.nextNode()) {
      const text = n.textContent.trim();
      if (text.length < 15 || !H.looksLikeInjection(text)) continue;
      const el = n.parentElement;
      if (H.isHidden(getComputedStyle(el), el.getBoundingClientRect(), bg)) found.push(text.slice(0, 300));
    }
    if (found.length) {
      chrome.runtime.sendMessage({ type: "injection", url: location.href, snippets: found });
      banner(`${found.length} hidden instruction(s) aimed at AI agents on this page`, false);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scanHidden);
  else scanHidden();
})();
