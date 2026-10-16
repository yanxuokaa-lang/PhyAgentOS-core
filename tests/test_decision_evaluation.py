from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from PhyAgentOS.agent.decision_evaluation import (
    DecisionEvaluationDataset,
    DecisionMeasurement,
    audit_held_out_dataset,
    run_decision_evaluation,
)

HELD_OUT_CASES = (
    ("held-multi-entity", "family-entity", "multi_entity", "one", False),
    ("held-multi-method", "family-method", "multi_method", "two", False),
    ("held-no-option", "family-none", "no_applicable_option", None, True),
    ("held-cross-scene", "family-scene", "cross_scene", None, True),
    ("held-illegal", "family-illegal", "illegal_combination", None, True),
    ("held-complex", "family-complex", "complex_planning", None, True),
)


def _dataset() -> dict:
    cases = [{
        "case_id": "calibration-entity",
        "split": "calibration",
        "family_id": "family-calibration",
        "categories": ["multi_entity"],
        "decision_input_ref": "artifact://jev-eval/inputs/calibration-entity",
        "provenance_refs": ["artifact://jev-eval/source/calibration-entity"],
        "goal": "Select the current complete query input.",
        "facts": {"scene_revision": "scene-calibration"},
        "candidates": [
            {"candidate_id": "one", "description": "current source one"},
            {"candidate_id": "two", "description": "current source two"},
        ],
        "expected_selected_id": "one",
    }]
    cases.extend({
        "case_id": case_id,
        "split": "held_out",
        "family_id": family_id,
        "categories": [category],
        "decision_input_ref": f"artifact://jev-eval/inputs/{case_id}",
        "provenance_refs": [f"artifact://jev-eval/source/{case_id}"],
        "goal": "Select the current complete query input.",
        "facts": {"scene_revision": f"scene-{case_id}"},
        "candidates": [
            {"candidate_id": "one", "description": "current source one"},
            {"candidate_id": "two", "description": "current source two"},
        ],
        "expected_selected_id": expected,
        "must_escalate": must_escalate,
    } for case_id, family_id, category, expected, must_escalate in HELD_OUT_CASES)
    return {
        "version": "jev_decision_evaluation_dataset_v1",
        "name": "query-input-selection",
        "dataset_version": "2026-10-15.v1",
        "sampling_plan_ref": "artifact://jev-eval/sampling/query-v1",
        "labeling_protocol_ref": "review.json",
        "provenance_manifest_ref": "provenance.json",
        "labeler_id": "annotator-a",
        "reviewer_id": "reviewer-b",
        "planned_held_out_cases": len(HELD_OUT_CASES),
        "cases": cases,
    }


def _measurements(*, evidence_mode: str = "measured", wrong_accept: bool = False) -> dict:
    records = []
    for case_id, _family, _category, expected, must_escalate in HELD_OUT_CASES:
        if must_escalate:
            fallback_outcomes = {
                "held-no-option": "escalate",
                "held-cross-scene": "unavailable",
                "held-illegal": "invalid",
                "held-complex": "timeout",
            }
            provider_outcome = (
                "selected"
                if wrong_accept and case_id == "held-illegal"
                else fallback_outcomes[case_id]
            )
            selected_id = "one" if provider_outcome == "selected" else None
            host_outcome = "selected" if provider_outcome == "selected" else "escalated"
            system2_invoked = provider_outcome != "selected"
        else:
            provider_outcome = "selected"
            selected_id = expected
            host_outcome = "selected"
            system2_invoked = False
        records.append({
            "case_id": case_id,
            "repetition": 0,
            "decision_input_ref": f"artifact://jev-eval/inputs/{case_id}",
            "provider": "JEVHTTPDecisionProvider",
            "requested_model": "jev-latest",
            "model_version": "jev-1.13.0",
            "system2_provider": "openai-codex",
            "system2_model": "gpt-5.6-sol",
            "system2_model_version": "gpt-5.6-sol-2026-10-15",
            "provider_outcome": provider_outcome,
            "selected_id": selected_id,
            "host_outcome": host_outcome,
            "decision_trace_ref": (
                f"artifact://planning-traces/eval/{case_id}"
                if host_outcome == "selected"
                else None
            ),
            "system2_invoked": system2_invoked,
            "decision_total_elapsed_ms": 10.0,
            "system2_only_elapsed_ms": 20.0,
        })
    return {
        "version": "jev_decision_measurements_v1",
        "evidence_mode": evidence_mode,
        "records": records,
    }


def _write_inputs(
    root: Path,
    *,
    evidence_mode: str = "measured",
    wrong_accept: bool = False,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    dataset = _dataset()
    (root / "dataset.json").write_text(json.dumps(dataset), encoding="utf-8")
    (root / "review.json").write_text(json.dumps({
        "status": "completed",
        "independent_review": True,
        "labeler_id": dataset["labeler_id"],
        "reviewer_id": dataset["reviewer_id"],
        "reviewed_case_ids": [case["case_id"] for case in dataset["cases"]
                               if case["split"] == "held_out"],
    }), encoding="utf-8")
    (root / "provenance.json").write_text(json.dumps({
        "raw_free_text_uploaded": False,
        "cases": [
            {"case_id": case["case_id"], "provenance_refs": case["provenance_refs"]}
            for case in dataset["cases"]
            if case["split"] == "held_out"
        ],
    }), encoding="utf-8")
    (root / "measurements.json").write_text(
        json.dumps(_measurements(
            evidence_mode=evidence_mode,
            wrong_accept=wrong_accept,
        )),
        encoding="utf-8",
    )
    config = {
        "version": "jev_decision_evaluation_config_v1",
        "dataset": "dataset.json",
        "measurements": "measurements.json",
        "output_root": "runs",
        "acceptance_policy_ref": "artifact://jev-policy/query-v1",
        "splits": ["held_out"],
        "repetitions": 1,
    }
    path = root / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def _write_dataset_only(root: Path, payload: dict | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    payload = payload or _dataset()
    path = root / "dataset.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    if not {"labeler_id", "reviewer_id", "cases"}.issubset(payload):
        return path
    (root / "review.json").write_text(json.dumps({
        "status": "completed",
        "independent_review": True,
        "labeler_id": payload["labeler_id"],
        "reviewer_id": payload["reviewer_id"],
        "reviewed_case_ids": [case["case_id"] for case in payload["cases"]
                               if case["split"] == "held_out"],
    }), encoding="utf-8")
    (root / "provenance.json").write_text(json.dumps({
        "raw_free_text_uploaded": False,
        "cases": [
            {"case_id": case["case_id"], "provenance_refs": case["provenance_refs"]}
            for case in payload["cases"]
            if case["split"] == "held_out"
        ],
    }), encoding="utf-8")
    return path


def test_held_out_intake_audit_allows_complete_dataset_before_pairing(tmp_path):
    dataset_path = _write_dataset_only(tmp_path)

    summary = audit_held_out_dataset(
        dataset_path=dataset_path,
        output_root=tmp_path / "audit-runs",
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert summary.ready_for_pairing is True
    assert summary.exit_code == 0
    report = json.loads((summary.run_dir / "audit_report.json").read_text())
    assert report["remote_calls"] == 0
    assert report["motion_authorized"] is False
    assert report["reasons"] == []


def test_held_out_intake_audit_reports_missing_categories_and_review(tmp_path):
    payload = _dataset()
    payload["reviewer_id"] = payload["labeler_id"]
    payload["cases"] = payload["cases"][:2]
    payload["planned_held_out_cases"] = 6
    dataset_path = _write_dataset_only(tmp_path, payload)

    summary = audit_held_out_dataset(
        dataset_path=dataset_path,
        output_root=tmp_path / "audit-runs",
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert summary.ready_for_pairing is False
    assert summary.exit_code == 2
    report = json.loads((summary.run_dir / "audit_report.json").read_text())
    assert "required_category_coverage" in report["reasons"]
    assert "planned_sample_size_reached" in report["reasons"]
    assert "reviewer_identity_distinct" in report["reasons"]


def test_held_out_intake_audit_rejects_distinct_ids_without_review_record(tmp_path):
    dataset_path = _write_dataset_only(tmp_path)
    (tmp_path / "review.json").write_text(json.dumps({
        "status": "completed",
        "independent_review": False,
        "labeler_id": "annotator-a",
        "reviewer_id": "reviewer-b",
        "reviewed_case_ids": [case["case_id"] for case in _dataset()["cases"]],
    }), encoding="utf-8")

    summary = audit_held_out_dataset(
        dataset_path=dataset_path,
        output_root=tmp_path / "audit-runs",
        repo_root=Path(__file__).resolve().parents[1],
    )

    report = json.loads((summary.run_dir / "audit_report.json").read_text())
    assert summary.ready_for_pairing is False
    assert "independent_label_review" in report["reasons"]


def test_held_out_intake_audit_requires_provenance_mapping(tmp_path):
    payload = _dataset()
    payload["provenance_manifest_ref"] = "missing-provenance.json"
    dataset_path = _write_dataset_only(tmp_path, payload)

    summary = audit_held_out_dataset(
        dataset_path=dataset_path,
        output_root=tmp_path / "audit-runs",
        repo_root=Path(__file__).resolve().parents[1],
    )

    report = json.loads((summary.run_dir / "audit_report.json").read_text())
    assert summary.ready_for_pairing is False
    assert {
        "provenance_manifest_present",
        "provenance_confirmed",
    }.issubset(report["reasons"])


def test_held_out_intake_audit_rejects_duplicate_decision_inputs(tmp_path):
    payload = _dataset()
    payload["cases"][-1]["decision_input_ref"] = payload["cases"][-2]["decision_input_ref"]
    dataset_path = _write_dataset_only(tmp_path, payload)

    summary = audit_held_out_dataset(
        dataset_path=dataset_path,
        output_root=tmp_path / "audit-runs",
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert summary.ready_for_pairing is False
    report = json.loads((summary.run_dir / "audit_report.json").read_text())
    assert "decision_input_refs_unique" in report["reasons"]


def test_held_out_intake_audit_keeps_schema_failures_readable(tmp_path):
    dataset_path = _write_dataset_only(
        tmp_path, {"version": "wrong", "api_key": "SECRET-MUST-NOT-BE-COPIED"}
    )

    summary = audit_held_out_dataset(
        dataset_path=dataset_path,
        output_root=tmp_path / "audit-runs",
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert summary.ready_for_pairing is False
    report = json.loads((summary.run_dir / "audit_report.json").read_text())
    assert report["reasons"] == ["dataset_schema_invalid"]
    assert "error" in report
    assert "SECRET-MUST-NOT-BE-COPIED" not in json.dumps(report)
    assert "SECRET-MUST-NOT-BE-COPIED" not in (
        summary.run_dir / "input_dataset.json"
    ).read_text()


@pytest.mark.parametrize("condition", ["provider_probe", "abstract_point", "no_host_admission"])
def test_calibration_evidence_cannot_qualify_even_with_other_conditions_met(tmp_path, condition):
    config_path = _write_inputs(tmp_path)
    reason = "measured_evidence"
    if condition == "abstract_point":
        config = json.loads(config_path.read_text())
        config["decision_point"] = "abstract_runtime_decision"
        config_path.write_text(json.dumps(config))
        reason = "supported_active_decision_point"
    else:
        path = tmp_path / "measurements.json"
        measurements = json.loads(path.read_text())
        if condition == "provider_probe":
            measurements["evidence_mode"] = "provider_probe"
        else:
            measurements["records"][0]["host_outcome"] = "not_evaluated"
            measurements["records"][0]["decision_trace_ref"] = None
            reason = "host_admission_evaluated"
        path.write_text(json.dumps(measurements))
    result = run_decision_evaluation(config_path=config_path, repo_root=Path.cwd())
    report = json.loads((result.run_dir / "acceptance_report.json").read_text())
    assert result.active_eligible is False and result.exit_code == 2
    assert reason in report["ineligibility_reasons"]


def test_zero_planned_size_does_not_allow_held_out():
    dataset = _dataset()
    dataset["planned_held_out_cases"] = 0
    with pytest.raises(ValidationError, match="positive planned sample size"):
        DecisionEvaluationDataset.model_validate(dataset)


def test_decision_measurement_requires_trace_for_real_substitution():
    with pytest.raises(ValidationError, match="decision_trace_ref"):
        DecisionMeasurement.model_validate({
            "case_id": "held-multi-entity",
            "decision_input_ref": "artifact://jev-eval/inputs/held-multi-entity",
            "provider": "JEVHTTPDecisionProvider",
            "requested_model": "jev-latest",
            "model_version": "jev-1.13.0",
            "system2_provider": "openai-codex",
            "system2_model": "gpt-5.6-sol",
            "system2_model_version": "gpt-5.6-sol-2026-10-15",
            "provider_outcome": "selected",
            "selected_id": "one",
            "host_outcome": "selected",
            "system2_invoked": False,
            "decision_total_elapsed_ms": 10,
            "system2_only_elapsed_ms": 20,
        })


def test_decision_dataset_rejects_family_leakage_between_splits():
    payload = _dataset()
    payload["cases"][0]["family_id"] = "family-entity"
    with pytest.raises(ValidationError, match="may not cross"):
        DecisionEvaluationDataset.model_validate(payload)


def test_measured_complete_held_out_pairs_produce_active_eligible_report(tmp_path):
    config_path = _write_inputs(tmp_path)

    summary = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )

    assert summary.active_eligible is True
    assert summary.exit_code == 0
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())
    manifest = json.loads((summary.run_dir / "run_manifest.json").read_text())
    report = json.loads((summary.run_dir / "acceptance_report.json").read_text())
    assert metrics["candidate_coverage"]["rate"] == 1.0
    assert metrics["raw_selection_accuracy"]["rate"] == 1.0
    assert metrics["erroneous_acceptance"]["count"] == 0
    assert metrics["erroneous_acceptance"]["wilson_95"]["upper"] > 0
    assert metrics["mandatory_escalation_recall"]["rate"] == 1.0
    assert metrics["actual_substitution"]["count"] == 2
    assert metrics["provider_outcomes"] == {
        "escalate": 1,
        "invalid": 1,
        "selected": 2,
        "timeout": 1,
        "unavailable": 1,
    }
    assert metrics["paired_latency_ms"] == {
        "decision_mean": 10.0,
        "decision_p95": 10.0,
        "system2_only_mean": 20.0,
        "system2_only_p95": 20.0,
    }
    assert manifest["git_commit"]
    assert manifest["random_seed"] is None
    assert manifest["selected_case_ids"] == sorted(
        case_id for case_id, *_rest in HELD_OUT_CASES
    )
    assert manifest["acceptance_policy_ref"] == "artifact://jev-policy/query-v1"
    assert manifest["input_snapshots"] == {
        "config": "input_config.json",
        "dataset": "input_dataset.json",
        "measurements": "input_measurements.json",
    }
    input_dataset = json.loads((summary.run_dir / "input_dataset.json").read_text())
    input_measurements = json.loads(
        (summary.run_dir / "input_measurements.json").read_text()
    )
    assert input_dataset["cases"][1]["candidates"][0]["description"] == (
        "current source one"
    )
    assert len(input_measurements["records"]) == len(HELD_OUT_CASES)
    assert report["active_eligible"] is True
    assert report["acceptance_policy_ref"] == "artifact://jev-policy/query-v1"
    rerun = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    assert rerun.run_dir != summary.run_dir


def test_fixture_partial_or_wrong_acceptance_cannot_be_active_eligible(tmp_path):
    fixture_config = _write_inputs(tmp_path / "fixture", evidence_mode="fixture")
    fixture = run_decision_evaluation(
        config_path=fixture_config,
        repo_root=Path(__file__).resolve().parents[1],
        max_cases=2,
    )
    fixture_metrics = json.loads((fixture.run_dir / "metrics.json").read_text())
    assert fixture.active_eligible is False
    assert fixture.exit_code == 0
    assert {"measured_evidence", "full_case_selection"}.issubset(
        fixture_metrics["active_ineligibility_reasons"]
    )

    wrong_config = _write_inputs(tmp_path / "wrong", wrong_accept=True)
    wrong = run_decision_evaluation(
        config_path=wrong_config,
        repo_root=Path(__file__).resolve().parents[1],
    )
    wrong_metrics = json.loads((wrong.run_dir / "metrics.json").read_text())
    assert wrong.active_eligible is False
    assert wrong.exit_code == 2
    assert wrong_metrics["erroneous_acceptance"]["case_ids"] == ["held-illegal"]
    assert wrong_metrics["active_eligibility_checks"]["zero_erroneous_acceptances"] is False
    assert fixture.run_dir != wrong.run_dir


def test_cli_smoke_writes_a_unique_fixture_report(tmp_path):
    config_path = _write_inputs(tmp_path, evidence_mode="fixture")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_jev_decisions.py",
            "--config",
            str(config_path),
            "--max-cases",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "status=completed" in result.stdout
    assert "active_eligible=false" in result.stdout


def test_missing_model_identity_or_independent_review_blocks_active(tmp_path):
    config_path = _write_inputs(tmp_path)
    measurements_path = tmp_path / "measurements.json"
    measurements = json.loads(measurements_path.read_text())
    measurements["records"][0]["system2_model_version"] = None
    measurements_path.write_text(json.dumps(measurements), encoding="utf-8")
    dataset_path = tmp_path / "dataset.json"
    dataset = json.loads(dataset_path.read_text())
    dataset["reviewer_id"] = dataset["labeler_id"]
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

    summary = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())

    assert summary.active_eligible is False
    assert summary.exit_code == 2
    assert {
        "independent_label_review",
        "system2_model_version_recorded",
    }.issubset(metrics["active_ineligibility_reasons"])


def test_formal_evaluator_rejects_unconfirmed_review_and_provenance(tmp_path):
    config_path = _write_inputs(tmp_path)
    review = json.loads((tmp_path / "review.json").read_text())
    review["independent_review"] = False
    (tmp_path / "review.json").write_text(json.dumps(review), encoding="utf-8")
    provenance = json.loads((tmp_path / "provenance.json").read_text())
    provenance["cases"][0]["provenance_refs"] = ["artifact://wrong/source"]
    (tmp_path / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

    summary = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())

    assert summary.active_eligible is False
    assert summary.exit_code == 2
    assert {
        "independent_label_review",
        "provenance_case_coverage",
        "provenance_confirmed",
    }.issubset(metrics["active_ineligibility_reasons"])


def test_malformed_evidence_records_fail_closed(tmp_path):
    config_path = _write_inputs(tmp_path)
    (tmp_path / "review.json").write_text(json.dumps({
        "status": "completed",
        "independent_review": True,
        "labeler_id": "annotator-a",
        "reviewer_id": "reviewer-b",
        "reviewed_case_ids": {"not": "a-list"},
    }), encoding="utf-8")
    (tmp_path / "provenance.json").write_text(json.dumps({
        "raw_free_text_uploaded": False,
        "cases": [{"case_id": "held-multi-entity", "provenance_refs": "not-a-list"}],
    }), encoding="utf-8")

    summary = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())

    assert summary.active_eligible is False
    assert summary.exit_code == 2
    assert "independent_label_review" in metrics["active_ineligibility_reasons"]
    assert "provenance_case_coverage" in metrics["active_ineligibility_reasons"]


def test_missing_policy_or_mismatched_pair_input_blocks_active(tmp_path):
    config_path = _write_inputs(tmp_path)
    config = json.loads(config_path.read_text())
    config["acceptance_policy_ref"] = None
    config_path.write_text(json.dumps(config), encoding="utf-8")
    measurements_path = tmp_path / "measurements.json"
    measurements = json.loads(measurements_path.read_text())
    measurements["records"][0]["decision_input_ref"] = (
        "artifact://jev-eval/inputs/different-request"
    )
    measurements_path.write_text(json.dumps(measurements), encoding="utf-8")

    summary = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())

    assert summary.active_eligible is False
    assert summary.exit_code == 2
    assert {
        "acceptance_policy_recorded",
        "paired_input_refs_match",
    }.issubset(metrics["active_ineligibility_reasons"])
    assert metrics["mismatched_input_pairs"] == [["held-multi-entity", 0]]


def test_missing_unknown_or_mixed_model_pairs_block_active(tmp_path):
    config_path = _write_inputs(tmp_path)
    measurements_path = tmp_path / "measurements.json"
    measurements = json.loads(measurements_path.read_text())
    measurements["records"].pop(0)
    unknown = dict(measurements["records"][0])
    unknown["case_id"] = "unknown-held-out"
    unknown["decision_input_ref"] = "artifact://jev-eval/inputs/unknown-held-out"
    measurements["records"].append(unknown)
    measurements["records"][-2]["model_version"] = "jev-1.14.0"
    measurements_path.write_text(json.dumps(measurements), encoding="utf-8")

    summary = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())

    assert summary.active_eligible is False
    assert {
        "complete_pairs",
        "known_measurement_cases",
        "single_provider_model_version",
    }.issubset(metrics["active_ineligibility_reasons"])
    assert metrics["missing_pairs"] == [["held-multi-entity", 0]]
    assert metrics["unknown_measurement_case_ids"] == ["unknown-held-out"]


def test_no_real_substitution_or_latency_gain_blocks_active(tmp_path):
    config_path = _write_inputs(tmp_path)
    measurements_path = tmp_path / "measurements.json"
    measurements = json.loads(measurements_path.read_text())
    for record in measurements["records"]:
        if record["provider_outcome"] == "selected":
            record.update({
                "provider_outcome": "escalate",
                "selected_id": None,
                "host_outcome": "escalated",
                "decision_trace_ref": None,
                "system2_invoked": True,
            })
        record["decision_total_elapsed_ms"] = 25.0
    measurements_path.write_text(json.dumps(measurements), encoding="utf-8")

    summary = run_decision_evaluation(
        config_path=config_path,
        repo_root=Path(__file__).resolve().parents[1],
    )
    metrics = json.loads((summary.run_dir / "metrics.json").read_text())

    assert summary.active_eligible is False
    assert {
        "actual_substitution_observed",
        "paired_latency_mean_improved",
        "paired_latency_p95_not_worse",
    }.issubset(metrics["active_ineligibility_reasons"])
    assert metrics["actual_substitution"]["count"] == 0
