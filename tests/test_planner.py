import os
import tempfile

from smart_buddy.memory import MemoryBank
from smart_buddy.agents.planner import PlannerAgent


def test_planner_checkpoint_persistence():
    fd, path = tempfile.mkstemp(prefix="sb_planner_", suffix=".db")
    os.close(fd)
    try:
        mem = MemoryBank(db_path=path)
        planner = PlannerAgent(memory=mem)

        # first call should create and complete a plan
        env = {"payload": {"user_id": "u1", "text": "Create a plan"}}
        r = planner.handle(env)
        assert r["status"] == "completed"
        plan = r.get("plan")
        assert plan is not None
        assert plan.get("done") is True

        # new agent instance using same DB should resume
        mem2 = MemoryBank(db_path=path)
        planner2 = PlannerAgent(memory=mem2)
        r2 = planner2.handle(env)
        assert r2["status"] == "resumed"
        cp = r2.get("checkpoint")
        assert cp is not None
        assert cp.get("done") is True
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


def test_planner_records_plan_execute_reflect_cycle():
    fd, path = tempfile.mkstemp(prefix="sb_planner_cycle_", suffix=".db")
    os.close(fd)
    try:
        mem = MemoryBank(db_path=path)
        planner = PlannerAgent(memory=mem)
        env = {
            "payload": {
                "user_id": "alice",
                "session_id": "sess-1",
                "text": "Launch a six week AI safety bootcamp for teens with mentors",
            }
        }

        result = planner.handle(env)
        assert result["status"] == "completed"
        plan = result["plan"]
        assert len(plan["steps"]) == plan["depth"]["steps"]
        assert len(plan["execution_log"]) == len(plan["steps"])
        assert isinstance(plan["reflection"], str)
        assert plan["reflection"]
        timeline = plan.get("timeline", [])
        stages = {entry["stage"] for entry in timeline}
        assert {"depth", "plan", "execute", "reflect"}.issubset(stages)
    finally:
        try:
            mem.close()
        except Exception:
            pass
        os.remove(path)


def test_planner_intent_aware_depth():
    fd, path = tempfile.mkstemp(prefix="sb_planner_depth_", suffix=".db")
    os.close(fd)
    try:
        mem = MemoryBank(db_path=path)
        planner = PlannerAgent(memory=mem)
        env = {
            "payload": {
                "user_id": "depth-user",
                "text": "Create a detailed architecture roadmap",
                "intent": {"intent": "planner", "confidence": 0.9},
            }
        }
        result = planner.handle(env)
        steps = result["plan"]["depth"]["steps"]
        assert steps >= 5  # boosted due to high confidence + complex text
    finally:
        try:
            mem.close()
        except Exception:
            pass
        os.remove(path)


def test_planner_emits_tool_calls():
    fd, path = tempfile.mkstemp(prefix="sb_planner_tools_", suffix=".db")
    os.close(fd)
    try:
        mem = MemoryBank(db_path=path)
        planner = PlannerAgent(memory=mem)
        env = {
            "payload": {
                "user_id": "tool-user",
                "session_id": "sess-tool",
                "text": "Schedule onboarding workshops and research deployment guardrails",
            }
        }
        result = planner.handle(env)
        plan = result.get("plan")
        assert plan is not None
        tool_calls = plan.get("tool_calls", [])
        assert len(tool_calls) >= 1
        first_call = tool_calls[0]
        assert "tool" in first_call and first_call["tool"]
    finally:
        try:
            mem.close()
        except Exception:
            pass
        os.remove(path)
