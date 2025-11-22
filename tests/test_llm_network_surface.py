from smart_buddy.llm import LLM


def test_adc_500_surfaces(monkeypatch):
    # ADC token present
    monkeypatch.setattr(LLM, "_get_adc_token", lambda self: "tok")

    # Simulate _post_with_retries returning a request exception with status 500
    def fake_post_with_retries(self, endpoint, headers, payload, params=None):
        return {"error": "request_exception", "message": "server error", "status": 500}

    monkeypatch.setattr(LLM, "_post_with_retries", fake_post_with_retries)
    llm = LLM()
    res = llm.generate("hello")
    assert isinstance(res, dict)
    assert res.get("error") == "request_exception"


def test_adc_404_falls_back(monkeypatch):
    # ADC token present
    monkeypatch.setattr(LLM, "_get_adc_token", lambda self: "tok")

    def fake_post_with_retries(self, endpoint, headers, payload, params=None):
        return {"error": "request_exception", "message": "not found", "status": 404}

    monkeypatch.setattr(LLM, "_post_with_retries", fake_post_with_retries)

    # Ensure no API key and no binary/transformers available -> ultimately stub
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    llm = LLM()
    res = llm.generate("hello")
    # should fall through to local fallbacks and return candidates (stub)
    assert isinstance(res, dict)
    assert "candidates" in res
