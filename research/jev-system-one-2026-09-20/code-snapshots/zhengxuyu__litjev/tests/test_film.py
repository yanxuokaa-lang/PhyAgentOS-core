import json

import pytest

pytest.importorskip("gymnasium")

from test_games import RecordingClient

from litjev.games import make_env
from litjev.games.film import build_film
from litjev.games.policy import LitJevPolicy
from litjev.games.rollout import record_episode


def test_standalone_film_escapes_trace_content_and_contains_real_readout(tmp_path):
    with make_env("chess", max_steps=1) as env:
        trace = record_episode(
            env,
            LitJevPolicy(RecordingClient(), env.unwrapped.action_names, env.unwrapped.instructions),
        )
    trace["actions"][0] = '</script><script>alert("injected")</script>'
    source, output = tmp_path / "trace.json", tmp_path / "replay.html"
    source.write_text(json.dumps(trace))
    build_film(source, output)
    html = output.read_text()
    assert trace["actions"][0] not in html
    assert "\\u003c/script\\u003e" in html
    assert "litjev.trace.v1" in html
    assert "lm_head" in html
    assert '"__LITJEV_TRACE__"' not in html


def test_film_rejects_upstream_trained_head_format(tmp_path):
    source = tmp_path / "trace.json"
    source.write_text('{"decisions": []}')
    with pytest.raises(ValueError):
        build_film(source, tmp_path / "out.html")
