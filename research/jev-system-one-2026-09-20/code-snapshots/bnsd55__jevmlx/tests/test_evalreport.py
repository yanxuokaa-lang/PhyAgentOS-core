"""Tests for jevmlx.evalreport: environment probe + report writer. No model."""

import json
import sys

import pytest

from jevmlx import evalreport

REQUIRED_ENV_KEYS = {
    "machine_model",
    "chip",
    "ram_gb",
    "macos_version",
    "python_version",
    "mlx_version",
    "mlx_lm_version",
    "jevmlx_version",
    "git_sha",
    "timestamp_utc",
}

FAKE_RUN = {
    "environment": {"chip": "Apple M2 Pro", "ram_gb": 32.0, "git_sha": None},
    "config": {"model": "mlx-community/Qwen2.5-0.5B-Instruct-4bit", "temperature": 1.0},
    "metrics": {
        "accuracy": 0.87,
        "ece": 0.041,
        "nll": 0.52,
        "latency_ms_p50": 210.5,
        "latency_ms_p90": 318.2,
    },
    "per_type": {"transaction": 0.9, "alert": {"accuracy": 0.8, "n": 50}},
    "per_field": [
        {"field": "amount_valid", "n": 120, "accuracy": 0.95},
        {"field": "action", "n": 120, "accuracy": 0.79},
        {"field": "category", "n": 120, "accuracy": 0.88},
    ],
    # Unknown top-level keys must pass through to JSON, be ignored in markdown.
    "future_extension": {"anything": [1, 2, 3]},
}


class TestEnvironment:
    def test_required_keys_present_and_never_raises(self):
        env = evalreport.environment()
        assert REQUIRED_ENV_KEYS <= set(env)
        assert env["python_version"] == sys.version.split()[0]
        assert env["timestamp_utc"].endswith("+00:00")

    def test_optional_safe_probes_degrade_to_none(self, monkeypatch):
        monkeypatch.setattr(evalreport, "_probe", lambda command: None)
        monkeypatch.setattr(evalreport, "_dist_version", lambda name: None)
        env = evalreport.environment()
        assert env["machine_model"] is None
        assert env["chip"] is None
        assert env["ram_gb"] is None
        assert env["mlx_version"] is None
        assert env["jevmlx_version"] is None

    def test_ram_gb_parses_bytes(self, monkeypatch):
        monkeypatch.setattr(
            evalreport,
            "_probe",
            lambda command: str(32 * 2**30) if "memsize" in " ".join(command) else None,
        )
        assert evalreport._ram_gb() == 32.0


class TestWriteReport:
    @pytest.fixture()
    def report_paths(self, tmp_path):
        json_path = tmp_path / "run.json"
        evalreport.write_report(json_path, FAKE_RUN)
        return json_path, json_path.with_suffix(".md")

    def test_writes_both_files(self, report_paths):
        json_path, md_path = report_paths
        assert json_path.is_file()
        assert md_path.is_file()

    def test_json_is_sorted_indent2_and_keeps_unknown_keys(self, report_paths):
        json_path, _ = report_paths
        run = json.loads(json_path.read_text())
        assert run["future_extension"] == FAKE_RUN["future_extension"]
        raw = json_path.read_text()
        # top-level keys sorted: config < environment < metrics < per_field < per_type
        assert (
            raw.index('"config"')
            < raw.index('"environment"')
            < raw.index('"metrics"')
            < raw.index('"per_field"')
            < raw.index('"per_type"')
        )

    def test_markdown_has_env_metrics_and_ascending_field_table(self, report_paths):
        _, md_path = report_paths
        md = md_path.read_text()
        assert "## Environment" in md and "| chip |" in md
        assert "| accuracy | 0.8700 |" in md and "| ece | 0.0410 |" in md
        assert "| latency_ms_p50 | 210.5000 |" in md
        # per-type rows for both dict and bare-number per_type entries
        assert "| accuracy[alert] | 0.8000 |" in md
        assert "| accuracy[transaction] | 0.9000 |" in md
        # ascending by accuracy: action (0.79) before category (0.88) before amount_valid (0.95)
        assert md.index("| action |") < md.index("| category |") < md.index("| amount_valid |")

    def test_markdown_ignores_unknown_keys_and_renders_nones(self, tmp_path):
        json_path = tmp_path / "run.json"
        evalreport.write_report(
            json_path,
            {
                "environment": {"chip": None},
                "metrics": {"accuracy": 1.0},
                "per_field": [{"field": "a", "n": 1, "accuracy": 0.5}],
                "mystery": {"x": 1},
            },
        )
        md = json_path.with_suffix(".md").read_text()
        assert "mystery" not in md and "future_extension" not in md
        assert "| chip | n/a |" in md

    def test_empty_run_does_not_raise(self, tmp_path):
        json_path = tmp_path / "run.json"
        evalreport.write_report(json_path, {})
        md = json_path.with_suffix(".md").read_text()
        assert "## Metrics" in md
