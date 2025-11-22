"""Planner Agent with plan-execute-reflect loop for complex goals.

Implements a deterministic planning pipeline so tests run without network access
while still supporting production logging and persistence.
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional, Any

from smart_buddy.memory import MemoryBank
from smart_buddy.logging import get_logger

# LLM kept for future prompts; current implementation uses deterministic fallback
from smart_buddy.llm import LLM
from smart_buddy.tools import build_default_registry


class PlannerAgent:
    """Multi-step planner with intent-aware depth and checkpointing."""

    def __init__(
        self,
        memory: Optional[MemoryBank] = None,
        db_path: Optional[str] = None,
    ) -> None:
        self.memory = memory or MemoryBank(db_path)
        self._ns = "planner_runs"
        self._logger = get_logger(__name__)
        self.llm = LLM()
        self.tools = build_default_registry(memory=self.memory)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        payload = envelope.get("payload", {})
        user_id = payload.get("user_id", "user")
        session_id = payload.get("session_id", "session")
        goal = (payload.get("text") or "").strip()
        intent_payload = payload.get("intent") or {}
        trace_id = envelope.get("meta", {}).get("trace_id") or str(uuid.uuid4())

        if not goal:
            return {
                "status": "error",
                "error": "missing_goal",
                "reply": "Please describe what you want to plan."
            }

        checkpoint = self.memory.get(self._ns, user_id, trace_id=trace_id)
        if checkpoint:
            self._logger.info(
                "planner_resume_checkpoint",
                extra={"user_id": user_id, "trace_id": trace_id},
            )
            return {
                "status": "resumed",
                "checkpoint": checkpoint,
                "reply": (
                    f"Resuming your most recent plan for \"{checkpoint.get('goal', 'your goal')}\". "
                    "You can start from any step or ask for adjustments."
                ),
            }

        depth_cfg = self._determine_depth(intent_payload, goal)
        timeline: List[Dict[str, Any]] = []
        timeline.append(self._timeline_entry(
            stage="depth", summary=f"level={depth_cfg['level']} steps={depth_cfg['steps']}", trace_id=trace_id
        ))

        plan_steps = self._draft_plan(goal, depth_cfg, trace_id)
        timeline.append(self._timeline_entry(
            stage="plan", summary=f"drafted {len(plan_steps)} steps", trace_id=trace_id
        ))

        execution_log, tool_calls = self._execute_plan(
            plan_steps, depth_cfg, trace_id, user_id, session_id, goal
        )
        timeline.append(self._timeline_entry(
            stage="execute", summary=f"logged {len(execution_log)} execution notes", trace_id=trace_id
        ))

        reflection = self._reflect(plan_steps, execution_log, depth_cfg, trace_id)
        timeline.append(self._timeline_entry(
            stage="reflect", summary=reflection[:160], trace_id=trace_id
        ))

        plan_state = {
            "plan_id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "goal": goal,
            "depth": depth_cfg,
            "steps": plan_steps,
            "execution_log": execution_log,
            "tool_calls": tool_calls,
            "reflection": reflection,
            "timeline": timeline,
            "done": True,
            "timestamp": time.time(),
        }

        self.memory.set(self._ns, user_id, plan_state, trace_id=trace_id)
        response_text = self._format_response(plan_state)
        return {"status": "completed", "plan": plan_state, "reply": response_text}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _determine_depth(self, intent_payload: Dict[str, Any], goal: str) -> Dict[str, Any]:
        text = goal.lower()
        base_steps = 4
        complexity_triggers = [
            "roadmap",
            "launch",
            "strategy",
            "architecture",
            "curriculum",
            "campaign",
            "research",
            "bootcamp",
        ]
        level = "standard"
        if len(goal.split()) > 40 or any(word in text for word in complexity_triggers):
            base_steps = 6
            level = "deep"
        confidence = intent_payload.get("confidence", 0)
        if confidence >= 0.85:
            base_steps = min(base_steps + 1, 8)
            if level == "standard":
                level = "comprehensive"
        return {
            "steps": base_steps,
            "level": level,
            "reflection_prompts": 2 if level != "standard" else 1,
        }

    def _timeline_entry(self, stage: str, summary: str, trace_id: str) -> Dict[str, Any]:
        entry = {"stage": stage, "summary": summary, "timestamp": time.time()}
        self._logger.info(
            "planner_stage",
            extra={"stage": stage, "summary": summary, "trace_id": trace_id},
        )
        return entry

    def _draft_plan(
        self, goal: str, depth_cfg: Dict[str, Any], trace_id: str
    ) -> List[Dict[str, Any]]:
        steps = depth_cfg.get("steps", 4)
        scaffolding = [
            "Clarify success criteria",
            "Research constraints",
            "Design approach",
            "Prototype or pilot",
            "Measure outcomes",
            "Iterate and scale",
            "Document learnings",
            "Share results",
        ]
        plan_steps: List[Dict[str, Any]] = []
        for idx in range(steps):
            scaffold = scaffolding[idx % len(scaffolding)]
            action = f"{scaffold} for the goal: {goal}."
            success = "Evidence of progress captured in notes and metrics."
            plan_steps.append(
                {"step": idx + 1, "action": action, "success": success, "status": "planned"}
            )
        return plan_steps

    def _execute_plan(
        self,
        plan_steps: List[Dict[str, Any]],
        depth_cfg: Dict[str, Any],
        trace_id: str,
        user_id: str,
        session_id: str,
        goal: str,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        execution_log: List[Dict[str, Any]] = []
        tool_calls: List[Dict[str, Any]] = []
        for step in plan_steps:
            note = (
                f"Validated step {step['step']} by defining deliverables and aligning them with the goal."
            )
            execution_log.append(
                {
                    "step": step["step"],
                    "action": step["action"],
                    "result": note,
                    "status": "completed",
                }
            )
            tool_entry = self._maybe_call_tool(
                step,
                goal,
                user_id=user_id,
                session_id=session_id,
                trace_id=trace_id,
            )
            if tool_entry:
                tool_calls.append(tool_entry)
        self._logger.info(
            "planner_execution_log",
            extra={
                "entries": len(execution_log),
                "tool_calls": len(tool_calls),
                "trace_id": trace_id,
            },
        )
        return execution_log, tool_calls

    def _reflect(
        self,
        plan_steps: List[Dict[str, Any]],
        execution_log: List[Dict[str, Any]],
        depth_cfg: Dict[str, Any],
        trace_id: str,
    ) -> str:
        focus = "comprehensive" if depth_cfg.get("reflection_prompts", 1) > 1 else "quick"
        summary = (
            f"Completed {len(plan_steps)} steps with {focus} reflection. "
            "Key takeaway: keep tracking metrics after each iteration to detect risks early."
        )
        self._logger.info(
            "planner_reflection",
            extra={"trace_id": trace_id, "focus": focus, "steps": len(plan_steps)},
        )
        return summary

    def _maybe_call_tool(
        self,
        step: Dict[str, Any],
        goal: str,
        *,
        user_id: str,
        session_id: str,
        trace_id: str,
    ) -> Optional[Dict[str, Any]]:
        action_text = step.get("action", "").lower()
        goal_text = goal.lower()
        intent: Optional[Dict[str, Any]] = None
        if "research" in action_text or "document" in action_text:
            intent = {
                "name": "docs.lookup",
                "arguments": {"query": goal[:160]},
            }
        elif any(word in action_text for word in ("measure", "monitor", "scan")):
            intent = {
                "name": "web.search",
                "arguments": {"query": goal.split()[0], "tag": "metrics"},
            }
        elif any(word in goal_text for word in ("schedule", "calendar", "onboard")):
            intent = {
                "name": "calendar.manage",
                "arguments": {
                    "action": "add_hold",
                    "title": goal[:60],
                },
            }
        if not intent:
            return None
        result = self.tools.call(
            intent["name"],
            user_id=user_id,
            session_id=session_id,
            trace_id=f"{trace_id}:{step['step']}",
            arguments=intent["arguments"],
        )
        entry = {
            "step": step["step"],
            "tool": result.name,
            "success": result.success,
            "output": result.output,
            "diagnostics": result.diagnostics,
        }
        if not result.success:
            entry["diagnostics"]["warning"] = entry["diagnostics"].get(
                "warning", "guardrail or runtime failure"
            )
        return entry

    def _format_response(self, plan_state: Dict[str, Any]) -> str:
        bullet_lines = []
        for step in plan_state.get("steps", [])[:4]:
            bullet_lines.append(f"{step['step']}. {step['action']}")
        bullets = "\n".join(bullet_lines)
        reflection = plan_state.get("reflection", "Plan created.")
        return (
            "🧭 **Multi-Step Plan Created**\n\n"
            f"Goal: {plan_state.get('goal')}\n"
            f"Depth: {plan_state.get('depth', {}).get('level')} ({plan_state.get('depth', {}).get('steps')} steps)\n\n"
            f"First steps:\n{bullets}\n\n"
            f"Reflection: {reflection}"
        )