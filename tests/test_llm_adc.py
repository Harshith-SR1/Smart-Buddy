import types

import requests

from smart_buddy.llm import LLM


def test_llm_adc_flow(monkeypatch, tmp_path):
    # simulate a service account file path
    fake_sa = tmp_path / "sa.json"
    fake_sa.write_text("{}")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(fake_sa))

    # mock service_account.Credentials.from_service_account_file
    class FakeCreds:
        def __init__(self):
            self.token = None

        def refresh(self, request):
            self.token = "fake-adc-token"

    def fake_from_file(path, scopes=None):
        return FakeCreds()

    # patch the module objects
    import importlib

    sa_mod = importlib.import_module("google.oauth2.service_account")
    monkeypatch.setattr(
        sa_mod,
        "Credentials",
        types.SimpleNamespace(from_service_account_file=fake_from_file),
    )

    # mock requests.post to capture Authorization header
    def fake_post(url, json=None, headers=None, params=None, timeout=None):
        assert headers is not None
        assert headers.get("Authorization") == "Bearer fake-adc-token"
        resp = types.SimpleNamespace()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        resp.json = lambda: {"candidates": [{"content": "adc reply"}]}
        return resp

    monkeypatch.setattr(requests, "post", fake_post)

    llm = LLM()
    r = llm.generate("hello adc")
    assert r["candidates"][0]["content"] == "adc reply"
