"""Isolated GraspNet JSONL worker.

The adapter-facing protocol is intentionally the same as GraspGen's.  The
GraspNet dependency and checkpoint stay in the provider environment; this
process only converts its ``grasp_center``/rotation output to homogeneous
matrices and never performs IK, collision checks, or motion.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from worker_protocol import serve


class WorkerUnavailableError(RuntimeError):
    pass


_OPTIONS: argparse.Namespace | None = None
_MODEL: tuple[Any, Any, Any] | None = None


def _load() -> None:
    global _MODEL
    assert _OPTIONS is not None
    checkpoint = Path(_OPTIONS.checkpoint).expanduser().resolve()
    if not checkpoint.is_file():
        raise WorkerUnavailableError("graspnet checkpoint is unavailable")
    if _OPTIONS.source_root:
        import sys

        source = str(Path(_OPTIONS.source_root).expanduser().resolve())
        if source not in sys.path:
            sys.path.insert(0, source)
    try:
        import torch
        from graspnet import GraspNet, pred_decode
        from graspnetAPI import GraspGroup

        device = torch.device(_OPTIONS.device if torch.cuda.is_available() and _OPTIONS.device.startswith("cuda") else "cpu")
        network = GraspNet(
            input_feature_dim=0,
            num_view=300,
            num_angle=12,
            num_depth=4,
            cylinder_radius=0.05,
            hmin=-0.02,
            hmax_list=[0.01, 0.02, 0.03, 0.04],
            is_training=False,
        )
        state = torch.load(str(checkpoint), map_location=device)
        state_dict = state["model_state_dict"] if isinstance(state, dict) and "model_state_dict" in state else state
        network.load_state_dict(state_dict)
        network.to(device).eval()
        _MODEL = (network, pred_decode, GraspGroup)
    except Exception as exc:  # noqa: BLE001
        raise WorkerUnavailableError("graspnet model initialization failed") from exc


def _handle(request: Mapping[str, Any]) -> Mapping[str, Any]:
    if request.get("schema_version") != "paos-grasp-worker/v1":
        raise WorkerUnavailableError("grasp request schema_version is unsupported")
    if request.get("provider") != "graspnet":
        raise WorkerUnavailableError("grasp request provider is unsupported")
    path = request.get("point_cloud_path")
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise WorkerUnavailableError("grasp point_cloud_path must be absolute")
    try:
        import numpy as np

        points = np.asarray(np.load(Path(path), allow_pickle=False), dtype=np.float32)
    except (ImportError, OSError, ValueError) as exc:
        raise WorkerUnavailableError("grasp point cloud could not be loaded") from exc
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 1 or not bool(np.isfinite(points).all()):
        raise WorkerUnavailableError("grasp point cloud must be a finite non-empty Nx3 array")
    if _MODEL is None:
        raise WorkerUnavailableError("graspnet model is unavailable")
    max_candidates = request.get("max_candidates")
    threshold = request.get("score_threshold")
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or not 1 <= max_candidates <= 512:
        raise WorkerUnavailableError("max_candidates is invalid")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= float(threshold) <= 1:
        raise WorkerUnavailableError("score_threshold is invalid")
    if request.get("apply_model_collision") is True:
        raise WorkerUnavailableError("model collision filtering requires a provider-specific implementation")
    try:
        import torch

        network, pred_decode, grasp_group_type = _MODEL
        if points.shape[0] >= 20000:
            sampled = points[np.random.choice(points.shape[0], 20000, replace=False)]
        else:
            sampled = np.concatenate([points, points[np.random.choice(points.shape[0], 20000 - points.shape[0], replace=True)]])
        with torch.no_grad():
            device = next(network.parameters()).device
            end_points = network({"point_clouds": torch.from_numpy(sampled[None]).to(device)})
            decoded = pred_decode(end_points)[0].detach().cpu().numpy()
        group = grasp_group_type(decoded)
    except Exception as exc:  # noqa: BLE001
        raise WorkerUnavailableError("graspnet model inference failed") from exc
    candidates = []
    for grasp in group:
        center = np.asarray(grasp.translation, dtype=np.float64).reshape(3)
        rotation = np.asarray(grasp.rotation_matrix, dtype=np.float64).reshape(3, 3)
        score = float(grasp.score)
        if not np.isfinite(center).all() or not np.isfinite(rotation).all() or not np.isfinite(score):
            raise WorkerUnavailableError("graspnet model returned malformed candidates")
        if score < float(threshold):
            continue
        matrix = np.eye(4, dtype=np.float64)
        matrix[:3, :3] = rotation
        matrix[:3, 3] = center
        candidates.append({"matrix": matrix.tolist(), "score": score})
    candidates = candidates[:max_candidates]
    return {
        "request_id": request["request_id"],
        "status": "available" if candidates else "empty",
        "candidates": candidates,
        "funnel": {"decoded": len(group), "canonicalized": len(candidates), "deduplicated": len(candidates), "retained": len(candidates)},
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio-worker", action="store_true")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--source-root")
    parser.add_argument("--device", default="cuda:0")
    return parser


def main(argv: list[str] | None = None) -> int:
    global _OPTIONS
    _OPTIONS = _parser().parse_args(argv)
    if not _OPTIONS.stdio_worker:
        raise SystemExit("--stdio-worker is required")
    return serve("graspnet", _load, _handle, schema_version="paos-grasp-worker/v1")


if __name__ == "__main__":
    raise SystemExit(main())
