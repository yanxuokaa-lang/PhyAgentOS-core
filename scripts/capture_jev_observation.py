#!/usr/bin/env python3
"""Capture one real no-motion scene and interpret it using only a local VLM."""

import argparse
import json
import sys
from pathlib import Path

from PhyAgentOS.agent.decision_snapshot import SnapshotConfig, capture_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    for name in ("adapter_root", "runtime_root", "runtime_profile", "worker_python", "output_root"):
        path = Path(raw[name]).expanduser()
        raw[name] = (config_path.parent / path).resolve() if not path.is_absolute() else path.resolve()
    if raw.get("worker_script") is not None:
        path = Path(raw["worker_script"]).expanduser()
        raw["worker_script"] = (config_path.parent / path).resolve() if not path.is_absolute() else path.resolve()
    config = SnapshotConfig.model_validate(raw)
    sys.path.insert(0, str(config.adapter_root / "src"))
    root = capture_snapshot(config, repo_root=Path(__file__).resolve().parents[1])
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    print(json.dumps({"run_dir": str(root), **summary}, ensure_ascii=False))
    return 0 if summary["status"] == "captured" else 2


if __name__ == "__main__":
    raise SystemExit(main())
