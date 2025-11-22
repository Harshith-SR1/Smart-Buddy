import types

from smart_buddy.llm import LLM


def test_llm_stub(monkeypatch):
    # Ensure no API key in env
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    llm = LLM()
    r = llm.generate("Hello")
    assert isinstance(r, dict)
    assert "candidates" in r
    assert "[stub reply]" in r["candidates"][0]["content"]


def test_llm_api_key_path(monkeypatch):
    # Provide a fake API key
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")

    # Mock requests.post to simulate a successful API response
    import requests

    def fake_post(url, json=None, headers=None, params=None, timeout=None):
        resp = types.SimpleNamespace()

        def raise_for_status():
            return None

        def json_fn():
            return {"candidates": [{"content": "real reply"}]}

        resp.raise_for_status = raise_for_status
        resp.json = json_fn
        return resp

    monkeypatch.setattr(requests, "post", fake_post)

    llm = LLM()
    r = llm.generate("Hi")
    assert isinstance(r, dict)
    assert r.get("candidates")[0]["content"] == "real reply"
