"""Tests for the jevmlx CLI argument handling and version output."""

import json

import pytest

from jevmlx import __version__
from jevmlx.cli import main


def test_version(capsys):
    """`jevmlx --version` exits 0 and prints `jevmlx <version>`."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert f"jevmlx {__version__}" in capsys.readouterr().out


def test_decide_requires_preset_or_schema_and_context(capsys):
    """`decide` with neither --preset nor --schema/--context exits 2, naming what is missing."""
    with pytest.raises(SystemExit) as exc:
        main(["decide"])
    assert exc.value.code == 2
    stderr = capsys.readouterr().err
    assert "--preset" in stderr
    assert "--schema" in stderr
    assert "--context" in stderr


def test_decide_schema_without_context(capsys):
    """`decide --schema FILE` without --context exits 2, naming --context."""
    with pytest.raises(SystemExit) as exc:
        main(["decide", "--schema", "schema.json"])
    assert exc.value.code == 2
    assert "--context" in capsys.readouterr().err


def test_decide_context_without_schema(capsys):
    """`decide --context FILE` without --schema exits 2, naming --schema."""
    with pytest.raises(SystemExit) as exc:
        main(["decide", "--context", "context.txt"])
    assert exc.value.code == 2
    assert "--schema" in capsys.readouterr().err


def test_decide_rejects_preset_with_schema(capsys):
    """`decide --preset x --schema y` exits 2."""
    with pytest.raises(SystemExit) as exc:
        main(["decide", "--preset", "fintech_fraud", "--schema", "schema.json"])
    assert exc.value.code == 2


def test_decide_rejects_preset_with_context(capsys):
    """`decide --preset x --context y` exits 2."""
    with pytest.raises(SystemExit) as exc:
        main(["decide", "--preset", "fintech_fraud", "--context", "context.txt"])
    assert exc.value.code == 2


def test_validate_exits_1_on_compile_error(tmp_path, capsys, monkeypatch):
    """`jevmlx validate` exits 1 when the schema cannot compile (L1b)."""

    class FakeTok:
        name_or_path = "fake-cli-tok"

        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            # OK1/OK2 tokenize identically -> compile_error.
            if "OK1" in text or "OK2" in text:
                return [ord(c) for c in text.replace("OK1", "OK").replace("OK2", "OK")]
            return [ord(c) for c in text]

    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "action": {
                    "type": "enum",
                    "description": "d",
                    "choices": ["OK1", "OK2"],
                }
            }
        )
    )
    tok = FakeTok()
    monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", lambda _model: tok)
    with pytest.raises(SystemExit) as exc:
        main(["validate", str(schema_path)])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "compile_error" in out
