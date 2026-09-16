#!/usr/bin/env python3
"""Build a deterministic, self-verifying Forge Skill ``tar.gz`` bundle."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PhyAgentOS.skill_runtime.archive import ArchiveValidator, sha256_file  # noqa: E402


class PackagingError(RuntimeError):
    pass


EXCLUDED_PARTS = {
    ".git",
    ".hg",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    "__pycache__",
    "node_modules",
}


def _safe_identity(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackagingError(f"{label} must be a non-empty string")
    value = value.strip()
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise PackagingError(f"{label} must be directory-safe")
    return value


def _files(root: Path, output: Path) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise PackagingError(f"symlinks are forbidden: {relative.as_posix()}")
        if path.is_file() and path.resolve() != output.resolve():
            if relative.as_posix() == "archive-manifest.json":
                continue
            result.append((relative.as_posix(), path))
    result.sort(key=lambda item: item[0])
    return result


def _tar_info(name: str, size: int, *, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def package(skill_dir: Path, output_dir: Path, *, force: bool = False) -> Path:
    skill_dir = skill_dir.expanduser().resolve()
    if not (skill_dir / "skill.yaml").is_file() or not (skill_dir / "SKILL.md").is_file():
        raise PackagingError("Skill source must contain skill.yaml and SKILL.md")
    try:
        manifest = yaml.safe_load((skill_dir / "skill.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PackagingError("cannot parse skill.yaml") from exc
    if not isinstance(manifest, dict):
        raise PackagingError("skill.yaml must be a mapping")
    name = _safe_identity(manifest.get("name"), "Skill name")
    version = _safe_identity(manifest.get("version"), "Skill version")
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{name}-{version}.tar.gz"
    if target.exists() and not force:
        raise PackagingError(f"output already exists: {target}; use --force to replace it")
    files = _files(skill_dir, target)
    archive_manifest = json.dumps(
        {
            "schema_version": 1,
            "files": [
                {
                    "path": relative,
                    "size": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for relative, path in files
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=output_dir)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(mode="w", fileobj=compressed, format=tarfile.PAX_FORMAT) as tar:
                    for relative, path in files:
                        data = path.read_bytes()
                        mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        tar.addfile(_tar_info(relative, len(data), mode=mode), io.BytesIO(data))
                    tar.addfile(
                        _tar_info("archive-manifest.json", len(archive_manifest), mode=0o644),
                        io.BytesIO(archive_manifest),
                    )
            raw.flush()
            os.fsync(raw.fileno())
        with tempfile.TemporaryDirectory(prefix="paos-package-verify-") as directory:
            ArchiveValidator().extract(
                temporary,
                Path(directory) / "bundle",
                expected_sha256=sha256_file(temporary),
            )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir")
    parser.add_argument("--output-dir", default="dist/skills")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        result = package(Path(args.skill_dir), Path(args.output_dir), force=args.force)
    except PackagingError as exc:
        parser.error(str(exc))
    print(result)
    print(f"sha256: {sha256_file(result)}")
    print(f"size_bytes: {result.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
