"""Offline, evidence-bound evaluation for typed Agent decisions."""

from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from PhyAgentOS.agent.decision_provider import DecisionCandidate
from PhyAgentOS.utils.atomic_file import atomic_write_text

DecisionEvaluationSplit = Literal["calibration", "held_out"]
DecisionEvidenceMode = Literal["measured", "fixture"]
ProviderOutcome = Literal["selected", "escalate", "unavailable", "timeout", "invalid"]
HostOutcome = Literal[
    "selected",
    "escalated",
    "unavailable",
    "stale",
    "admission_rejected",
]

REQUIRED_HELD_OUT_CATEGORIES = frozenset({
    "multi_entity",
    "multi_method",
    "no_applicable_option",
    "cross_scene",
    "illegal_combination",
    "complex_planning",
})


class DecisionEvaluationConfigurationError(ValueError):
    """Raised when a decision-evaluation input is invalid or incomplete."""


class DecisionEvaluationCase(BaseModel):
    """One independently labeled decision case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,79}$")
    split: DecisionEvaluationSplit
    family_id: str = Field(min_length=1)
    categories: tuple[str, ...] = Field(min_length=1)
    decision_input_ref: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    facts: dict[str, Any]
    candidates: tuple[DecisionCandidate, ...] = Field(min_length=2)
    expected_selected_id: str | None = None
    must_escalate: bool = False

    @field_validator("family_id", "decision_input_ref", "goal")
    @classmethod
    def normalize_case_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("case identity and goal fields must be non-empty")
        return value

    @field_validator("categories")
    @classmethod
    def unique_nonempty_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in values)
        if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("case categories must be unique and non-empty")
        return normalized

    @model_validator(mode="after")
    def validate_expected_choice(self) -> "DecisionEvaluationCase":
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("case candidate IDs must be unique")
        if not self.must_escalate and not self.expected_selected_id:
            raise ValueError("replaceable cases require expected_selected_id")
        if self.must_escalate and self.expected_selected_id is not None:
            raise ValueError("must-escalate cases cannot define an expected selection")
        return self


class DecisionEvaluationDataset(BaseModel):
    """Versioned labels with calibration/held-out family isolation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["jev_decision_evaluation_dataset_v1"]
    name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    sampling_plan_ref: str = Field(min_length=1)
    labeling_protocol_ref: str = Field(min_length=1)
    labeler_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    planned_held_out_cases: int = Field(ge=1)
    cases: tuple[DecisionEvaluationCase, ...] = Field(min_length=1)

    @field_validator(
        "name",
        "dataset_version",
        "sampling_plan_ref",
        "labeling_protocol_ref",
        "labeler_id",
        "reviewer_id",
    )
    @classmethod
    def normalize_dataset_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("dataset metadata must be non-empty")
        return value

    @model_validator(mode="after")
    def validate_dataset(self) -> "DecisionEvaluationDataset":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("decision evaluation case IDs must be unique")
        family_splits: dict[str, set[str]] = {}
        for case in self.cases:
            family_splits.setdefault(case.family_id, set()).add(case.split)
        leaked = sorted(family for family, splits in family_splits.items() if len(splits) > 1)
        if leaked:
            raise ValueError(
                "near-duplicate family IDs may not cross calibration and held_out: "
                + ", ".join(leaked)
            )
        if {case.split for case in self.cases} != {"calibration", "held_out"}:
            raise ValueError("dataset requires both calibration and held_out cases")
        return self


class DecisionMeasurement(BaseModel):
    """One paired System-1 versus System-2 measurement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    repetition: int = Field(default=0, ge=0)
    decision_input_ref: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    model_version: str | None = None
    system2_provider: str = Field(min_length=1)
    system2_model: str = Field(min_length=1)
    system2_model_version: str | None = None
    provider_outcome: ProviderOutcome
    selected_id: str | None = None
    host_outcome: HostOutcome
    decision_trace_ref: str | None = None
    system2_invoked: bool
    decision_total_elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    system2_only_elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    tool_wait_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    operator_wait_ms: float = Field(default=0, ge=0, allow_inf_nan=False)

    @field_validator(
        "decision_input_ref",
        "provider",
        "requested_model",
        "system2_provider",
        "system2_model",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("provider and requested_model must be non-empty")
        return value

    @field_validator("model_version", "system2_model_version")
    @classmethod
    def normalize_model_version(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("model_version must be non-empty when provided")
        return value

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> "DecisionMeasurement":
        if self.provider_outcome == "selected" and not self.selected_id:
            raise ValueError("selected provider outcome requires selected_id")
        if self.provider_outcome != "selected" and self.selected_id is not None:
            raise ValueError("only selected provider outcome may include selected_id")
        if self.host_outcome == "selected":
            if self.provider_outcome != "selected":
                raise ValueError("host selection requires a selected provider outcome")
            if not self.decision_trace_ref or not self.decision_trace_ref.startswith("artifact://"):
                raise ValueError("host selection requires an artifact decision_trace_ref")
            if self.system2_invoked:
                raise ValueError("accepted host selection cannot also invoke System 2")
        elif self.decision_trace_ref is not None:
            raise ValueError("only accepted host selections may carry decision_trace_ref")
        return self


class DecisionEvaluationMeasurements(BaseModel):
    """Versioned paired records collected outside the production task path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["jev_decision_measurements_v1"]
    evidence_mode: DecisionEvidenceMode
    records: tuple[DecisionMeasurement, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_pairs(self) -> "DecisionEvaluationMeasurements":
        keys = [(record.case_id, record.repetition) for record in self.records]
        if len(keys) != len(set(keys)):
            raise ValueError("measurement case/repetition pairs must be unique")
        return self


class DecisionEvaluationConfig(BaseModel):
    """Paths and selection controls for one reproducible offline report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["jev_decision_evaluation_config_v1"]
    dataset: str = Field(min_length=1)
    measurements: str = Field(min_length=1)
    output_root: str = Field(min_length=1)
    acceptance_policy_ref: str | None = None
    splits: tuple[DecisionEvaluationSplit, ...] = ("held_out",)
    repetitions: int = Field(default=1, ge=1, le=20)

    @field_validator("acceptance_policy_ref")
    @classmethod
    def normalize_policy_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("acceptance_policy_ref must be non-empty when provided")
        return value

    @field_validator("splits")
    @classmethod
    def validate_splits(
        cls, splits: tuple[DecisionEvaluationSplit, ...]
    ) -> tuple[DecisionEvaluationSplit, ...]:
        if not splits or len(splits) != len(set(splits)):
            raise ValueError("evaluation splits must be non-empty and unique")
        return splits


class DecisionEvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_dir: Path
    status: Literal["completed"]
    active_eligible: bool
    exit_code: int


def _strict_json_load(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant is not allowed: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key!r}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicates,
    )


def load_decision_evaluation_inputs(
    config_path: Path,
) -> tuple[
    DecisionEvaluationConfig,
    DecisionEvaluationDataset,
    DecisionEvaluationMeasurements,
]:
    config_path = config_path.resolve()
    config = DecisionEvaluationConfig.model_validate(_strict_json_load(config_path))
    dataset = DecisionEvaluationDataset.model_validate(
        _strict_json_load((config_path.parent / config.dataset).resolve())
    )
    measurements = DecisionEvaluationMeasurements.model_validate(
        _strict_json_load((config_path.parent / config.measurements).resolve())
    )
    return config, dataset, measurements


def _write_json(path: Path, payload: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
    )


def _git_commit(repo_root: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _nearest_rank_p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, (95 * len(ordered) + 99) // 100 - 1)
    return ordered[index]


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _wilson_95(numerator: int, denominator: int) -> dict[str, float]:
    """Return a dependency-free Wilson score interval for a binomial rate."""
    if denominator == 0:
        return {"lower": 0.0, "upper": 1.0}
    z = 1.959963984540054
    observed = numerator / denominator
    denominator_term = 1 + z * z / denominator
    center = (observed + z * z / (2 * denominator)) / denominator_term
    margin = (
        z
        * math.sqrt(
            observed * (1 - observed) / denominator
            + z * z / (4 * denominator * denominator)
        )
        / denominator_term
    )
    return {
        "lower": max(0.0, center - margin),
        "upper": min(1.0, center + margin),
    }


def _create_run_dir(output_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = output_root / f"{timestamp}-{uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def run_decision_evaluation(
    *,
    config_path: Path,
    repo_root: Path,
    max_cases: int | None = None,
) -> DecisionEvaluationSummary:
    """Score recorded pairs without invoking Runtime, Gateway, or any provider."""

    config_path = config_path.resolve()
    repo_root = repo_root.resolve()
    config, dataset, measurements = load_decision_evaluation_inputs(config_path)
    dataset_path = (config_path.parent / config.dataset).resolve()
    measurements_path = (config_path.parent / config.measurements).resolve()
    output_root = (config_path.parent / config.output_root).resolve()

    selected_cases = [case for case in dataset.cases if case.split in config.splits]
    selected_cases.sort(key=lambda case: case.case_id)
    if max_cases is not None:
        if max_cases < 1:
            raise DecisionEvaluationConfigurationError("max_cases must be positive")
        selected_cases = selected_cases[:max_cases]
    if not selected_cases:
        raise DecisionEvaluationConfigurationError("selected splits contain no cases")

    selected_ids = {case.case_id for case in selected_cases}
    dataset_ids = {case.case_id for case in dataset.cases}
    unknown_measurement_case_ids = sorted({
        record.case_id
        for record in measurements.records
        if record.case_id not in dataset_ids
    })
    selected_records = [
        record for record in measurements.records if record.case_id in selected_ids
    ]
    case_by_id = {case.case_id: case for case in selected_cases}
    expected_pairs = {
        (case.case_id, repetition)
        for case in selected_cases
        for repetition in range(config.repetitions)
    }
    actual_pairs = {(record.case_id, record.repetition) for record in selected_records}
    missing_pairs = sorted(expected_pairs - actual_pairs)
    unexpected_pairs = sorted(actual_pairs - expected_pairs)

    replaceable_cases = [case for case in selected_cases if not case.must_escalate]
    covered_replaceable = sum(
        case.expected_selected_id
        in {candidate.candidate_id for candidate in case.candidates}
        for case in replaceable_cases
    )
    mismatched_input_pairs = sorted(
        (record.case_id, record.repetition)
        for record in selected_records
        if record.decision_input_ref != case_by_id[record.case_id].decision_input_ref
    )
    raw_selected = [record for record in selected_records if record.provider_outcome == "selected"]
    raw_correct = sum(
        not case_by_id[record.case_id].must_escalate
        and record.selected_id == case_by_id[record.case_id].expected_selected_id
        for record in raw_selected
    )
    accepted = [record for record in selected_records if record.host_outcome == "selected"]
    erroneous_acceptances = [
        record
        for record in accepted
        if case_by_id[record.case_id].must_escalate
        or record.selected_id != case_by_id[record.case_id].expected_selected_id
    ]
    must_escalate_records = [
        record for record in selected_records if case_by_id[record.case_id].must_escalate
    ]
    escalated_required = sum(record.system2_invoked for record in must_escalate_records)
    actual_substitutions = [
        record
        for record in accepted
        if not case_by_id[record.case_id].must_escalate
        and record.selected_id == case_by_id[record.case_id].expected_selected_id
        and not record.system2_invoked
    ]

    decision_latencies = [record.decision_total_elapsed_ms for record in selected_records]
    baseline_latencies = [record.system2_only_elapsed_ms for record in selected_records]
    decision_mean = statistics.fmean(decision_latencies) if decision_latencies else 0.0
    baseline_mean = statistics.fmean(baseline_latencies) if baseline_latencies else 0.0
    decision_p95 = _nearest_rank_p95(decision_latencies)
    baseline_p95 = _nearest_rank_p95(baseline_latencies)
    observed_categories = sorted({item for case in selected_cases for item in case.categories})
    missing_categories = sorted(REQUIRED_HELD_OUT_CATEGORIES - set(observed_categories))
    category_distribution = dict(sorted(Counter(
        category
        for case in selected_cases
        for category in case.categories
    ).items()))
    provider_versions = sorted({
        (record.provider, record.requested_model, record.model_version)
        for record in selected_records
    }, key=lambda item: tuple(value or "" for value in item))
    system2_versions = sorted({
        (
            record.system2_provider,
            record.system2_model,
            record.system2_model_version,
        )
        for record in selected_records
    }, key=lambda item: tuple(value or "" for value in item))
    outcome_counts = Counter(record.host_outcome for record in selected_records)
    provider_outcome_counts = Counter(
        record.provider_outcome for record in selected_records
    )

    checks = {
        "measured_evidence": measurements.evidence_mode == "measured",
        "held_out_only": config.splits == ("held_out",),
        "full_case_selection": max_cases is None,
        "complete_pairs": not missing_pairs and not unexpected_pairs,
        "known_measurement_cases": not unknown_measurement_case_ids,
        "paired_input_refs_match": not mismatched_input_pairs,
        "required_category_coverage": not missing_categories,
        "planned_sample_size_reached": (
            len(selected_cases) >= dataset.planned_held_out_cases
        ),
        "independent_label_review": dataset.labeler_id != dataset.reviewer_id,
        "actual_model_version_recorded": all(
            record.model_version for record in selected_records
        ),
        "single_provider_model_version": len(provider_versions) == 1,
        "system2_model_version_recorded": all(
            record.system2_model_version for record in selected_records
        ),
        "single_system2_model_version": len(system2_versions) == 1,
        "acceptance_policy_recorded": bool(config.acceptance_policy_ref),
        "candidate_coverage_complete": covered_replaceable == len(replaceable_cases),
        "zero_erroneous_acceptances": not erroneous_acceptances,
        "mandatory_escalation_recall_complete": (
            bool(must_escalate_records)
            and escalated_required == len(must_escalate_records)
        ),
        "actual_substitution_observed": bool(actual_substitutions),
        "paired_latency_mean_improved": decision_mean < baseline_mean,
        "paired_latency_p95_not_worse": decision_p95 <= baseline_p95,
    }
    active_eligible = all(checks.values())
    ineligibility_reasons = [name for name, passed in checks.items() if not passed]

    metrics = {
        "version": "jev_decision_evaluation_metrics_v1",
        "attempts": len(selected_records),
        "case_count": len(selected_cases),
        "candidate_coverage": {
            "covered": covered_replaceable,
            "replaceable_cases": len(replaceable_cases),
            "rate": _ratio(covered_replaceable, len(replaceable_cases)),
            "wilson_95": _wilson_95(covered_replaceable, len(replaceable_cases)),
        },
        "raw_selection_accuracy": {
            "correct": raw_correct,
            "selected": len(raw_selected),
            "rate": _ratio(raw_correct, len(raw_selected)),
            "wilson_95": _wilson_95(raw_correct, len(raw_selected)),
        },
        "policy_acceptance": {
            "accepted": len(accepted),
            "attempts": len(selected_records),
            "rate": _ratio(len(accepted), len(selected_records)),
            "wilson_95": _wilson_95(len(accepted), len(selected_records)),
        },
        "erroneous_acceptance": {
            "count": len(erroneous_acceptances),
            "accepted": len(accepted),
            "rate": _ratio(len(erroneous_acceptances), len(accepted)),
            "wilson_95": _wilson_95(len(erroneous_acceptances), len(accepted)),
            "case_ids": sorted({record.case_id for record in erroneous_acceptances}),
        },
        "mandatory_escalation_recall": {
            "recalled": escalated_required,
            "required": len(must_escalate_records),
            "rate": _ratio(escalated_required, len(must_escalate_records)),
            "wilson_95": _wilson_95(
                escalated_required, len(must_escalate_records)
            ),
        },
        "actual_substitution": {
            "count": len(actual_substitutions),
            "attempts": len(selected_records),
            "rate": _ratio(len(actual_substitutions), len(selected_records)),
            "wilson_95": _wilson_95(
                len(actual_substitutions), len(selected_records)
            ),
        },
        "paired_latency_ms": {
            "decision_mean": decision_mean,
            "system2_only_mean": baseline_mean,
            "decision_p95": decision_p95,
            "system2_only_p95": baseline_p95,
        },
        "wait_ms": {
            "tool_mean": statistics.fmean(
                record.tool_wait_ms for record in selected_records
            ) if selected_records else 0.0,
            "operator_mean": statistics.fmean(
                record.operator_wait_ms for record in selected_records
            ) if selected_records else 0.0,
        },
        "host_outcomes": dict(sorted(outcome_counts.items())),
        "provider_outcomes": dict(sorted(provider_outcome_counts.items())),
        "observed_categories": observed_categories,
        "case_distribution": {
            "by_split": dict(sorted(Counter(case.split for case in selected_cases).items())),
            "by_category": category_distribution,
            "unique_families": len({case.family_id for case in selected_cases}),
        },
        "provider_model_versions": [
            {"provider": provider, "requested_model": requested, "model_version": version}
            for provider, requested, version in provider_versions
        ],
        "system2_model_versions": [
            {"provider": provider, "model": model, "model_version": version}
            for provider, model, version in system2_versions
        ],
        "missing_pairs": [list(pair) for pair in missing_pairs],
        "unexpected_pairs": [list(pair) for pair in unexpected_pairs],
        "mismatched_input_pairs": [list(pair) for pair in mismatched_input_pairs],
        "unknown_measurement_case_ids": unknown_measurement_case_ids,
        "missing_required_categories": missing_categories,
        "active_eligibility_checks": checks,
        "active_eligible": active_eligible,
        "active_ineligibility_reasons": ineligibility_reasons,
    }

    run_dir = _create_run_dir(output_root)
    _write_json(run_dir / "input_config.json", config.model_dump(mode="json"))
    _write_json(run_dir / "input_dataset.json", dataset.model_dump(mode="json"))
    _write_json(
        run_dir / "input_measurements.json",
        measurements.model_dump(mode="json"),
    )
    _write_json(run_dir / "metrics.json", metrics)
    report = {
        "version": "jev_decision_acceptance_report_v1",
        "active_eligible": active_eligible,
        "decision_point": "query_input_selection",
        "dataset_name": dataset.name,
        "dataset_version": dataset.dataset_version,
        "evidence_mode": measurements.evidence_mode,
        "acceptance_policy_ref": config.acceptance_policy_ref,
        "provider_model_versions": metrics["provider_model_versions"],
        "system2_model_versions": metrics["system2_model_versions"],
        "metrics_path": "metrics.json",
        "ineligibility_reasons": ineligibility_reasons,
    }
    _write_json(run_dir / "acceptance_report.json", report)
    manifest = {
        "version": "jev_decision_evaluation_run_v1",
        "status": "completed",
        "run_id": run_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(repo_root),
        "config_path": str(config_path),
        "dataset_path": str(dataset_path),
        "dataset_name": dataset.name,
        "dataset_version": dataset.dataset_version,
        "sampling_plan_ref": dataset.sampling_plan_ref,
        "labeling_protocol_ref": dataset.labeling_protocol_ref,
        "labeler_id": dataset.labeler_id,
        "reviewer_id": dataset.reviewer_id,
        "planned_held_out_cases": dataset.planned_held_out_cases,
        "measurements_path": str(measurements_path),
        "evidence_mode": measurements.evidence_mode,
        "acceptance_policy_ref": config.acceptance_policy_ref,
        "splits": list(config.splits),
        "repetitions": config.repetitions,
        "random_seed": None,
        "runtime": {"python_version": sys.version.split()[0]},
        "selected_case_ids": [case.case_id for case in selected_cases],
        "partial_case_selection": max_cases is not None,
        "input_snapshots": {
            "config": "input_config.json",
            "dataset": "input_dataset.json",
            "measurements": "input_measurements.json",
        },
        "metrics_path": "metrics.json",
        "acceptance_report_path": "acceptance_report.json",
        "active_eligible": active_eligible,
        "active_ineligibility_reasons": ineligibility_reasons,
    }
    _write_json(run_dir / "run_manifest.json", manifest)
    exit_code = 0 if active_eligible or measurements.evidence_mode == "fixture" else 2
    return DecisionEvaluationSummary(
        run_dir=run_dir,
        status="completed",
        active_eligible=active_eligible,
        exit_code=exit_code,
    )


__all__ = [
    "DecisionEvaluationCase",
    "DecisionEvaluationConfig",
    "DecisionEvaluationConfigurationError",
    "DecisionEvaluationDataset",
    "DecisionEvaluationMeasurements",
    "DecisionEvaluationSummary",
    "DecisionMeasurement",
    "load_decision_evaluation_inputs",
    "run_decision_evaluation",
]
