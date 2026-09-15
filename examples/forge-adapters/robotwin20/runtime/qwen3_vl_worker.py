"""JSONL Qwen3-VL worker; imports ML dependencies only inside the worker."""

from __future__ import annotations

import contextlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from worker_protocol import serve

_JSON = re.compile(r"\{.*\}", re.DOTALL)


class Qwen3VLWorker:
    def __init__(self, model_path: Path, device: str = "cuda:0") -> None:
        self.model_path = model_path
        self.device = device
        self.processor: Any = None
        self.model: Any = None

    def load(self) -> None:
        if not self.model_path.is_absolute() or not (self.model_path / "config.json").is_file():
            raise ValueError("qwen model directory is unavailable")
        with contextlib.redirect_stdout(sys.stderr):
            import torch
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            if self.device.startswith("cuda") and not torch.cuda.is_available():
                raise RuntimeError("configured CUDA device is unavailable")
            self.processor = AutoProcessor.from_pretrained(
                str(self.model_path), local_files_only=True, trust_remote_code=True
            )
            load_kwargs = {
                "dtype": "auto",
                "local_files_only": True,
                "trust_remote_code": True,
            }
            if self.device == "cpu":
                # Explicit CPU placement is required for a sequential low-VRAM
                # deployment; device_map="auto" may silently reclaim CUDA.
                load_kwargs["device_map"] = {"": "cpu"}
            elif self.device.startswith("cuda"):
                # Keep placement explicit.  The operator must stop other GPU
                # workers before this process starts; automatic CPU offload is
                # not assumed because compressed-tensors kernels may still
                # materialize temporary tensors on CUDA during generation.
                load_kwargs["device_map"] = {"": self.device}
            else:
                raise ValueError("device must be cpu or a CUDA device")
            self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                str(self.model_path), **load_kwargs
            ).eval()

    def handle(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        request_id = request["request_id"]
        expected = {
            "request_id", "operation", "observation_ref", "scene_revision", "frame_id",
            "rgb_artifact_ref", "rgb_path", "max_output_tokens",
        }
        if set(request) != expected or request.get("operation") != "understand_scene":
            return {"request_id": request_id, "status": "unavailable"}
        path = Path(request["rgb_path"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError("rgb_path must be an existing absolute file")
        from PIL import Image

        with Image.open(path) as source:
            image = source.convert("RGB")
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": _prompt()},
        ]}]
        with contextlib.redirect_stdout(sys.stderr):
            import torch

            inputs = self.processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt",
            )
            model_device = next(self.model.parameters()).device
            inputs = {
                key: value.to(model_device) if hasattr(value, "to") else value
                for key, value in inputs.items()
            }
            with torch.inference_mode():
                generated = self.model.generate(
                    **inputs, max_new_tokens=int(request["max_output_tokens"]), do_sample=False
                )
            prompt_length = inputs["input_ids"].shape[1]
            output = self.processor.batch_decode(
                generated[:, prompt_length:], skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]
        result = _parse_json(output)
        return {"request_id": request_id, "status": "available", "result": result}


def _prompt() -> str:
    return (
        "Inspect this single RGB observation for a robot scene. Return one JSON object only, with exactly these keys: "
        "entities, relations, spatial_envelopes, ambiguities. Entities must be objects with entity_ref "
        "(entity://name), category, confidence. Relations must be objects with relation_ref, subject_ref, "
        "predicate, object_ref, confidence. spatial_envelopes must be an empty array because metric geometry "
        "comes from RGB-D perception. Every one of entities, relations, spatial_envelopes, and ambiguities "
        "must be an array (use [] when empty). Ambiguities items must contain code, message, entity_refs. "
        "Inspect the complete image including corners and small or low-contrast objects; do not "
        "return an empty entities array when a distinct object is visible. Populate one entity for "
        "every distinct visible object before writing ambiguities. Identify only "
        "clearly visible objects; never invent simulator IDs, poses, dimensions, collision geometry, IK, "
        "motion authorization, or task success. Use this task-neutral JSON shape exactly: "
        '{"entities":[{"entity_ref":"entity://object-1","category":"visible category",'
        '"confidence":0.9}],"relations":[],"spatial_envelopes":[],"ambiguities":[]}'
    )


def _parse_json(output: str) -> dict[str, Any]:
    match = _JSON.search(output)
    if not match:
        raise ValueError("qwen output did not contain JSON")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("qwen output JSON must be an object")
    # Some instruct checkpoints emit one ambiguity object instead of the
    # schema's array when there is only one item.  Normalize that container
    # shape locally; semantic fields and metric-envelope prohibitions remain
    # validated by the adapter provider.
    if isinstance(value.get("ambiguities"), dict):
        value["ambiguities"] = [value["ambiguities"]]
    return value


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    worker = Qwen3VLWorker(args.model_path, args.device)
    return serve("qwen3_vl", worker.load, worker.handle)


if __name__ == "__main__":
    raise SystemExit(main())
