"""SGLang lifecycle. CUDA dependencies stay in the SGLang Python environment."""

import asyncio
import logging
import os
import signal
import subprocess
import time
from contextlib import asynccontextmanager

from .config import Settings
from .launch import watch_process
from .profiles import PROFILES

logger = logging.getLogger(__name__)


def backend_command(
    settings: Settings, extra: list[str], tokenizer_path: str | None = None
) -> list[str]:
    forbidden = {"--disable-radix-cache", "--disable-cuda-graph", "--disable-piecewise-cuda-graph"}
    if any(arg.split("=")[0] in forbidden for arg in extra):
        raise ValueError("OpenJev requires radix caching and CUDA graphs")
    command = [
        settings.sglang_python,
        "-m",
        "sglang.launch_server",
        "--model-path",
        settings.model,
        "--served-model-name",
        settings.served_model_name,
        "--host",
        "127.0.0.1",
        "--port",
        str(settings.backend_port),
        "--context-length",
        str(settings.max_input_tokens),
        "--mem-fraction-static",
        "0.8",
        "--moe-runner-backend",
        "flashinfer_cutlass",
        "--mamba-radix-cache-strategy",
        "extra_buffer",
        "--cuda-graph-backend-prefill",
        "breakable",
        "--cuda-graph-max-bs-decode",
        "64",
        "--enable-metrics",
    ]
    command.extend(PROFILES[settings.profile].backend_args)
    if settings.model_revision:
        command.extend(["--revision", settings.model_revision])
    if tokenizer_path:
        command.extend(["--tokenizer-path", tokenizer_path])
    if settings.backend_api_key:
        command.extend(["--api-key", settings.backend_api_key.get_secret_value()])
    return command + extra


@asynccontextmanager
async def backend_process(settings: Settings, enabled: bool, extra: list[str]):
    process = None
    stopping = None
    if enabled:
        # Rust's Hub lookup can miss a revision-pinned HF cache snapshot. Resolve
        # assets before GPU startup and pass a real directory to both frontends.
        tokenizer_path = await asyncio.to_thread(resolve_tokenizer_path, settings)
        env = dict(os.environ)
        env["SGLANG_RUST_SERVER"] = "1" if settings.frontend == "rust" else "0"
        logger.info("Starting SGLang with %s frontend and breakable CUDA graphs", settings.frontend)
        process = subprocess.Popen(
            backend_command(settings, extra, tokenizer_path), env=env, start_new_session=True
        )
        stopping = watch_process(process, "SGLang")
    try:
        yield process
    finally:
        if stopping is not None:
            stopping.set()
        if process is not None:
            await asyncio.to_thread(stop_process, process)


def stop_process(process: subprocess.Popen):
    # Kill the group even if the leader exited: scheduler children may remain.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


async def wait_ready(backend, process, timeout: float):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"SGLang exited with status {process.returncode}; see logs above")
        if await backend.health():
            return
        await asyncio.sleep(1)
    raise TimeoutError(f"SGLang was not ready within {timeout:g}s")


def load_tokenizer(settings: Settings):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        settings.model, revision=settings.model_revision, trust_remote_code=False
    )


def resolve_tokenizer_path(settings: Settings) -> str:
    from pathlib import Path

    from huggingface_hub import snapshot_download

    if Path(settings.model).is_dir():
        return str(Path(settings.model).resolve())
    return snapshot_download(
        settings.model,
        revision=settings.model_revision,
        allow_patterns=["*.json", "*.jinja", "*.model", "*.txt"],
    )
