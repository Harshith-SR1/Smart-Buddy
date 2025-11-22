"""Evaluation harness for Smart Buddy.

Provides scripted judge scenarios, scoring, dashboards, and regression gates
so we can prove product quality to competition judges and CI alike.
"""

from .harness import EvaluationHarness, ScenarioResult, EvalScenario

__all__ = ["EvaluationHarness", "ScenarioResult", "EvalScenario"]
