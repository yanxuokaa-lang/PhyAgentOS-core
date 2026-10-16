#!/usr/bin/env python3
"""Audit a held-out dataset before spending paired JEV/System-2 requests."""

from __future__ import annotations

import argparse
from pathlib import Path

from PhyAgentOS.agent.decision_evaluation import audit_held_out_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    summary = audit_held_out_dataset(
        dataset_path=args.dataset,
        output_root=args.output_root,
        repo_root=Path(__file__).resolve().parents[1],
    )
    print(f"status={summary.status}")
    print(f"run_dir={summary.run_dir}")
    print(f"ready_for_pairing={str(summary.ready_for_pairing).lower()}")
    return summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
