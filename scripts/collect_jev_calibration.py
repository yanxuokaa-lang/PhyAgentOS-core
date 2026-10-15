#!/usr/bin/env python3
"""Extract real calibration abstractions or collect bounded remote provider pairs."""
import argparse
import asyncio
from pathlib import Path

from PhyAgentOS.agent.decision_calibration import collect_calibration, extract_calibration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract")
    extract.add_argument("--database", type=Path, required=True)
    extract.add_argument("--since", required=True)
    extract.add_argument("--until", required=True)
    extract.add_argument("--session-prefix", required=True)
    extract.add_argument("--output-root", type=Path, required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--config", type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    repo_root = Path(__file__).resolve().parents[1]
    if command == "extract":
        run_dir = extract_calibration(**args, repo_root=repo_root)
    else:
        run_dir = asyncio.run(collect_calibration(args["config"], repo_root=repo_root))
    print(f"run_dir={run_dir}")
    print("active_eligible=false")


if __name__ == "__main__":
    main()
