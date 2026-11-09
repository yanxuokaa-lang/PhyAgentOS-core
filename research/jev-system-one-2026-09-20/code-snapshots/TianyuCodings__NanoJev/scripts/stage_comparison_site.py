#!/usr/bin/env python3
"""Stage the standalone comparison site or package its committed static files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


SOURCES = {
    "side-by-side.html": "index.html",
    "side-by-side.css": "side-by-side.css",
    "side-by-side.js": "side-by-side.js",
    "side_by_side_results.json": "side_by_side_results.json",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-root", type=Path, default=Path("web"))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    hosting_file = project / ".openai/hosting.json"
    hosting = json.loads(hosting_file.read_text())
    assert isinstance(hosting["project_id"], str) and hosting["project_id"]
    public = (project / hosting["static"]["directory"]).resolve()
    assert public.is_relative_to(project) and public != project
    if args.archive:
        assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=project).strip(), "Commit the complete site before packaging"
        commit = subprocess.check_output(["git", "rev-parse", "--verify", "HEAD"], cwd=project, text=True).strip()
        tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=project, text=True).split("\0"))
        files = [hosting_file, *sorted(p for p in public.rglob("*") if p.is_file())]
        assert (public / "index.html").is_file()
        for file in files:
            assert not file.is_symlink() and file.relative_to(project).as_posix() in tracked
        assert not args.archive.resolve().is_relative_to(project), "Write the archive outside the source checkout"
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(args.archive, "w:gz") as archive:
            for file in files:
                archive.add(file, arcname=file.relative_to(project).as_posix(), recursive=False)
        with tarfile.open(args.archive, "r:gz") as archive:
            assert all(member.isfile() and not member.name.startswith("/") and ".." not in Path(member.name).parts for member in archive.getmembers())
            for file in files:
                assert archive.extractfile(file.relative_to(project).as_posix()).read() == file.read_bytes()
        print(json.dumps({"archive": str(args.archive.resolve()), "files": len(files), "commit_sha": commit,
                          "sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest()}))
        return
    data = json.loads((args.web_root / "side_by_side_results.json").read_text())
    assert data["schema"] == "nanojev-arcade-v1" and {item["game"] for item in data["examples"]} == {"maze", "snake"}
    for item in data["examples"]:
        assert {model["id"] for model in item["systems"]} == {"jev", "nanojev", "base"}
        assert next(model for model in item["systems"] if model["id"] == "base")["name"] == "Untuned Qwen"
    public.mkdir(parents=True, exist_ok=True)
    assert set(p.name for p in public.iterdir()) <= set(SOURCES.values()) | {"source_manifest.json"}
    records = []
    for source, destination in SOURCES.items():
        raw = (args.web_root / source).read_bytes()
        (public / destination).write_bytes(raw)
        records.append({"source": "web/" + source, "asset": destination, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    (public / "source_manifest.json").write_text(json.dumps({"schema": "nanojev-comparison-static-v1", "files": records}, indent=2) + "\n")
    print(json.dumps({"public_directory": str(public), "files": len(records) + 1, "new_model_calls": 0}))


if __name__ == "__main__":
    main()
