from __future__ import annotations

import hashlib
import importlib.util
import sys
import tarfile
from pathlib import Path

import yaml

SCRIPT = (
    Path(__file__).resolve().parents[4] / "scripts/build_robotwin20_skill_bundle.py"
)
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("build_robotwin20_skill_bundle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_bundle_embeds_only_the_node_archive_locked_by_the_manifest(tmp_path):
    repository = tmp_path / "repository"
    workflow = repository / "examples/forge-skills/pick-place-workflow"
    nodes = workflow / "nodes"
    nodes.mkdir(parents=True)
    (workflow / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")
    stale = nodes / "robotwin20_persistent_host-0.10.0.tar.gz"
    stale.write_bytes(b"stale-node")
    current = tmp_path / "downloaded-node.tar.gz"
    current.write_bytes(b"current-node")
    digest = hashlib.sha256(current.read_bytes()).hexdigest()
    (workflow / "skill.yaml").write_text(
        yaml.safe_dump({
            "manifest_version": 2,
            "name": "pick-place-workflow",
            "version": "2.10.2",
            "skill_document": "SKILL.md",
            "artifacts": {
                "resolver": "local",
                "nodes": {
                    "robotwin20_persistent_host": {
                        "version": "0.10.1",
                        "sha256": digest,
                    }
                },
            },
        }),
        encoding="utf-8",
    )

    bundle = MODULE.build_bundle(repository, tmp_path / "dist", current)

    with tarfile.open(bundle, "r:gz") as archive:
        node_members = sorted(
            member.name
            for member in archive.getmembers()
            if member.name.startswith("nodes/")
            and member.name.endswith(".tar.gz")
        )
        assert node_members == ["nodes/robotwin20_persistent_host-0.10.1.tar.gz"]
        stream = archive.extractfile(node_members[0])
        assert stream is not None
        assert stream.read() == b"current-node"
