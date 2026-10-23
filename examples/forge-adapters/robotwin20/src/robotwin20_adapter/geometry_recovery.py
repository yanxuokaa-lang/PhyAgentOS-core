"""Camera-geometry recovery port and the existing process-worker transport.

The port has no simulator or grasp policy. Returned geometry remains an estimate;
availability establishes aligned metric output, not manipulation readiness.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol
from uuid import uuid4

import numpy as np


class GeometryRecoveryError(RuntimeError):
    """The configured recovery mechanism could not produce aligned geometry."""


@dataclass
class GeometryRecoveryRequest:
    observation_ref: str
    scene_revision: str
    frame_id: str
    calibration_ref: str
    rgb_path: Path
    depth_path: Path
    mask_path: Path
    image_size_px: tuple[int, int]


@dataclass
class GeometryRecoveryResult:
    depth_m: np.ndarray
    metadata: Mapping[str, Any]


class GeometryRecoveryProvider(Protocol):
    def recover(self, request: GeometryRecoveryRequest) -> GeometryRecoveryResult: ...
    def release(self) -> None: ...
    def shutdown(self) -> None: ...


class WorkerGeometryRecoveryProvider:
    """Load a recovery worker's original-resolution, metre-valued depth artifact."""

    def __init__(self, client, *, worker_artifact_root: Path):
        self.client = client
        self.root = Path(worker_artifact_root).resolve()

    def recover(self, request: GeometryRecoveryRequest) -> GeometryRecoveryResult:
        request_id = uuid4().hex
        reply = self.client.request({
            "request_id": request_id, "operation": "recover_depth",
            **{key: getattr(request, key) for key in
               ("observation_ref", "scene_revision", "frame_id", "calibration_ref")},
            **{key: str(getattr(request, key)) for key in ("rgb_path", "depth_path", "mask_path")},
            "image_size_px": list(request.image_size_px),
        })
        if not isinstance(reply, Mapping) or reply.get("request_id") != request_id:
            raise GeometryRecoveryError("geometry worker returned a mismatched response")
        if reply.get("status") != "available":
            raise GeometryRecoveryError(f"geometry recovery failed: {reply.get('error', reply.get('status'))}")
        metadata = reply.get("metadata", {})
        if (reply.get("image_size_px") != list(request.image_size_px)
                or not isinstance(metadata, Mapping) or metadata.get("unit") != "m"):
            raise GeometryRecoveryError("geometry worker changed output dimensions or metric units")
        value = reply.get("depth_path")
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise GeometryRecoveryError("geometry worker returned an invalid artifact path")
        path = Path(value).resolve()
        if self.root not in path.parents or not path.is_file():
            raise GeometryRecoveryError("geometry artifact is unavailable or outside the worker root")
        try:
            depth = np.load(path, allow_pickle=False)
        except (ValueError, OSError) as exc:
            raise GeometryRecoveryError("geometry artifact could not be read") from exc
        if depth.shape != tuple(reversed(request.image_size_px)) or depth.dtype.kind != "f":
            raise GeometryRecoveryError("geometry output is not an aligned floating-point depth image")
        if not np.any(np.isfinite(depth) & (depth > 0)):
            raise GeometryRecoveryError("geometry output has no finite positive depth")
        return GeometryRecoveryResult(depth_m=depth, metadata=dict(metadata))

    def release(self):
        self.client.release()

    def shutdown(self):
        self.client.shutdown()
