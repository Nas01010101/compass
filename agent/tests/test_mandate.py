from copilot import mandate


def test_live_voice_model_never_compiles_mandates(monkeypatch):
    monkeypatch.delenv("COPILOT_MANDATE_MODEL", raising=False)
    assert mandate.mandate_model("gemini-3.8-live") == mandate.DEFAULT_MODEL
    assert mandate.mandate_model("gemini-live-3.8-flash-native-audio") == mandate.DEFAULT_MODEL


def test_text_model_is_kept_and_override_wins(monkeypatch):
    monkeypatch.delenv("COPILOT_MANDATE_MODEL", raising=False)
    assert mandate.mandate_model("gemini-3.8-pro") == "gemini-3.8-pro"
    monkeypatch.setenv("COPILOT_MANDATE_MODEL", "gemini-3.8-pro")
    assert mandate.mandate_model("gemini-3.8-live") == "gemini-3.8-pro"


def test_regex_fallback_reads_nothing_from_a_spoken_sentence():
    # Why the voice path must reach Gemini: spoken emails and amounts have no "@" and no digits.
    m = mandate.fallback("pay my rent to jane at rent dot example, at most twelve hundred dollars")
    assert m["allowedRecipients"] is None and m["maxAmount"] is None
