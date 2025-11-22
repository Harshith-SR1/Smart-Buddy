import os
import types
import tempfile

import requests

from smart_buddy.llm import LLM
from smart_buddy.memory import MemoryBank
from smart_buddy.agents.planner import PlannerAgent
from smart_buddy.agents.router import RouterAgent


def test_llm_timeout(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake")

    def raise_timeout(*args, **kwargs):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(requests, "post", raise_timeout)
    llm = LLM()
    r = llm.generate("Hello")
    assert isinstance(r, dict)
    assert r.get("error") == "request_exception"


def test_llm_http_error(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake")

    def fake_post(url, json=None, headers=None, params=None, timeout=None):
        resp = types.SimpleNamespace()

        def raise_for_status():
            raise requests.exceptions.HTTPError("bad status")

        resp.raise_for_status = raise_for_status
        resp.json = lambda: {"candidates": [{"content": "should not be returned"}]}
        return resp

    monkeypatch.setattr(requests, "post", fake_post)
    llm = LLM()
    r = llm.generate("Hi")
    assert isinstance(r, dict)
    assert r.get("error") == "request_exception"


def test_planner_resume_partial():
    fd, path = tempfile.mkstemp(prefix="sb_planner_", suffix=".db")
    os.close(fd)
    try:
        mem = MemoryBank(db_path=path)
        # create partial checkpoint
        mem.set(
            "planner", "u1", {"progress": 1, "steps": ["a", "b", "c"], "done": False}
        )
        planner = PlannerAgent(memory=mem)
        env = {"payload": {"user_id": "u1", "text": "continue"}}
        r = planner.handle(env)
        assert r["status"] == "resumed"
        cp = r.get("checkpoint")
        assert cp["progress"] == 1
    finally:
        try:
            mem.close()
        except Exception:
            pass
        os.remove(path)


def test_integration_router_memory_llm(monkeypatch):
    # Ensure LLM uses stub path
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    fd, path = tempfile.mkstemp(prefix="sb_int_", suffix=".db")
    os.close(fd)
    try:
        mem = MemoryBank(db_path=path)
        router = RouterAgent(memory=mem)
        # add a task
        r = router.route("u1", "s1", "Add task: finish unit tests")
        assert r["result"]["action"] == "added"
        # planner
        r2 = router.route("u1", "s1", "Create a short plan")
        assert r2["result"]["status"] in ("completed", "resumed")
        # emotion
        r3 = router.route("u2", "s2", "I feel down")
        assert "reply" in r3["result"]
        # verify task persisted
        tasks = mem.get("tasks", "u1")
        assert any(t["text"].startswith("finish unit tests") for t in tasks)
    finally:
        try:
            mem.close()
        except Exception:
            pass
        os.remove(path)
