"""Generate golden benchmark artifacts for CI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from smart_buddy.eval import EvaluationHarness

TARGET_CATEGORIES = ["planner", "rag", "safety", "tools"]


def _extract_metrics(summary: Dict) -> Dict:
    categories = summary.get("categories", {})
    metrics = {}
    for name in TARGET_CATEGORIES:
        data = categories.get(name, {})
        metrics[name] = {
            "pass_rate": round(data.get("pass_rate", 0.0) * 100, 2),
            "score_pct": round(data.get("score_pct", 0.0) * 100, 2),
            "passed": data.get("passed", 0),
            "total": data.get("total", 0),
        }
    metrics["overall"] = {
        "pass_rate": round(summary.get("pass_rate", 0.0) * 100, 2),
        "score_pct": round(summary.get("score_pct", 0.0) * 100, 2),
    }
    metrics["timestamp"] = summary.get("timestamp")
    return metrics


def main() -> None:
    harness = EvaluationHarness(report_dir="reports/eval")
    result = harness.run(
        regression_gates={
            "planner": 0.9,
            "rag": 0.8,
            "safety": 0.9,
        }
    )
    summary = result["summary"]
    metrics = _extract_metrics(summary)

    bench_dir = Path("reports/benchmarks")
    bench_dir.mkdir(parents=True, exist_ok=True)

    latest = bench_dir / "latest.json"
    history = bench_dir / "history.jsonl"
    markdown = bench_dir / "latest.md"

    latest.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(metrics) + "\n")

    markdown.write_text(_render_markdown(metrics), encoding="utf-8")

    print("Golden benchmarks updated:")
    print(json.dumps(metrics, indent=2))

    if summary.get("regression_check", {}).get("status") == "fail":
        raise SystemExit(1)


def _render_markdown(metrics: Dict) -> str:
    lines = ["| Category | Pass | Pass % | Score % |", "|---|---|---|---|"]
    for name in TARGET_CATEGORIES:
        data = metrics.get(name, {})
        lines.append(
            f"| {name.title()} | {data.get('passed', 0)}/{data.get('total', 0)} | {data.get('pass_rate', 0):.2f}% | {data.get('score_pct', 0):.2f}% |"
        )
    overall = metrics.get("overall", {})
    lines.append(
        f"| Overall | — | {overall.get('pass_rate', 0):.2f}% | {overall.get('score_pct', 0):.2f}% |"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
