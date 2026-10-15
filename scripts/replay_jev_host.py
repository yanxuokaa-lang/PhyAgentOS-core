"""Run a bounded no-motion decision pair in isolated Coordinator workspaces."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PhyAgentOS.agent.decision_host_replay import (  # noqa: E402
    HostReplayConfig,
    evaluate_host_run,
    run_host_replay,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", type=Path)
    source.add_argument("--evaluate-run", type=Path, help="Score existing pairs without network calls")
    args = parser.parse_args()
    if args.evaluate_run:
        summary = evaluate_host_run(args.evaluate_run.resolve(), repo_root=ROOT)
        print(summary.run_dir)
        return summary.exit_code
    path = args.config.resolve()
    config = HostReplayConfig.model_validate_json(path.read_text())
    for name in ("snapshot_dir", "output_root"):
        value = getattr(config, name)
        if not value.is_absolute():
            setattr(config, name, path.parent / value)
    root = asyncio.run(run_host_replay(config, repo_root=ROOT, config_path=path))
    print(root)
    report = json.loads((root / "report.json").read_text())
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
