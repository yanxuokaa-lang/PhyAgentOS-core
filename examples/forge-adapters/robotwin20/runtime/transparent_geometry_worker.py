"""RGB-D transparent-geometry inference using the shared worker protocol."""
from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
from sam2_worker import _atomic_numpy, _bounded_source
from worker_protocol import serve


class DepthRecoveryWorker:
    def __init__(self, *, method, repo_root, checkpoint, relative_checkpoint, device,
                 source_artifact_root, worker_artifact_root, image_size,
                 depth_min_m, depth_max_m, depth_scale_to_m=1., seed=0):
        if method not in {"remake", "dfnet"}:
            raise ValueError("unsupported geometry model")
        if (not np.isfinite([depth_min_m, depth_max_m, depth_scale_to_m]).all()
                or not 0 <= depth_min_m < depth_max_m or depth_scale_to_m <= 0):
            raise ValueError("depth range and metric scale must be explicit and valid")
        if len(image_size) != 2 or any(v <= 0 or v % 16 for v in image_size):
            raise ValueError("model image dimensions must be positive multiples of 16")
        self.method, self.device = method, device
        self.repo_root, self.checkpoint = Path(repo_root).resolve(), Path(checkpoint).resolve()
        self.relative_checkpoint = Path(relative_checkpoint).resolve() if relative_checkpoint else None
        self.source_root, self.output_root = Path(source_artifact_root).resolve(), Path(worker_artifact_root).resolve()
        self.image_size = tuple(image_size)
        self.depth_min, self.depth_max, self.depth_scale = depth_min_m, depth_max_m, depth_scale_to_m
        self.seed, self.backend = seed, None
        self.model_revision = None
        self.runtime_metadata = {}

    def load(self):
        if self.backend is not None:
            return
        if not self.repo_root.is_dir() or not self.checkpoint.is_file():
            raise ValueError("geometry source or trained checkpoint is unavailable")
        with contextlib.redirect_stdout(sys.stderr):
            self.backend = TorchDepthBackend(self.method, self.repo_root, self.checkpoint,
                                             self.relative_checkpoint, self.device, self.seed)
        self.model_revision = subprocess.check_output(
            ["git", "-C", str(self.repo_root), "rev-parse", "HEAD"], text=True).strip()
        import torch
        self.runtime_metadata = {"torch": torch.__version__, "numpy": np.__version__,
            "cuda": torch.version.cuda, "device": self.device,
            "model_local_changes": subprocess.check_output(
                ["git", "-C", str(self.repo_root), "diff", "--name-only"], text=True).splitlines()}

    def sleep(self):
        if self.backend is not None:
            self.backend.to("cpu")

    def wake(self):
        self.load()
        self.backend.to(self.device)

    def handle(self, request):
        request_id = request["request_id"]
        try:
            import cv2
            from PIL import Image

            if request.get("operation") != "recover_depth":
                raise ValueError("unsupported geometry operation")
            rgb = np.asarray(Image.open(_bounded_source(request.get("rgb_path"), self.source_root)).convert("RGB"))
            raw = np.load(_bounded_source(request.get("depth_path"), self.source_root), allow_pickle=False)
            mask = np.load(_bounded_source(request.get("mask_path"), self.source_root), allow_pickle=False)
            shape = tuple(reversed(request["image_size_px"]))
            if rgb.shape[:2] != shape or raw.shape != shape or mask.shape != shape:
                raise ValueError("RGB, depth and mask must share original image dimensions")
            mask = mask.astype(bool)
            if not mask.any():
                raise ValueError("recovery requires a nonempty observation mask")
            depth = raw.astype(np.float32) * self.depth_scale
            valid = np.isfinite(depth) & (depth > self.depth_min) & (depth <= self.depth_max)
            if not valid.any():
                raise ValueError("no depth remains inside the configured metric input range")
            depth = np.where(valid, depth, 0).astype(np.float32)
            rgb_model = cv2.resize(rgb, self.image_size, interpolation=cv2.INTER_NEAREST)
            depth_model = cv2.resize(depth, self.image_size, interpolation=cv2.INTER_NEAREST)
            mask_model = cv2.resize(mask.astype(np.uint8), self.image_size, interpolation=cv2.INTER_NEAREST).astype(bool)
            if not mask_model.any() or not np.any(depth_model > 0):
                raise ValueError("model resizing removed the target mask or depth context")
            started = perf_counter()
            with contextlib.redirect_stdout(sys.stderr):
                output = np.asarray(self.backend.predict(rgb_model, depth_model, mask_model), dtype=np.float32)
            if output.shape != depth_model.shape:
                raise ValueError("model output dimensions do not match the inference image")
            output = cv2.resize(output, tuple(reversed(shape)), interpolation=cv2.INTER_NEAREST)
            output_valid = np.isfinite(output) & (output > 0) & (output <= self.depth_max)
            if not np.any(output_valid & mask):
                raise ValueError("model produced no finite positive target depth")
            output = np.where(output_valid, output, 0).astype(np.float32)
            # Atomic helper avoids exposing an incomplete array to the parent.
            from uuid import uuid4
            path = self.output_root / f"depth-{uuid4().hex}.npy"
            _atomic_numpy(path, output)
            return {"request_id": request_id, "status": "available", "depth_path": str(path),
                    "image_size_px": list(reversed(shape)), "metadata": {
                        **self.runtime_metadata, "method": self.method, "unit": "m", "geometry_qualification": "unverified_estimate",
                        "model_revision": self.model_revision, "checkpoint": str(self.checkpoint),
                        "relative_checkpoint": str(self.relative_checkpoint) if self.relative_checkpoint else None,
                        "input_size_px": list(self.image_size), "output_size_px": list(reversed(shape)),
                        "depth_scale_to_m": self.depth_scale, "depth_range_m": [self.depth_min, self.depth_max],
                        "input_valid_fraction": float(valid.mean()), "target_output_valid_fraction": float(output_valid[mask].mean()),
                        "inference_s": perf_counter() - started, "seed": self.seed,
                        "preprocessing": "remake_upstream_rgb_relative_swap" if self.method == "remake" else "dfnet_upstream_inpaint_normalize",
                    }}
        except Exception as exc:
            print(f"geometry inference failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return {"request_id": request_id, "status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}


class TorchDepthBackend:
    """Load actual upstream model classes; preserve their inference normalization."""
    def __init__(self, method, repo_root, checkpoint, relative_checkpoint, device, seed):
        import cv2
        import torch

        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("configured CUDA device is unavailable")
        torch.manual_seed(seed)
        self.method, self.device, self.relative = method, device, None
        sys.path.insert(0, str(repo_root))
        if method == "remake":
            from models.remake import ReMake
            sys.path.insert(0, str(repo_root / "relat_depth_models"))
            from depth_anything_v2.dpt import DepthAnythingV2
            from depth_anything_v2.util.transform import NormalizeImage, PrepareForNet, Resize
            if relative_checkpoint is None or not relative_checkpoint.is_file():
                raise ValueError("ReMake requires the trained relative-depth checkpoint")
            self.model = ReMake()
            self.relative = DepthAnythingV2(encoder="vits", features=64, out_channels=[48, 96, 192, 384])
            self.relative.load_state_dict(torch.load(relative_checkpoint, map_location="cpu", weights_only=True))
            self.transforms = [Resize(518, 518, resize_target=False, keep_aspect_ratio=True,
                                      ensure_multiple_of=14, resize_method="lower_bound",
                                      image_interpolation_method=cv2.INTER_CUBIC),
                               NormalizeImage(mean=[.485, .456, .406], std=[.229, .224, .225]), PrepareForNet()]
        else:
            from models.DFNet import DFNet
            self.model = DFNet()
        # Released ReMake metadata contains a NumPy scalar. Allow exactly these
        # numeric types while retaining weights-only loading (no pickle fallback).
        with torch.serialization.safe_globals([(np.core.multiarray.scalar, "numpy.core.multiarray.scalar"), np.dtype, type(np.dtype("float64"))]):
            trained = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.model.load_state_dict(trained["model_state_dict"])
        self.to(device)

    def to(self, device):
        import torch
        self.device = device
        self.model.to(device).eval()
        if self.relative is not None:
            self.relative.to(device).eval()
        if device == "cpu" and torch.cuda.is_available():
            torch.cuda.empty_cache()

    def predict(self, rgb, depth, mask):
        import cv2
        import torch
        from torch.nn import functional as functional

        def tensor(value):
            return torch.from_numpy(np.ascontiguousarray(value, dtype=np.float32)).to(self.device).unsqueeze(0)

        rgb_tensor = tensor((rgb / 255.).transpose(2, 0, 1))
        with torch.inference_mode():
            if self.method == "remake":
                # Match the released training/inference helper, including its RGB
                # channel swap for the relative-depth branch; record this choice.
                sample = {"image": cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB) / 255.}
                for transform in self.transforms:
                    sample = transform(sample)
                relative = self.relative(tensor(sample["image"]))[:, None]
                relative = functional.interpolate(relative, size=depth.shape, mode="bilinear", align_corners=False)
                result = self.model(rgb_tensor, relative, tensor(depth), tensor(mask))
            else:
                from scipy.interpolate import NearestNDInterpolator
                depth = depth.copy()
                values = depth[depth > 0]
                mean, std = values.mean(), values.std()
                depth[(depth < mean - 10 * std) | (depth > mean + 10 * std)] = 0
                ys, xs = np.where(depth > 0)
                if not len(ys):
                    raise ValueError("DFNet preprocessing removed all depth context")
                depth = NearestNDInterpolator(np.column_stack((ys, xs)), depth[ys, xs])(*np.indices(depth.shape))
                low, high = depth.min() - .5 * depth.std() - 1e-6, depth.max() + .5 * depth.std() + 1e-6
                result = self.model(rgb_tensor, tensor((depth - low) / (high - low))) * (high - low) + low
        return result.squeeze().cpu().numpy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("remake", "dfnet"), required=True)
    for key in ("repo-root", "checkpoint", "source-artifact-root", "worker-artifact-root"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--relative-checkpoint", type=Path)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--image-size", type=int, nargs=2, required=True)
    parser.add_argument("--depth-min-m", type=float, required=True)
    parser.add_argument("--depth-max-m", type=float, required=True)
    parser.add_argument("--depth-scale-to-m", type=float, default=1.)
    parser.add_argument("--seed", type=int, default=0)
    worker = DepthRecoveryWorker(**vars(parser.parse_args()))
    return serve("transparent_geometry", worker.load, worker.handle, sleep=worker.sleep, wake=worker.wake)


if __name__ == "__main__":
    raise SystemExit(main())
