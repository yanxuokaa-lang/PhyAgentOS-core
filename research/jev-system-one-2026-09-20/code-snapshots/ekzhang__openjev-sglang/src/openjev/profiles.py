"""Dependency-free deployment and backend presets; safe in Modal's outer Python."""

from dataclasses import dataclass

from .defaults import DEFAULT_MODEL, DEFAULT_REVISION, SGLANG_IMAGE


@dataclass(frozen=True)
class ModelProfile:
    model: str
    served_model_name: str
    revision: str
    image: str
    backend_python: str
    memory_mib: int
    app_name: str
    backend_args: tuple[str, ...]


PROFILES = {
    "qwen36": ModelProfile(
        model=DEFAULT_MODEL,
        served_model_name="Qwen/Qwen3.6-35B-A3B",
        revision=DEFAULT_REVISION,
        image=SGLANG_IMAGE,
        backend_python="/opt/sglang/bin/python",
        memory_mib=32768,
        app_name="openjev-sglang",
        backend_args=(
            "--language-only",
            "--attention-backend",
            "trtllm_mha",
            "--kv-cache-dtype",
            "fp8_e4m3",
        ),
    ),
}
