from __future__ import annotations

import tarfile

from scripts.package_skill import package


def test_package_excludes_local_tool_caches(tmp_path):
    skill = tmp_path / "example-skill"
    skill.mkdir()
    (skill / "skill.yaml").write_text(
        "manifest_version: 2\nname: example-skill\nversion: '1.0.0'\n",
        encoding="utf-8",
    )
    (skill / "SKILL.md").write_text("# Example\n", encoding="utf-8")
    for directory in (".pytest_cache", ".ruff_cache", "src/__pycache__"):
        cache = skill / directory
        cache.mkdir(parents=True)
        (cache / "generated").write_text("not release content", encoding="utf-8")

    archive = package(skill, tmp_path / "dist")

    with tarfile.open(archive, "r:gz") as bundle:
        names = bundle.getnames()
    assert "SKILL.md" in names
    assert "skill.yaml" in names
    assert not any(
        part in {".pytest_cache", ".ruff_cache", "__pycache__"}
        for name in names
        for part in name.split("/")
    )
