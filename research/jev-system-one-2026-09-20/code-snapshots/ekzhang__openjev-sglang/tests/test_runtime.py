import pytest

from openjev.config import Settings
from openjev.runtime import backend_command


def test_explicit_model_and_revision_override_profile():
    settings = Settings(model="local/custom", revision="revision")
    assert settings.model == "local/custom"
    assert settings.model_revision == "revision"


def test_default_launch_keeps_radix_and_breakable_graphs():
    command = backend_command(Settings(), [])
    assert command[command.index("--cuda-graph-backend-prefill") + 1] == "breakable"
    assert command[command.index("--mamba-radix-cache-strategy") + 1] == "extra_buffer"
    assert "--disable-radix-cache" not in command
    assert "--speculative-algorithm" not in command
    assert "--revision" in command


def test_public_name_is_independent_of_weight_source(monkeypatch):
    monkeypatch.setenv("OPENJEV_SERVED_MODEL_NAME", "my-model")
    settings = Settings()
    command = backend_command(settings, [])
    assert command[command.index("--model-path") + 1] == "nvidia/Qwen3.6-35B-A3B-NVFP4"
    assert command[command.index("--served-model-name") + 1] == "my-model"


def test_reject_cache_disable():
    with pytest.raises(ValueError, match="radix"):
        backend_command(Settings(), ["--disable-radix-cache"])


def test_local_tokenizer_path_is_forwarded_to_rust():
    command = backend_command(Settings(), [], "/cache/pinned-snapshot")
    assert command[command.index("--tokenizer-path") + 1] == "/cache/pinned-snapshot"
    assert "--cuda-graph-max-bs-decode" in command
    assert "--cuda-graph-max-bs" not in command
