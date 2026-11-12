// Runs in the page's own JS world so it can wrap fetch/XHR used by the page or by an agent.
// Only writes whose body names a recipient or an amount are held for a decision; analytics
// and ordinary traffic pass untouched.
(() => {
  const WATCH = /"?(to|recipient|payee|beneficiary|iban|account|amount|total|montant)"?\s*[:=]/i;
  let seq = 0;

  function bodyFields(body) {
    if (!body || typeof body !== "string" || !WATCH.test(body)) return null;
    try { return JSON.parse(body); } catch {}
    try { return Object.fromEntries(new URLSearchParams(body)); } catch {}
    return null;
  }

  function ask(url, fields) {
    const id = ++seq;
    return new Promise((resolve) => {
      const onMsg = (e) => {
        if (e.source === window && e.data?.mandat === "verdict" && e.data.id === id) {
          window.removeEventListener("message", onMsg);
          resolve(e.data.allow);
        }
      };
      window.addEventListener("message", onMsg);
      window.postMessage({ mandat: "ask", id, url: new URL(url, location.href).href, fields }, location.origin === "null" ? "*" : location.origin);
    });
  }

  const origFetch = window.fetch;
  window.fetch = async function (input, init = {}) {
    const method = (init.method || input?.method || "GET").toUpperCase();
    const fields = method !== "GET" ? bodyFields(init.body) : null;
    if (fields && !(await ask(input?.url || input, fields))) {
      return Promise.reject(new TypeError("Blocked by Compass: outside the user's mandate"));
    }
    return origFetch.apply(this, arguments);
  };

  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url) {
    this._mandat = { method: String(method).toUpperCase(), url };
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function (body) {
    const fields = this._mandat?.method !== "GET" ? bodyFields(body) : null;
    if (!fields) return origSend.apply(this, arguments);
    ask(this._mandat.url, fields).then((ok) => (ok ? origSend.call(this, body) : this.abort()));
  };
})();
