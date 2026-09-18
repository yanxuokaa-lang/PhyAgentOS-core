#!/usr/bin/env python3
"""Run the semantic-only Qwen provider over multiple RobotWIN screenshots.

This evaluator never starts a runtime, calls a Gateway tool, creates an
AgentTask, steps a simulator, or executes an Action.  It is deliberately
artifact-backed so model and prompt changes can be compared without changing
the physical or simulated world.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_STRUCTURAL_PREDICATES = {
    "on",
    "supports",
    "supported_by",
    "in_contact_with",
    "attached_to",
    "hanging_from",
    "contains",
    "inside",
    "occludes",
    "blocked_by",
}


def _normalized_predicate(value: Any) -> str:
    """Normalize surface wording for evaluation metrics only."""
    predicate = " ".join(str(value).strip().casefold().replace("_", " ").split())
    for prefix in ("is ", "are "):
        if predicate.startswith(prefix):
            predicate = predicate[len(prefix) :]
    return predicate


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model", default="qwen3-vl-4b-awq")
    parser.add_argument("--api-base", default="http://127.0.0.1:8012/v1")
    parser.add_argument("--max-images", type=int, default=12)
    parser.add_argument("--max-per-group", type=int, default=2)
    parser.add_argument("--image", action="append", default=[], help="label=/absolute/path/to/rgb.png")
    return parser.parse_args()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _parse_explicit_images(values: list[str]) -> list[tuple[str, Path]]:
    result = []
    for value in values:
        label, separator, raw_path = value.partition("=")
        if not separator or not label.strip() or not raw_path.strip():
            raise ValueError("--image must use label=/absolute/path/to/rgb.png")
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        result.append((label.strip(), path))
    return result


def _discover_images(root: Path, *, max_images: int, max_per_group: int) -> list[tuple[str, Path]]:
    if not root.is_dir():
        raise NotADirectoryError(root)
    selected: list[tuple[str, Path]] = []
    group_counts: dict[str, int] = {}
    for path in sorted(root.rglob("rgb.png")):
        relative = path.relative_to(root)
        group = relative.parts[0] if relative.parts else path.parent.name
        count = group_counts.get(group, 0)
        if count >= max_per_group:
            continue
        group_counts[group] = count + 1
        label = f"{group}:{path.parent.name}"
        selected.append((label, path))
        if len(selected) >= max_images:
            break
    return selected


def _resolver(path_by_ref: dict[str, Path]):
    from robotwin20_adapter import ArtifactPayload

    def resolve(ref: str) -> ArtifactPayload | None:
        path = path_by_ref.get(ref)
        if path is None:
            return None
        media_type = "image/png" if path.suffix.casefold() == ".png" else "image/jpeg"
        return ArtifactPayload(path.read_bytes(), media_type)

    return resolve


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    entities = result.get("entities", [])
    relations = result.get("relations", [])
    ambiguities = result.get("ambiguities", [])
    predicates = [str(item.get("predicate", "")) for item in relations]
    return {
        "entity_count": len(entities),
        "relation_count": len(relations),
        "structural_relation_count": sum(
            _normalized_predicate(item) in _STRUCTURAL_PREDICATES for item in predicates
        ),
        "ambiguity_count": len(ambiguities),
        "categories": [str(item.get("category", "")) for item in entities],
        "predicates": predicates,
        "ambiguity_codes": [str(item.get("code", "")) for item in ambiguities],
        "provider_available": result.get("provider_available", True),
    }


def main() -> int:
    args = _parse_args()
    if args.max_images < 1 or args.max_per_group < 1:
        raise ValueError("max-images and max-per-group must be positive")
    explicit = _parse_explicit_images(args.image)
    if explicit:
        images = explicit
    else:
        if args.input_root is None:
            raise ValueError("--input-root is required when --image is not supplied")
        images = _discover_images(
            args.input_root.expanduser().resolve(),
            max_images=args.max_images,
            max_per_group=args.max_per_group,
        )
    if not images:
        raise RuntimeError("no RobotWIN rgb.png screenshots were selected")

    output = args.output_root.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output root must be empty: {output}")
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.json").write_text(
        json.dumps(
            {
                "input_root": (
                    str(args.input_root.expanduser().resolve())
                    if args.input_root is not None
                    else None
                ),
                "model": args.model,
                "api_base": args.api_base,
                "temperature": 0,
                "top_p": 1,
                "max_images": args.max_images,
                "max_per_group": args.max_per_group,
                "git_commit": _git_commit(),
                "motion_authorized": False,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = [{"label": label, "path": str(path)} for label, path in images]
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    from robotwin20_adapter import Qwen3VLVLLMConfig, Qwen3VLVLLMSceneUnderstandingInference

    path_by_ref: dict[str, Path] = {}
    diagnostics: list[dict[str, Any]] = []
    provider = None

    def on_diagnostic(event: dict[str, Any]) -> None:
        diagnostics.append(dict(event))

    results: list[dict[str, Any]] = []
    for index, (label, path) in enumerate(images, start=1):
        image_ref = f"artifact://evaluation/{index}/rgb"
        path_by_ref[image_ref] = path
        if provider is None:
            provider = Qwen3VLVLLMSceneUnderstandingInference(
                _resolver(path_by_ref),
                config=Qwen3VLVLLMConfig(api_base=args.api_base, model=args.model),
                diagnostic_sink=on_diagnostic,
            )
        request = {
            "observation_ref": f"observation://evaluation/{index}",
            "scene_revision": f"evaluation-scene-{index}",
            "frame_id": "head_camera",
            "calibration_ref": f"calibration://evaluation/{index}",
            "freshness_ms": 0,
            "max_age_ms": 0,
            "artifacts": [image_ref],
        }
        started = time.perf_counter()
        try:
            result = dict(provider.infer(request))
            results.append(
                {
                    "label": label,
                    "image": str(path),
                    "status": "available",
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "summary": _summary(result),
                    "result": result,
                }
            )
        except Exception as exc:  # preserve one bad screenshot without hiding it
            results.append(
                {
                    "label": label,
                    "image": str(path),
                    "status": "error",
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            )

    (output / "results.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in results),
        encoding="utf-8",
    )
    (output / "route_telemetry.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in diagnostics),
        encoding="utf-8",
    )
    metrics = {
        "images": len(results),
        "available": sum(item["status"] == "available" for item in results),
        "errors": sum(item["status"] == "error" for item in results),
        "entity_count_total": sum(item.get("summary", {}).get("entity_count", 0) for item in results),
        "structural_relation_count_total": sum(
            item.get("summary", {}).get("structural_relation_count", 0) for item in results
        ),
        "motion_authorized": False,
        "gateway_calls": 0,
    }
    (output / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# Open-world scene-understanding evaluation\n\n"
        "Artifact-backed, semantic-only, no-motion evaluation. The run does not "
        "start a RobotWIN runtime, call Gateway/Action/Session, step a simulator, "
        "or authorize motion. `results.jsonl` contains normalized provider results; "
        "`route_telemetry.jsonl` contains optional raw-to-normalized diagnostics.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "completed", "output_root": str(output), **metrics}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
