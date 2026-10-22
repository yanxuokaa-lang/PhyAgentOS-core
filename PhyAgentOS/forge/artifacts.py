"""Provider-neutral access to artifacts referenced by Forge contracts."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class ArtifactContent:
    """Bytes and media type resolved from an opaque artifact reference."""

    data: bytes
    media_type: str


class ArtifactResolver(Protocol):
    """Resolve an artifact URI without exposing storage paths to callers."""

    def resolve(self, artifact_ref: str) -> ArtifactContent | None: ...


class LocalFilesystemArtifactResolver:
    """Resolve ``artifact://authority/path`` beneath configured local roots."""

    _MEDIA_TYPES = {
        ".npy": "application/x-npy",
        ".json": "application/json",
    }

    def __init__(self, roots: Mapping[str, str | Path]) -> None:
        if not isinstance(roots, Mapping) or not roots:
            raise ValueError("artifact roots must be a non-empty authority mapping")
        normalized: dict[str, Path] = {}
        for authority, root in roots.items():
            if (
                not isinstance(authority, str)
                or not authority.strip()
                or "/" in authority
                or "\\" in authority
                or authority in {".", ".."}
            ):
                raise ValueError("artifact authority must be a simple non-empty name")
            path = Path(root).expanduser().resolve()
            if not path.is_dir():
                raise ValueError(f"artifact root is not a directory: {path}")
            normalized[authority] = path
        self._roots = normalized

    def resolve(self, artifact_ref: str) -> ArtifactContent | None:
        if not isinstance(artifact_ref, str) or not artifact_ref.strip():
            return None
        try:
            parsed = urlsplit(artifact_ref)
            has_port = parsed.port is not None
        except ValueError:
            return None
        root = self._roots.get(parsed.netloc)
        if (
            parsed.scheme != "artifact"
            or root is None
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
            or has_port
        ):
            return None
        raw_parts = parsed.path.lstrip("/").split("/")
        parts = [unquote(part) for part in raw_parts]
        if not parts or any(
            not part or part in {".", ".."} or "/" in part or "\\" in part or "\x00" in part
            for part in parts
        ):
            return None
        candidate = root.joinpath(*parts).resolve()
        if root not in candidate.parents or not candidate.is_file():
            return None
        try:
            data = candidate.read_bytes()
        except OSError:
            return None
        if not data:
            return None
        media_type = self._MEDIA_TYPES.get(candidate.suffix.lower()) or mimetypes.guess_type(candidate.name)[0]
        if not media_type:
            return None
        return ArtifactContent(data=data, media_type=media_type)


__all__ = ["ArtifactContent", "ArtifactResolver", "LocalFilesystemArtifactResolver"]
