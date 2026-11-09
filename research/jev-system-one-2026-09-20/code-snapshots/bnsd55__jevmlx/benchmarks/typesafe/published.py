"""Published-model agreement from TypeSafe data: what evals.typesafe.ai shows.

The fetcher (``benchmarks.typesafe.fetch``) stores each published model's raw
answer per question in ``meta.models`` (``{field_name: {model: raw}}``). This
module computes what the TypeSafe leaderboard shows for those published
models: each model's agreement with the consensus label — over the STRICT
COMMON SUBSET of questions every published model answered that also have a
non-ambiguous consensus. The subset definition is part of the output so our
own runs can be scored on the identical subset.

Answer-value semantics (from the published viewer payload, see fetch.py):

- boolean (``noul``) fields: the raw value is the model's probability of
  ``true``; the model's picked answer is ``raw >= 0.5``.
- enum ``choice`` fields with string raws: the raw value is the picked
  choice; agreement is exact match with the consensus label.
- enum ``score`` fields (choices ``0``..``3``) with float raws: the raw is
  the model's continuous score; the picked answer is ``round(raw)`` (the
  published probabilities' argmax equals ``round(score)`` on 43/47 sampled
  answers; ties differ but the site's own display uses the score value).

Usage:
    python -m benchmarks.typesafe.published --data cases.jsonl \\
        --out published_agreement.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

__all__ = ["common_subset_field_ids", "published_agreement", "main"]

# Score questions are answered on a fixed 0-3 scale (fetch.SCORE_CHOICES).
SCORE_CHOICES = ("0", "1", "2", "3")


def _field_type(record: dict, field: str) -> str | None:
    spec = (record.get("schema") or {}).get(field) or {}
    return spec.get("type")


def _is_score_field(record: dict, field: str) -> bool:
    """Score questions are enums whose choices are the fixed 0-3 rubric."""
    spec = record.get("schema", {}).get(field) or {}
    return tuple(spec.get("choices") or ()) == SCORE_CHOICES


def _model_pick(raw, field_type: str | None, is_score: bool):
    """The model's picked answer for one field, in consensus-label space."""
    if raw is None:
        return None
    if is_score and isinstance(raw, (int, float)):
        return str(int(round(raw)))
    if field_type == "boolean" and isinstance(raw, (int, float)):
        return bool(raw >= 0.5)
    return raw


def _field_key(record_id: str, field: str) -> str:
    """Unique id for one (record, field) pair.

    Field names repeat across records (same qid at multiple workflow steps),
    so bare names do not identify a question; ``<record_id>::<field>`` does.
    """
    return f"{record_id}::{field}"


def common_subset_field_ids(records: list[dict]) -> list[str]:
    """Field ids of the STRICT COMMON SUBSET, in stable order.

    The subset is every (record, field) question that (a) every published
    model found in ``meta.models`` answered and (b) has a non-ambiguous
    consensus (fetcher's ``meta.ambiguous`` flag empty for that field and a
    consensus label present). Returns ``["<record_id>::<field_name>", ...]``
    sorted; the same ids the output JSON's ``subset.field_ids`` carries, so
    ``jevmlx report`` / the leaderboard can score our own runs on the
    identical subset.
    """
    # Pass 1: model names seen anywhere, and per-field answer bookkeeping.
    # meta.models maps field_name -> {model: raw} (the fetcher's shape).
    model_names: set[str] = set()
    answered: dict[str, set[str]] = defaultdict(set)  # key -> models that answered
    eligible: dict[str, bool] = {}
    workflow_of: dict[str, str] = {}
    for record in records:
        models_meta = record.get("meta", {}).get("models") or {}
        labels = record.get("labels") or {}
        ambiguous = set(record.get("meta", {}).get("ambiguous") or [])
        for field, answers in models_meta.items():
            for model, raw in answers.items():
                model_names.add(model)
                if raw is None:
                    continue
                key = _field_key(record.get("id", ""), field)
                answered[key].add(model)
        for field, label in labels.items():
            if label is None or field in ambiguous:
                continue
            eligible[_field_key(record.get("id", ""), field)] = True
            workflow_of[_field_key(record.get("id", ""), field)] = str(record.get("workflow", ""))
    if not model_names:
        return []
    # Pass 2: keep fields answered by EVERY published model and eligible.
    subset = [key for key in sorted(eligible) if answered.get(key, set()) >= model_names]
    return subset


def published_agreement(records: list[dict]) -> dict:
    """Published models' agreement with the consensus over the common subset.

    Returns the output-schema dict: ``subset`` (definition: n_fields,
    n_cases, workflows, field_ids) and ``models`` (one row per published
    model name found in ``meta.models``, names as published; each with
    agreed/total/agreement and by_workflow rates). Models are sorted by name
    for stable output.
    """
    subset_ids = common_subset_field_ids(records)
    by_key: dict[str, tuple[dict, str]] = {}
    for record in records:
        for field in record.get("labels") or {}:
            by_key.setdefault(_field_key(record.get("id", ""), field), (record, field))

    model_names: set[str] = set()
    for record in records:
        for answers in (record.get("meta", {}).get("models") or {}).values():
            model_names.update(answers.keys())

    # Per model: agreed/total per field id in the subset, plus workflow.
    agreed: dict[str, int] = {m: 0 for m in model_names}
    total: dict[str, int] = {m: 0 for m in model_names}
    by_workflow: dict[str, dict[str, list[int]]] = {
        m: defaultdict(lambda: [0, 0]) for m in model_names
    }
    for key in subset_ids:
        record, field = by_key[key]
        label = record["labels"][field]
        models_meta = record.get("meta", {}).get("models") or {}
        workflow = str(record.get("workflow", ""))
        is_score = _is_score_field(record, field)
        ftype = _field_type(record, field)
        for model, raw in models_meta.get(field, {}).items():
            if raw is None:
                continue
            pick = _model_pick(raw, ftype, is_score)
            total[model] += 1
            by_workflow[model][workflow][1] += 1
            if pick == label:
                agreed[model] += 1
                by_workflow[model][workflow][0] += 1

    models_out = []
    for model in sorted(model_names):
        n_total = total[model]
        models_out.append(
            {
                "name": model,
                "agreed": agreed[model],
                "total": n_total,
                "agreement": (agreed[model] / n_total) if n_total else None,
                "by_workflow": {
                    workflow: {
                        "agreed": pair[0],
                        "total": pair[1],
                        "agreement": (pair[0] / pair[1]) if pair[1] else None,
                    }
                    for workflow, pair in sorted(by_workflow[model].items())
                },
            }
        )

    # Subset definition: n_cases counts distinct record ids that own subset
    # fields; workflows sorted for stable output.
    subset_records = {key.split("::", 1)[0] for key in subset_ids}
    subset_workflows = sorted(
        {str(by_key[key][0].get("workflow", "")) for key in subset_ids if key in by_key}
    )
    return {
        "subset": {
            "n_fields": len(subset_ids),
            "n_cases": len(subset_records),
            "workflows": subset_workflows,
            "field_ids": subset_ids,
        },
        "models": models_out,
    }


def _print_table(result: dict) -> None:
    subset = result["subset"]
    print(
        f"common subset: {subset['n_fields']} fields over "
        f"{subset['n_cases']} cases; workflows: {', '.join(subset['workflows'])}"
    )
    header = f"{'model':<20} {'agreed':>7} {'total':>7} {'agreement':>10}"
    print(header)
    print("-" * len(header))
    for row in result["models"]:
        rate = "—" if row["agreement"] is None else f"{row['agreement']:.3f}"
        print(f"{row['name']:<20} {row['agreed']:>7} {row['total']:>7} {rate:>10}")
    for row in result["models"]:
        for workflow, stats in row["by_workflow"].items():
            rate = "—" if stats["agreement"] is None else f"{stats['agreement']:.3f}"
            print(f"  {row['name']} / {workflow}: {stats['agreed']}/{stats['total']} ({rate})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.typesafe.published",
        description="Published-model agreement with the TypeSafe consensus "
        "over the strict common subset.",
    )
    parser.add_argument("--data", required=True, help="cases.jsonl from the fetcher")
    parser.add_argument("--out", required=True, help="output JSON path")
    args = parser.parse_args(argv)

    records = [
        json.loads(line)
        for line in Path(args.data).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = published_agreement(records)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _print_table(result)
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
