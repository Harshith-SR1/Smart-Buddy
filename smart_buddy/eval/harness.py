"""Evaluation harness for Smart Buddy.

Runs scripted judge scenarios (>50) and emits JSON + HTML dashboards so we can
track readiness inside CI.
"""
from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional

from .scenarios import (
    build_context,
    build_scenarios,
    EvalContext,
    EvalScenario,
    ScenarioOutcome,
)


@dataclass
class ScenarioResult:
    id: str
    name: str
    category: str
    passed: bool
    score: float
    max_score: float
    details: Dict[str, Any]
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        # ensure floats are rounded for readability
        payload["latency_ms"] = round(self.latency_ms, 2)
        return payload


class EvaluationHarness:
    """Runs scripted scenarios, calculates scores, and saves dashboards."""

    def __init__(self, report_dir: str = "reports/eval") -> None:
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.context: EvalContext = build_context()
        self.scenarios: List[EvalScenario] = build_scenarios()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, regression_gates: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        results = self._execute_scenarios()
        summary = self._summarize(results)
        self._write_reports(summary, results)
        gate_report = self._check_regressions(summary, regression_gates or {})
        summary["regression_check"] = gate_report
        return {"summary": summary, "results": [r.to_dict() for r in results]}

    # ------------------------------------------------------------------
    # Scenario execution
    # ------------------------------------------------------------------
    def _execute_scenarios(self) -> List[ScenarioResult]:
        results: List[ScenarioResult] = []
        for scenario in self.scenarios:
            start = time.perf_counter()
            try:
                outcome: ScenarioOutcome = scenario.runner(self.context)
            except Exception as exc:  # pragma: no cover - defensive
                outcome = ScenarioOutcome(
                    passed=False,
                    score=0.0,
                    max_score=1.0,
                    details={"error": str(exc)},
                )
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(
                ScenarioResult(
                    id=scenario.id,
                    name=scenario.name,
                    category=scenario.category,
                    passed=outcome.passed,
                    score=outcome.score,
                    max_score=outcome.max_score,
                    details=outcome.details,
                    latency_ms=latency_ms,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def _summarize(self, results: List[ScenarioResult]) -> Dict[str, Any]:
        total_score = sum(r.score for r in results)
        max_score = sum(r.max_score for r in results) or 1.0
        passes = sum(1 for r in results if r.passed)
        pass_rate = passes / len(results)
        category_breakdown: Dict[str, Dict[str, Any]] = {}
        for r in results:
            bucket = category_breakdown.setdefault(
                r.category,
                {"passed": 0, "total": 0, "score": 0.0, "max_score": 0.0},
            )
            bucket["total"] += 1
            bucket["max_score"] += r.max_score
            bucket["score"] += r.score
            if r.passed:
                bucket["passed"] += 1
        for data in category_breakdown.values():
            total = data["total"] or 1
            data["pass_rate"] = data["passed"] / total
            data["score_pct"] = data["score"] / (data["max_score"] or 1)
        latencies = [r.latency_ms for r in results]
        summary = {
            "timestamp": time.time(),
            "scenario_count": len(results),
            "total_score": round(total_score, 2),
            "max_score": round(max_score, 2),
            "score_pct": round(total_score / max_score, 4),
            "passed": passes,
            "pass_rate": round(pass_rate, 4),
            "latency_ms": {
                "mean": round(statistics.mean(latencies), 2) if latencies else 0.0,
                "p95": round(_percentile(latencies, 0.95), 2) if latencies else 0.0,
                "max": round(max(latencies), 2) if latencies else 0.0,
            },
            "categories": category_breakdown,
        }
        return summary

    def _write_reports(self, summary: Dict[str, Any], results: List[ScenarioResult]) -> None:
        latest_json = self.report_dir / "latest.json"
        history_file = self.report_dir / "history.jsonl"
        dashboard_file = self.report_dir / "dashboard.html"

        latest_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        with history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary) + "\n")
        dashboard_file.write_text(
            _render_dashboard(summary, self._load_history()),
            encoding="utf-8",
        )
        results_file = self.report_dir / "scenario_results.json"
        results_file.write_text(
            json.dumps([r.to_dict() for r in results], indent=2),
            encoding="utf-8",
        )

    def _load_history(self) -> List[Dict[str, Any]]:
        history_file = self.report_dir / "history.jsonl"
        if not history_file.exists():
            return []
        history: List[Dict[str, Any]] = []
        with history_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    history.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return history

    def _check_regressions(self, summary: Dict[str, Any], gates: Dict[str, float]) -> Dict[str, Any]:
        if not gates:
            return {"status": "skipped", "details": {}}
        details: Dict[str, Any] = {}
        overall_status = "pass"
        for category, min_rate in gates.items():
            cat = summary["categories"].get(category)
            actual = cat.get("pass_rate", 0.0) if cat else 0.0
            ok = actual >= min_rate
            details[category] = {"actual": actual, "required": min_rate, "passed": ok}
            if not ok:
                overall_status = "fail"
        return {"status": overall_status, "details": details}


# ---------------------------------------------------------------------------
# Dashboard rendering helpers
# ---------------------------------------------------------------------------

def _render_dashboard(latest: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
    rows = []
    for category, data in latest.get("categories", {}).items():
        rows.append(
            f"<tr><td>{category}</td><td>{data['passed']} / {data['total']}</td>"
            f"<td>{data['pass_rate']*100:.1f}%</td><td>{data['score_pct']*100:.1f}%</td></tr>"
        )
    sparkline = _history_js(history)
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Smart Buddy Evaluation Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #101820; color: #f2f2f2; }}
    .card {{ background: #1c2533; border-radius: 10px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,.3); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,.08); text-align: left; }}
    th {{ text-transform: uppercase; font-size: 12px; letter-spacing: .08em; color: #7dd3fc; }}
    .score {{ font-size: 42px; font-weight: 700; }}
    canvas {{ width: 100%; height: 120px; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <div style=\"display:flex; justify-content:space-between; align-items:center;\">
      <div>
        <div class=\"score\">{latest['pass_rate']*100:.1f}%</div>
        <div>Total Score: {latest['total_score']} / {latest['max_score']}</div>
      </div>
      <div>
        <div>Latency p95: {latest['latency_ms']['p95']} ms</div>
        <div>Scenarios: {latest['scenario_count']}</div>
      </div>
    </div>
  </div>
  <div class=\"card\">
    <h3>Category Breakdown</h3>
    <table>
      <tr><th>Category</th><th>Pass</th><th>Pass Rate</th><th>Score</th></tr>
      {''.join(rows)}
    </table>
  </div>
  <div class=\"card\">
    <h3>Trend (last {len(history)} runs)</h3>
    <canvas id=\"historyChart\"></canvas>
  </div>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <script>{sparkline}</script>
</body>
</html>
"""


def _history_js(history: List[Dict[str, Any]]) -> str:
    if not history:
        return "document.getElementById('historyChart').remove();"
    labels = [time.strftime("%H:%M:%S", time.localtime(row.get("timestamp", 0))) for row in history[-20:]]
    data = [round(row.get("pass_rate", 0) * 100, 2) for row in history[-20:]]
    return (
        "const ctx = document.getElementById('historyChart').getContext('2d');"
        "new Chart(ctx, {type: 'line', data: {labels: "
        + json.dumps(labels)
        + ", datasets: [{label: 'Pass %', data: "
        + json.dumps(data)
        + ", borderColor: '#38bdf8', fill: false}]}, options: {scales: {y: {beginAtZero: true, max: 100}}}});"
    )


def _percentile(values: List[float], quantile: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = int((len(values) - 1) * quantile)
    return float(values[k])


__all__ = ["EvaluationHarness", "ScenarioResult"]
