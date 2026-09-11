#!/usr/bin/env python3
"""Stage adapter-owned sources and package the formal RoboTwin20 Skill Bundle."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path

import yaml
from package_skill import package


def build_bundle(repository: Path, output_dir: Path, node_archive: Path) -> Path:
    workflow = repository / "examples/forge-skills/pick-place-workflow"
    if not (workflow / "skill.yaml").is_file():
        raise RuntimeError("pick-place workflow Skill source is missing")
    if not node_archive.is_file():
        raise RuntimeError(f"Node archive is missing: {node_archive}")
    manifest = yaml.safe_load((workflow / "skill.yaml").read_text(encoding="utf-8"))
    expected = manifest["artifacts"]["nodes"]["robotwin20_persistent_host"]["sha256"]
    actual = hashlib.sha256(node_archive.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(
            "Node archive sha256 does not match the Skill lock: "
            f"expected {expected}, got {actual}"
        )
    with tempfile.TemporaryDirectory(prefix="paos-robotwin20-skill-") as temporary:
        staging = Path(temporary) / "pick-place-workflow"
        shutil.copytree(workflow, staging)
        return package(staging, output_dir, force=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--node-archive", type=Path, required=True)
    args = parser.parse_args()
    result = build_bundle(args.repository.resolve(), args.output_dir.resolve(), args.node_archive.resolve())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
