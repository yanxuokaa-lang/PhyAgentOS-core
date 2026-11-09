import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/release_notes.py"


def run_release_notes(tmp_path: Path, changelog: str, tag: str = "v1.2.3", version: str = "1.2.3") -> subprocess.CompletedProcess[str]:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/changelog.md").write_text(changelog)
    return subprocess.run(  # noqa: S603 - Fixed interpreter and repository-owned script.
        [sys.executable, str(SCRIPT), tag, version],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(tmp_path / "output")},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


@pytest.mark.parametrize("unreleased", ["", "## Unreleased\n\nFuture work.\n\n"])
def test_release_notes(tmp_path: Path, unreleased: str) -> None:
    notes = "Custom **release notes**.\n\n### Features\n\n- Something new.\n"
    changelog = (
        "---\ntitle: Changelog\n---\n\n# Changelog\n\n"
        f"{unreleased}"
        f"## v1.2.3 (2026-09-09)\n\n{notes}\n"
        "## v1.2.2 (2026-09-08)\n\nOlder release.\n"
    )
    result = run_release_notes(tmp_path, changelog)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "output").read_text() == "title=v1.2.3 (2026-09-09)\n"
    assert (tmp_path / "release-notes.md").read_text() == notes


@pytest.mark.parametrize(
    "changelog, tag, version, error",
    [
        ("## v1.2.2 (2026-09-09)\nNotes.\n", "v1.2.3", "1.2.3", "found 0"),
        ("## v1.2.30 (2026-09-09)\nNotes.\n", "v1.2.3", "1.2.3", "found 0"),
        (
            "## v1.2.4 (2026-09-10)\nNew release.\n\n## v1.2.3 (2026-09-09)\nOlder release.\n",
            "v1.2.3",
            "1.2.3",
            "must match the latest changelog entry",
        ),
        ("## v1.2.3 (2026-09-09)\nNotes.\n" * 2, "v1.2.3", "1.2.3", "found 2"),
        ("## v1.2.3 (2026-09-09)\n\n", "v1.2.3", "1.2.3", "Empty release notes"),
        ("## v1.2.3 (2026-02-30)\nNotes.\n", "v1.2.3", "1.2.3", "ValueError"),
        ("## v1.2.3 (tomorrow)\nNotes.\n", "v1.2.3", "1.2.3", "Invalid release heading"),
        ("", "v1.2.3", "1.2.4", "does not match package version"),
        ("", "v1.2", "1.2", "vX.Y.Z format"),
    ],
)
def test_invalid_release_notes(tmp_path: Path, changelog: str, tag: str, version: str, error: str) -> None:
    result = run_release_notes(tmp_path, changelog, tag, version)
    assert result.returncode != 0
    assert error in result.stderr
    assert not (tmp_path / "release-notes.md").exists()
    assert not (tmp_path / "output").exists()
