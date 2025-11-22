import logging

from smart_buddy.agents.router import RouterAgent
from smart_buddy.memory import MemoryBank


def test_trace_id_propagation(caplog, tmp_path):
    """Ensure a single `trace_id` is present in logs for Router, IntentAgent, MemoryBank and TaskAgent."""
    caplog.set_level(logging.DEBUG)
    db_path = tmp_path / "mem.db"
    mem = MemoryBank(str(db_path))
    router = RouterAgent(memory=mem)

    with caplog.at_level(logging.DEBUG):
        router.route("user1", "session1", "add task: buy milk")

    records = caplog.records

    # Find trace_id emitted by the router
    router_trace = None
    for r in records:
        if r.name.endswith("router") and getattr(r, "trace_id", None):
            router_trace = getattr(r, "trace_id")
            break

    assert router_trace is not None, "router did not emit a trace_id"

    # Modules that should have the same trace_id
    expected_modules = [
        "smart_buddy.agents.intent",
        "smart_buddy.memory",
        "smart_buddy.agents.task_agent",
    ]

    for mod in expected_modules:
        found = False
        for r in records:
            if r.name == mod and getattr(r, "trace_id", None) == router_trace:
                found = True
                break
        assert found, f"trace_id from router not found in logs for module {mod}"

    mem.close()
