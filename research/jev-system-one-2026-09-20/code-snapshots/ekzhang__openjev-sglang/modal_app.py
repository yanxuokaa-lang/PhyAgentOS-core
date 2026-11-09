"""uv run modal run modal_app.py  (ephemeral B200 smoke test)
uv run modal deploy modal_app.py  (persistent .modal.direct endpoint)
"""

import os
from pathlib import Path

import modal

from openjev.profiles import PROFILES

ROOT = Path(__file__).parent
PROFILE_NAME = os.environ.get("OPENJEV_PROFILE", "qwen36")
profile = PROFILES[PROFILE_NAME]
app = modal.App(profile.app_name)
cache = modal.Volume.from_name("openjev-huggingface", create_if_missing=True)

# Keep SGLang's tested CUDA environment intact. uv owns a separate, small API
# environment; the package starts SGLang using the base image's Python.
image = (
    modal.Image.from_registry(profile.image)
    .entrypoint([])
    .uv_pip_install("uv==0.12.5")
    .add_local_file(ROOT / "pyproject.toml", "/opt/openjev/pyproject.toml", copy=True)
    .add_local_file(ROOT / "uv.lock", "/opt/openjev/uv.lock", copy=True)
    .add_local_file(ROOT / "README.md", "/opt/openjev/README.md", copy=True)
    .add_local_dir(ROOT / "src", "/opt/openjev/src", copy=True)
    .run_commands("cd /opt/openjev && uv sync --frozen --no-default-groups --python 3.12")
    .env(
        {
            "PYTHONPATH": "/opt/openjev/src",
            "HF_HOME": "/cache/huggingface",
            "HF_XET_HIGH_PERFORMANCE": "1",
            "SGLANG_CACHE_DIR": "/cache/huggingface/runtime/sglang",
            "TRITON_CACHE_DIR": "/cache/huggingface/runtime/triton",
            "TOKENIZERS_PARALLELISM": "false",
            "OPENJEV_FRONTEND": os.environ.get("OPENJEV_FRONTEND", "rust"),
            "OPENJEV_PROFILE": PROFILE_NAME,
            "OPENJEV_SERVED_MODEL_NAME": os.environ.get(
                "OPENJEV_SERVED_MODEL_NAME", profile.served_model_name
            ),
        }
    )
)


@app.server(
    image=image,
    gpu="B200",
    cpu=8,
    memory=profile.memory_mib,
    volumes={"/cache/huggingface": cache},
    port=8000,
    routing_region="us-west",
    compute_region=["us-west", "us-central", "us"],
    unauthenticated=True,
    min_containers=0,
    target_concurrency=8,
    scaledown_window=300,
    startup_timeout=1200,
    exit_grace_period=30,
)
class OpenJev:
    @modal.enter()
    def startup(self):
        from openjev.launch import start_background

        self.process = start_background("/opt/openjev/.venv/bin/python", profile.backend_python)

    @modal.exit()
    def shutdown(self):
        from openjev.launch import stop_background

        if hasattr(self, "process"):
            stop_background(self.process)


@app.local_entrypoint()
async def main():
    import json

    from openjev.smoke import smoke_test

    url = await OpenJev.get_url.aio()
    print(f"OpenJev: {url}")
    result = await smoke_test(url)
    (ROOT / "smoke-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
