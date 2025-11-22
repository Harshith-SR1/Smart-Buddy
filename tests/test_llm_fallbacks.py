import types
import subprocess
import sys
from pathlib import Path

import requests

from smart_buddy.llm import LLM


def make_resp(json_obj):
    resp = types.SimpleNamespace()

    def raise_for_status():
        return None

    def json_fn():
        return json_obj

    resp.raise_for_status = raise_for_status
    resp.json = json_fn
    resp.status_code = 200
    return resp


def test_adc_priority(monkeypatch):
    # ADC present -> should use ADC path
    monkeypatch.setattr(LLM, "_get_adc_token", lambda self: "tok123")

    def fake_post(url, json=None, headers=None, params=None, timeout=None):
        return make_resp({"candidates": [{"content": "adc reply"}]})

    monkeypatch.setattr(requests, "post", fake_post)
    llm = LLM()
    r = llm.generate("hello")
    assert r.get("candidates")[0]["content"] == "adc reply"


def test_api_key_fallback(monkeypatch):
    # No ADC, but API key present
    monkeypatch.setattr(LLM, "_get_adc_token", lambda self: None)
    monkeypatch.setenv("GOOGLE_API_KEY", "fake")

    def fake_post(url, json=None, headers=None, params=None, timeout=None):
        return make_resp({"candidates": [{"content": "api reply"}]})

    monkeypatch.setattr(requests, "post", fake_post)
    llm = LLM()
    r = llm.generate("hi")
    assert r.get("candidates")[0]["content"] == "api reply"


def test_gpt4all_local_fallback(monkeypatch, tmp_path):
    # No ADC, no API key, but gpt4all binary + model present
    monkeypatch.setattr(LLM, "_get_adc_token", lambda self: None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    repo_root = Path.cwd()
    gpt4_dir = repo_root / "models" / "gpt4all"
    gpt4_dir.mkdir(parents=True, exist_ok=True)
    binary = gpt4_dir / "gpt4all.exe"
    model = gpt4_dir / "ggml-test.bin"
    binary.write_text("exe")
    model.write_text("model")

    class FakeProc:
        def __init__(self):
            pass

        def communicate(self, timeout=None):
            return ("local reply", "")

    def fake_popen(cmd, stdout=None, stderr=None, text=None):
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    llm = LLM()
    r = llm.generate("hello local")
    assert r.get("candidates")[0]["content"] == "local reply"

    # cleanup
    try:
        binary.unlink()
        model.unlink()
        gpt4_dir.rmdir()
    except Exception:
        pass


def test_transformers_fallback(monkeypatch):
    # force Popen to raise and no requests; provide transformers pipeline
    monkeypatch.setattr(LLM, "_get_adc_token", lambda self: None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    def raise_popen(*a, **k):
        raise RuntimeError("no binary")

    monkeypatch.setattr(subprocess, "Popen", raise_popen)

    class FakeGen:
        def __call__(self, prompt, max_length=None, num_return_sequences=None):
            return [{"generated_text": "transformer reply"}]

    # Insert a minimal transformers module into sys.modules
    fake_transformers = types.SimpleNamespace(pipeline=lambda *a, **k: FakeGen())
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    llm = LLM()
    r = llm.generate("use transformers")
    assert "transformer reply" in r.get("candidates")[0]["content"]


def test_stub_fallback(monkeypatch):
    # Ensure all upstream paths fail; expect stub reply
    monkeypatch.setattr(LLM, "_get_adc_token", lambda self: None)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    def raise_post(*args, **kwargs):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(requests, "post", raise_post)

    def raise_popen(*a, **k):
        raise RuntimeError("no binary")

    monkeypatch.setattr(subprocess, "Popen", raise_popen)

    # make transformers import fail by ensuring it's not present
    if "transformers" in sys.modules:
        del sys.modules["transformers"]

    llm = LLM()
    r = llm.generate("force stub")
    assert "[stub reply]" in r.get("candidates")[0]["content"]
