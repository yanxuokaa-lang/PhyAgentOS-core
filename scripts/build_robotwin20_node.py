#!/usr/bin/env python3
"""Build the single-executable RoboTwin20 persistent-host Forge Node archive."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import tarfile
import zipfile
from pathlib import Path


class NodeBuildError(RuntimeError):
    """Raised when the Node artifact cannot be built from repository inputs."""


def _source_archive(adapter_root: Path, workflow_root: Path) -> str:
    for label, root in (("adapter", adapter_root), ("workflow", workflow_root)):
        if not root.is_dir():
            raise NodeBuildError(f"{label} root is missing: {root}")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        paths = []
        roots = (
            ("adapter", adapter_root / "src"),
            ("adapter", adapter_root / "runtime"),
            ("adapter", adapter_root / "profiles"),
            ("workflow", workflow_root / "src"),
        )
        for label, root in roots:
            if not root.is_dir():
                raise NodeBuildError(f"{label} source directory is missing: {root}")
            paths.extend(
                (label, path)
                for path in root.rglob("*")
                if path.is_file()
                and not any(
                    part in {"__pycache__", ".pytest_cache", ".ruff_cache"}
                    for part in path.parts
                )
            )
        for label, path in sorted(paths, key=lambda item: (item[0], item[1].as_posix())):
            base = adapter_root if label == "adapter" else workflow_root / "src"
            relative = f"{label}/{path.relative_to(base).as_posix()}"
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _launcher(adapter_payload: str) -> bytes:
    return f'''#!/usr/bin/env python3
"""Self-contained PAOS RoboTwin20 persistent-host Node."""

from __future__ import annotations

import base64
import io
import os
import sys
import tempfile
import zipfile

_ADAPTER_PAYLOAD = "{adapter_payload}"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="paos-robotwin20-node-") as directory:
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(_ADAPTER_PAYLOAD))) as archive:
            archive.extractall(directory)
        root = os.path.join(directory, "adapter")
        environment = os.environ.copy()
        environment["ROBOTWIN20_EMBEDDED_ADAPTER_ROOT"] = root
        paths = [
            os.path.join(root, "src"),
            os.path.join(root, "runtime"),
            os.path.join(directory, "workflow"),
        ]
        existing = environment.get("PYTHONPATH")
        if existing:
            paths.append(existing)
        environment["PYTHONPATH"] = os.pathsep.join(paths)
        command = [sys.executable, "-m", "robotwin20_adapter.persistent_host", *sys.argv[1:]]
        os.execvpe(sys.executable, command, environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''.encode("utf-8")


def _tar_info(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o755
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def build(
    output: Path,
    *,
    adapter_root: Path,
    workflow_root: Path,
    entrypoint: str = "robotwin20_persistent_host",
) -> Path:
    if not entrypoint or "/" in entrypoint or "\\" in entrypoint:
        raise NodeBuildError("entrypoint must be a directory-safe filename")
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = _launcher(_source_archive(adapter_root.resolve(), workflow_root.resolve()))
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(mode="w", fileobj=compressed, format=tarfile.PAX_FORMAT) as tar:
                    tar.addfile(_tar_info(entrypoint, len(payload)), io.BytesIO(payload))
            raw.flush()
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter-root", type=Path, required=True)
    parser.add_argument("--workflow-root", type=Path, required=True)
    parser.add_argument("--entrypoint", default="robotwin20_persistent_host")
    args = parser.parse_args()
    artifact = build(
        args.output,
        adapter_root=args.adapter_root,
        workflow_root=args.workflow_root,
        entrypoint=args.entrypoint,
    )
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    print(artifact)
    print(f"sha256: {digest}")
    print(f"size_bytes: {artifact.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
