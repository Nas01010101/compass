// Hidden-instruction detector, loaded as a classic content script (shared global scope)
// and imported by node:test. Text a human cannot see but an agent reads is the injection channel.
(function (root) {
  const AGENT_PHRASES = [
    /ignore (all |any )?(previous|prior|above) (instructions|prompts)/i,
    /\b(ai|llm|agent|assistant|gemini|model)\b[^.]{0,40}\b(must|should|now|instead)\b/i,
    /\b(send|transfer|pay|forward|email)\b[^.]{0,60}\b(to|vers|à)\b[^.]{0,40}(@|iban|account|wallet)/i,
    /system prompt|new instructions|you are now|disregard/i,
    /ignore(z)? (les|toutes les) instructions/i,
  ];

  function looksLikeInjection(text) {
    return AGENT_PHRASES.some((re) => re.test(text));
  }

  // style: a CSSStyleDeclaration-like object; rect: {width, height, top, left}
  function isHidden(style, rect, bg) {
    if (style.display === "none" || style.visibility === "hidden") return true;
    if (parseFloat(style.opacity) < 0.05 || parseFloat(style.fontSize) < 2) return true;
    if (rect && (rect.width < 2 || rect.height < 2 || rect.left < -1000 || rect.top < -1000)) return true;
    if (bg && style.color && style.color === bg) return true;
    return false;
  }

  root.MandatHeuristics = { looksLikeInjection, isHidden };
})(globalThis);
