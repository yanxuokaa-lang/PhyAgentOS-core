"""Extract a tagged release's title and notes from the changelog."""

import os
import re
import sys
from datetime import date
from pathlib import Path


def release_notes(changelog: str, tag: str) -> tuple[str, str]:
    """Return the latest release heading and body, requiring a unique entry matching the tag."""
    sections = re.split(r"^## ", changelog, flags=re.MULTILINE)[1:]
    sections = [section for section in sections if section.partition("\n")[0] != "Unreleased"]
    matches = [section for section in sections if section.partition("\n")[0].startswith(f"{tag} (")]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one changelog entry for {tag}, found {len(matches)}")
    if matches[0] != sections[0]:
        raise ValueError(f"Tag {tag} must match the latest changelog entry")
    title, _, body = matches[0].partition("\n")
    match = re.fullmatch(rf"{re.escape(tag)} \((\d{{4}}-\d{{2}}-\d{{2}})\)", title)
    if match is None:
        raise ValueError(f"Invalid release heading: {title}")
    date.fromisoformat(match[1])
    if not body.strip():
        raise ValueError(f"Empty release notes for {tag}")
    return title, body.strip() + "\n"


VERSION_PATTERN = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"


def validate_release(changelog: str, tag: str, version: str) -> tuple[str, str]:
    """Keep tag/version validation shared by extraction, snapshotting, and tagging."""
    if re.fullmatch(VERSION_PATTERN, version) is None or tag != f"v{version}":
        raise ValueError(f"Tag {tag} does not match package version {version} or the vX.Y.Z format")
    return release_notes(changelog, tag)


def main() -> None:
    """Validate the tag and write notes and GitHub Actions outputs."""
    tag, version = sys.argv[1:]
    title, notes = validate_release(Path("docs/changelog.md").read_text(), tag, version)
    Path("release-notes.md").write_text(notes)
    if output_path := os.environ.get("GITHUB_OUTPUT"):
        with Path(output_path).open("a") as output:
            output.write(f"title={title}\n")
    print(title)


if __name__ == "__main__":
    main()
