import pytest

from openjev.config import Settings
from openjev.models import SystemOneRequest
from openjev.prompts import PromptCompiler
from openjev.runtime import load_tokenizer

pytestmark = pytest.mark.integration


def test_real_qwen_token_boundaries_and_64_labels(payload):
    compiler = PromptCompiler(load_tokenizer(Settings()))
    payload["state"] = [
        {"role": "system", "content": "A system message"},
        {"role": "user", "content": "A question"},
        {"role": "assistant", "content": "An answer", "reasoning_content": "Thinking here"},
    ]
    prepared = compiler.prepare(SystemOneRequest.model_validate(payload))
    assert len(compiler.labels) == 64
    assert len(compiler.tokenizer.encode("64", add_special_tokens=False)) == 2
    for branch in prepared.branches:
        decoded = compiler.tokenizer.decode(branch.input_ids)
        assert compiler.tokenizer.encode(decoded, add_special_tokens=False) == branch.input_ids
        assert branch.input_ids[: len(prepared.prefix_ids)] == prepared.prefix_ids
        assert decoded.count("<|im_start|>system") == 1
        assert "<think>\n\n</think>\n\nAnswer:\n" in decoded
