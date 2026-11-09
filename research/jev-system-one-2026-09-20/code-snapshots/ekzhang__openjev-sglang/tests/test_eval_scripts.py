"""Offline checks for eval resumption, label scoring, and remote result collection."""

import io
import json
import runpy
from pathlib import Path

import pytest

EVALS = Path(__file__).parents[1] / "evals"


@pytest.fixture
def files():
    return runpy.run_path(EVALS / "run_files.py")


def test_resume_preserves_manifest_and_only_allows_execution_changes(files, tmp_path):
    path = tmp_path / "manifest.json"
    settings = {"model": "test", "indices": [2, 5], "concurrency": 2}
    original = files["save_manifest"](path, settings)
    resumed = files["save_manifest"](
        path, {**settings, "concurrency": 16}, mutable=("concurrency",)
    )
    assert resumed == original == json.loads(path.read_text())
    with pytest.raises(ValueError, match="Different run parameters"):
        files["save_manifest"](path, {**settings, "indices": [2, 6]})


def test_partial_predictions_resume_but_cannot_be_reported(files, tmp_path):
    path = tmp_path / "predictions.jsonl"
    assert files["load_predictions"](path, [2, 5]) == []
    path.write_text('{"index": 2}\n')
    assert files["load_predictions"](path, [2, 5]) == [{"index": 2}]
    with pytest.raises(ValueError, match="Incomplete"):
        files["load_predictions"](path, [2, 5], complete=True)


@pytest.mark.parametrize("indices", [[2, 2], [2, 7]])
def test_duplicate_or_foreign_predictions_are_rejected(files, tmp_path, indices):
    path = tmp_path / "predictions.jsonl"
    path.write_text("".join(json.dumps({"index": i}) + "\n" for i in indices))
    with pytest.raises(ValueError, match="Duplicate or unexpected"):
        files["load_predictions"](path, [2, 5])


def test_duplicate_sample_indices_are_rejected(files, tmp_path):
    with pytest.raises(ValueError, match="duplicate sample indices"):
        files["load_predictions"](tmp_path / "predictions.jsonl", [2, 2])


@pytest.mark.parametrize("settings", [{"indices": [5, 2]}, {"count": 2}])
def test_report_loader_sorts_sampled_and_sequential_runs(files, tmp_path, settings):
    indices = settings.get("indices", [1, 0])
    (tmp_path / "manifest.json").write_text(json.dumps(settings))
    (tmp_path / "predictions.jsonl").write_text(
        "".join(json.dumps({"index": i}) + "\n" for i in indices)
    )
    manifest, rows = files["load_run"](tmp_path)
    assert manifest == settings
    assert [r["index"] for r in rows] == sorted(indices)


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.syspath_prepend(str(EVALS))
    return runpy.run_path(EVALS / "mmlu_pro_openrouter.py")


@pytest.fixture
def response():
    return {
        "usage": {"completion_tokens": 1, "completion_tokens_details": {"reasoning_tokens": 0}},
        "choices": [
            {
                "message": {"content": "A"},
                "logprobs": {
                    "content": [
                        {
                            "top_logprobs": [
                                {"token": " C", "logprob": -0.1},
                                {"token": "B", "logprob": -1},
                                {"token": "A", "logprob": -2},
                            ]
                        }
                    ]
                },
            }
        ],
    }


def test_hosted_scoring_uses_exact_label_argmax_not_sample(hosted, response):
    assert hosted["score_response"](response, list("ABC")) == ("B", {"B": -1, "A": -2})
    assert hosted["score_response"](response, list("DE")) == (None, {})


@pytest.mark.parametrize(
    "bad_field", ["output_count", "reasoning", "missing_reasoning", "logprobs"]
)
def test_hosted_scoring_rejects_protocol_violations(hosted, response, bad_field):
    if bad_field == "output_count":
        response["usage"]["completion_tokens"] = 2
    elif bad_field == "reasoning":
        response["usage"]["completion_tokens_details"]["reasoning_tokens"] = 1
    elif bad_field == "missing_reasoning":
        response["usage"]["completion_tokens_details"] = {}
    else:
        response["choices"][0]["logprobs"] = None
    with pytest.raises(ValueError):
        hosted["score_response"](response, list("ABC"))


def test_gold_and_rationale_never_enter_hosted_prompt(hosted):
    row = {
        "question": "Question?",
        "options": ["First", "Second"],
        "answer": "SECRET_GOLD",
        "cot_content": "SECRET_REASONING",
    }
    rendered = json.dumps(hosted["messages"](row))
    assert "SECRET" not in rendered
    assert "First" in rendered and "Second" in rendered


@pytest.mark.parametrize("exit_code", [0, 1])
def test_remote_launcher_collects_prefixed_records_and_surfaces_failures(
    monkeypatch, tmp_path, exit_code
):
    module = runpy.run_path(EVALS / "modal_probe.py")
    script = tmp_path / "probe.py"
    script.write_text("print('probe')")
    output = 'startup\nworker RESULT_JSON {"index": 2}\nTIMING_JSON {"budget": 0}\n'

    class Process:
        stdout = io.StringIO(output)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def wait(self):
            return exit_code

    def popen(command, **kwargs):
        assert command[6] == "ta-test"
        assert command[10] == script.read_text()
        assert kwargs["text"] is True
        return Process()

    monkeypatch.setattr(module["subprocess"], "Popen", popen)

    def call():
        return module["run_remote"](
            script, "ta-test", {"rows": []}, tmp_path, total=1, progress_every=1
        )

    if exit_code:
        with pytest.raises(RuntimeError, match="Remote probe failed"):
            call()
    else:
        assert call() == ([{"index": 2}], [{"budget": 0}])
    assert (tmp_path / "remote.log").read_text() == output
