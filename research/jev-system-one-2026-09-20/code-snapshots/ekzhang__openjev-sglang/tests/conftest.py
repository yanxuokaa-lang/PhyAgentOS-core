import asyncio
import json

import httpx
import pytest

from openjev.api import create_app
from openjev.backend import SGLangClient
from openjev.config import Settings
from openjev.prompts import PromptCompiler
from openjev.service import EvaluationService


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        if text.isalpha() and text.isupper() and len(text) <= 2:
            if len(text) == 1:
                return [10000 + ord(text)]
            return [20000 + ord(text[0]) * 100 + ord(text[1])]
        return [ord(c) for c in text]

    def decode(self, ids):
        if len(ids) == 1 and ids[0] >= 20000:
            return chr((ids[0] - 20000) // 100) + chr((ids[0] - 20000) % 100)
        if len(ids) == 1 and ids[0] >= 10000:
            return chr(ids[0] - 10000)
        return "".join(chr(i) for i in ids)

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs["enable_thinking"] is False
        return (
            "".join(
                f"<|im_start|>{m['role']}\n{m.get('content') or ''}<|im_end|>\n" for m in messages
            )
            + "<|im_start|>assistant\n<think>\n\n</think>\n\n"
        )


@pytest.fixture
def compiler():
    return PromptCompiler(FakeTokenizer())


@pytest.fixture
def payload():
    return {
        "model": "jev-latest",
        "state": "I was charged twice, please refund.",
        "questions": {
            "yes": {"type": "noul", "instructions": "Refund?"},
            "team": {
                "type": "choice",
                "instructions": "Team?",
                "criteria": {"billing": "Payments", "technical": "Software"},
            },
            "level": {
                "type": "score",
                "instructions": "Urgency?",
                "criteria": ["Low", "Medium", "High"],
            },
        },
    }


@pytest.fixture
async def api(compiler):
    calls = []
    warmed = False
    settings = Settings()

    async def handler(request):
        nonlocal warmed
        if request.url.path == "/health":
            return httpx.Response(200, json={})
        data = json.loads(request.content)
        calls.append(data)
        assert data["sampling_params"]["max_new_tokens"] == 1
        labels = data.get("token_ids_logprob")
        is_warmup = labels == [0]
        if not is_warmup:
            assert warmed, "A branch ran before the prefix barrier"
        else:
            await asyncio.sleep(0.005)
            warmed = True
        meta = {
            "prompt_tokens": len(data["input_ids"]),
            "completion_tokens": 1,
            "cached_tokens": 0 if is_warmup else 100,
        }
        if labels:
            # Return reordered entries, so correctness depends on IDs, not tuple order.
            meta["output_token_ids_logprobs"] = [
                [[-float(i + 1), label, None] for i, label in enumerate(labels)][::-1]
            ]
        return httpx.Response(200, json={"text": "unused", "meta_info": meta})

    async with httpx.AsyncClient(
        base_url="http://sglang", transport=httpx.MockTransport(handler)
    ) as client:
        service = EvaluationService(settings, compiler, SGLangClient(settings, client))
        app = create_app(settings, service=service)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                base_url="http://test", transport=httpx.ASGITransport(app=app)
            ) as api_client:
                yield api_client, calls, service
