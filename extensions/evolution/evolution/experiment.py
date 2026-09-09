"""Reproducible artifact writer for offline evolution evaluation."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from uuid import uuid4

from pydantic import Field

from evolution.api import EvaluationReceipt, EvolutionModel
from evolution.evaluation import EvaluationDecision, SelectionPolicy
from evolution.observation import FutureUseComparison


class EvaluationRunManifest(EvolutionModel):
    run_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    created_at: datetime
    code_revision: str = Field(min_length=1, max_length=200)
    config_ref: str = Field(min_length=1, max_length=1000)
    random_seed: int
    dataset_name: str = Field(min_length=1, max_length=300)
    dataset_version: str = Field(min_length=1, max_length=300)
    checkpoint_ref: str | None = Field(default=None, max_length=1000)
    task_order: tuple[str, ...] = ()
    method_ids: tuple[str, ...] = Field(min_length=1)
    selection_policy: SelectionPolicy


@dataclass(frozen=True)
class EvaluationArtifactPaths:
    run_dir: Path
    manifest: Path
    receipts: Path
    decisions: Path
    future_use: Path
    metrics: Path


def new_evaluation_manifest(
    *,
    slug: str,
    code_revision: str,
    config_ref: str,
    random_seed: int,
    dataset_name: str,
    dataset_version: str,
    method_ids: tuple[str, ...],
    selection_policy: SelectionPolicy,
    checkpoint_ref: str | None = None,
    task_order: tuple[str, ...] = (),
    now: datetime | None = None,
) -> EvaluationRunManifest:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    safe_slug = slug.strip().replace(" ", "-")
    run_id = f"{timestamp:%Y%m%dT%H%M%SZ}-{safe_slug}-{uuid4().hex[:8]}"
    return EvaluationRunManifest(
        run_id=run_id,
        created_at=timestamp,
        code_revision=code_revision,
        config_ref=config_ref,
        random_seed=random_seed,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        checkpoint_ref=checkpoint_ref,
        task_order=task_order,
        method_ids=method_ids,
        selection_policy=selection_policy,
    )


class EvaluationArtifactWriter:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root).expanduser()

    def write(
        self,
        *,
        manifest: EvaluationRunManifest,
        receipts: Iterable[EvaluationReceipt],
        decisions: Iterable[EvaluationDecision],
        future_use: Iterable[FutureUseComparison] = (),
    ) -> EvaluationArtifactPaths:
        receipt_rows = tuple(receipts)
        decision_rows = tuple(decisions)
        future_rows = tuple(future_use)
        run_dir = self.output_root / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=False)

        paths = EvaluationArtifactPaths(
            run_dir=run_dir,
            manifest=run_dir / "manifest.json",
            receipts=run_dir / "receipts.jsonl",
            decisions=run_dir / "decisions.json",
            future_use=run_dir / "future-use.json",
            metrics=run_dir / "metrics.json",
        )
        self._write_json(paths.manifest, manifest.model_dump(mode="json"))
        paths.receipts.write_text(
            "".join(row.model_dump_json() + "\n" for row in receipt_rows),
            encoding="utf-8",
        )
        self._write_json(
            paths.decisions,
            [row.model_dump(mode="json") for row in decision_rows],
        )
        self._write_json(
            paths.future_use,
            [row.model_dump(mode="json") for row in future_rows],
        )
        counts = Counter(row.decision for row in decision_rows)
        self._write_json(
            paths.metrics,
            {
                "receipt_count": len(receipt_rows),
                "decision_count": len(decision_rows),
                "decision_counts": dict(sorted(counts.items())),
                "mean_utility": (
                    fmean(row.utility for row in decision_rows) if decision_rows else None
                ),
                "future_use_comparison_count": len(future_rows),
            },
        )
        return paths

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


__all__ = [
    "EvaluationArtifactPaths",
    "EvaluationArtifactWriter",
    "EvaluationRunManifest",
    "new_evaluation_manifest",
]
