import os
import tempfile

from smart_buddy.memory import MemoryBank
from smart_buddy.agents.task_agent import TaskAgent


def test_task_agent_persistence():
    fd, path = tempfile.mkstemp(prefix="sb_mem_", suffix=".db")
    os.close(fd)
    try:
        mem = MemoryBank(db_path=path)
        ta = TaskAgent(memory=mem)
        env = {"payload": {"user_id": "u1", "text": "Add task: buy milk"}}
        r = ta.handle(env)
        assert r["action"] == "added"
        assert len(r["tasks"]) == 1
        # create new instance to ensure persistence
        mem2 = MemoryBank(db_path=path)
        ta2 = TaskAgent(memory=mem2)
        r2 = ta2.handle({"payload": {"user_id": "u1", "text": ""}})
        assert len(r2["tasks"]) == 1
    finally:
        try:
            mem.close()
        except Exception:
            pass
        try:
            mem2.close()
        except Exception:
            pass
        os.remove(path)
