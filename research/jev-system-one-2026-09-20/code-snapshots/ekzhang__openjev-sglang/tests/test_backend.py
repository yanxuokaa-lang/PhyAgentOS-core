import asyncio
import json
import math

import httpx
import pytest

from openjev.backend import BackendError, SGLangClient, parse_generation
from openjev.config import Settings
from openjev.models import SystemOneRequest
from openjev.scoring import confidence, normalize
from openjev.service import EvaluationService


def test_stable_softmax_and_confidence():
    assert normalize([-10001, -10000]) == pytest.approx([0.2689414214, 0.7310585786])
    assert normalize([-math.inf, 0]) == [0, 1]
    assert normalize([0, 0, 0]) == pytest.approx([1 / 3] * 3)
    assert confidence([0.5, 0.5]) == pytest.approx(0)
    assert confidence([0, 1]) == pytest.approx(1)
    assert max(normalize([-2, 0], 2)) < max(normalize([-2, 0], 1))


def test_rust_cache_count_is_unknown_when_missing():
    result = parse_generation({"meta_info": {"prompt_tokens": 1024, "completion_tokens": 1}}, [])
    assert result.cached_tokens is None


@pytest.mark.parametrize("values", [[], [-math.inf, -math.inf], [math.nan, 0], [math.inf, 0]])
def test_invalid_logits_fail_loudly(values):
    with pytest.raises(ValueError):
        normalize(values)


@pytest.mark.parametrize("entries", [[], [[None, 1]], [[-1, 1]], [[-1, 1], [-2, 1]]])
def test_missing_invalid_or_duplicate_selected_logprobs_fail(entries):
    with pytest.raises((ValueError, KeyError)):
        parse_generation(
            {
                "meta_info": {
                    "prompt_tokens": 10,
                    "completion_tokens": 1,
                    "output_token_ids_logprobs": [entries],
                }
            },
            [1, 2],
        )


async def test_failed_branch_cancels_siblings(compiler, payload):
    aborted = []
    branches_started = asyncio.Event()
    count = 0

    async def handler(request):
        nonlocal count
        data = json.loads(request.content)
        if request.url.path == "/abort_request":
            aborted.append(data["rid"])
            return httpx.Response(200)
        if data.get("token_ids_logprob") != [0]:
            count += 1
            if count == 1:
                await branches_started.wait()
                return httpx.Response(500)
            branches_started.set()
            await asyncio.Event().wait()
        return httpx.Response(
            200,
            json={
                "meta_info": {
                    "prompt_tokens": 10,
                    "completion_tokens": 1,
                }
            },
        )

    settings = Settings()
    async with httpx.AsyncClient(
        base_url="http://sglang", transport=httpx.MockTransport(handler)
    ) as client:
        service = EvaluationService(settings, compiler, SGLangClient(settings, client))
        with pytest.raises(BackendError):
            await service.evaluate(SystemOneRequest.model_validate(payload))
    assert len(aborted) == 2
    assert service.active == 0


async def test_global_branch_concurrency_limit():
    active = maximum = 0

    async def handler(request):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.005)
        active -= 1
        return httpx.Response(
            200,
            json={
                "meta_info": {
                    "prompt_tokens": 10,
                    "completion_tokens": 1,
                }
            },
        )

    async with httpx.AsyncClient(
        base_url="http://sglang", transport=httpx.MockTransport(handler)
    ) as client:
        backend = SGLangClient(Settings(max_concurrent_branches=2), client)
        await asyncio.gather(*(backend.generate([1, 2]) for _ in range(8)))
    assert maximum == 2


async def test_warmup_and_scoring_can_share_a_selected_logprob_batch():
    requests = []

    async def handler(request):
        data = json.loads(request.content)
        requests.append(data)
        assert data["return_logprob"] is True
        assert data["token_ids_logprob"]
        assert data["sampling_params"]["max_new_tokens"] == 1
        return httpx.Response(
            200,
            json={
                "meta_info": {
                    "prompt_tokens": 10,
                    "completion_tokens": 1,
                    "output_token_ids_logprobs": [
                        [[-1.0, token_id] for token_id in data["token_ids_logprob"]]
                    ],
                }
            },
        )

    async with httpx.AsyncClient(
        base_url="http://sglang", transport=httpx.MockTransport(handler)
    ) as client:
        backend = SGLangClient(Settings(), client)
        warmup, answer = await asyncio.gather(
            backend.generate([1, 2]), backend.generate([1, 2, 3], [16, 17])
        )
    assert warmup.logprobs == []
    assert answer.logprobs == [-1.0, -1.0]
    assert requests[1]["token_ids_logprob"] == [16, 17]
