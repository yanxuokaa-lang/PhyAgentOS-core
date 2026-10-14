#!/usr/bin/env python3
"""Evaluate recorded JEV Agent decisions against versioned independent labels."""

from __future__ import annotations

import argparse
from pathlib import Path

from PhyAgentOS.agent.decision_evaluation import run_decision_evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--max-cases",
        type=int,
        help="Smoke-test a deterministic prefix; partial runs are never active-eligible.",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    summary = run_decision_evaluation(
        config_path=args.config,
        repo_root=repo_root,
        max_cases=args.max_cases,
    )
    print(f"status={summary.status}")
    print(f"run_dir={summary.run_dir}")
    print(f"active_eligible={str(summary.active_eligible).lower()}")
    return summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
