#!/usr/bin/env python3
"""Freeze complete API annotations beside unchanged independent game targets."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from assemble_pipeline_dataset import assemble, load_rows
from train_pipeline_decisions import SPLITS


def json_value_equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if type(left) in {int, float} and type(right) in {int, float}:
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_value_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(json_value_equal(a, b) for a, b in zip(left, right))
    return left == right


def restore_raw_rng_metadata(raw, annotated):
    """Node parses JSON numbers as doubles; keep the authoritative uint64 RNG.

    This field is never part of the rendered request. Only the known RNG field
    may differ by an equivalent IEEE-754 round trip; every other raw field is
    subsequently checked by assemble(). No probability or model input is changed.
    """
    row = copy.deepcopy(annotated)
    original = raw.get("metadata", {}).get("environment_state", {}).get("rng_state")
    copied = row.get("metadata", {}).get("environment_state", {}).get("rng_state")
    changed = original != copied
    if changed:
        if type(original) is not int or type(copied) is not int or abs(original) <= 2**53 or float(original) != float(copied):
            raise ValueError("RNG metadata changed beyond a JSON-number round trip")
        row["metadata"]["environment_state"]["rng_state"] = original
    for key, value in raw.items():
        if key not in row or not json_value_equal(value, row[key]):
            raise ValueError(f"Annotation changed authoritative raw field {key}")
    payload = {"state": raw["state"], "questions": raw["questions"]}
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if row.get("input_sha256") != digest:
        raise ValueError("Saved annotation input digest differs from the rendered request")
    return row, changed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    paths = [args.input_dir / f"{split}.jsonl" for split in SPLITS] + [args.input_dir / "labeled.jsonl"]
    snapshots = {str(path): path.read_bytes() for path in paths}
    raw = [row for path in paths[:-1] for row in load_rows(path)]
    labels = load_rows(paths[-1])
    if {r["id"] for r in raw} != {r["id"] for r in labels}:
        raise ValueError("Annotations must cover exactly the frozen raw-state cohort")
    by_id = {row["id"]: row for row in raw}
    normalized, restored = [], []
    for label in labels:
        row, changed = restore_raw_rng_metadata(by_id[label["id"]], label)
        normalized.append(row)
        if changed:
            restored.append(row["id"])
    rows, report = assemble([], raw, normalized, [])
    if any(path.read_bytes() != snapshots[str(path)] for path in paths):
        raise ValueError("Inputs changed during assembly; stop collection before freezing")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("Use a new empty output directory")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        selected = [r for r in rows if r["split"] == split]
        (args.output_dir / f"{split}.jsonl").write_text("".join(json.dumps(r, allow_nan=False) + "\n" for r in selected))
    report.update(schema="nanojev-scaled-annotations-v1", complete_state_coverage=True,
                  raw_uint64_rng_metadata_preserved_for=restored,
                  rng_metadata_note="Only the original raw RNG integer is retained after a verified JavaScript double round trip; model inputs and targets are unchanged.",
                  source_sha256={name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()},
                  output_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.output_dir.glob("*.jsonl")})
    (args.output_dir / "manifest.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"states": len(rows), "questions": sum(len(r["questions"]) for r in rows),
                      "output_dir": str(args.output_dir), "complete_state_coverage": True}))


if __name__ == "__main__":
    main()
