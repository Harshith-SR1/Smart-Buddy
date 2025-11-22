"""CLI entry point for Smart Buddy evaluation harness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from smart_buddy.eval import EvaluationHarness


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Smart Buddy evaluation harness")
    parser.add_argument(
        "--report-dir",
        default="reports/eval",
        help="Directory for JSON + HTML outputs (default: reports/eval)",
    )
    parser.add_argument(
        "--min-planner",
        type=float,
        default=0.9,
        help="Regression gate for planner category (0-1)",
    )
    parser.add_argument(
        "--min-rag",
        type=float,
        default=0.8,
        help="Regression gate for rag category (0-1)",
    )
    parser.add_argument(
        "--min-safety",
        type=float,
        default=0.9,
        help="Regression gate for safety category (0-1)",
    )
    args = parser.parse_args()

    harness = EvaluationHarness(report_dir=args.report_dir)
    result = harness.run(
        regression_gates={
            "planner": args.min_planner,
            "rag": args.min_rag,
            "safety": args.min_safety,
        }
    )
    summary = result["summary"]
    print(json.dumps(summary, indent=2))
    status = summary.get("regression_check", {}).get("status", "pass")
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
