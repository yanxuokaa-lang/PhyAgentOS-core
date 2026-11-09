#!/usr/bin/env python3
"""Overlay available labels onto all raw game records; preserve every independent gold target.

Default mode only checks source records. --freeze explicitly writes the immutable
merged input and its manifest after labeling has finished; no API calls or GPU work.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from predict_toy_decisions import prepare_examples, reject_nonfinite, unique_object
from train_pipeline_decisions import SPLITS, data_schema_summary, validate_training_row


def load_rows(path):
    rows, seen = [], set()
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_nonfinite)
        if row["id"] in seen:
            raise ValueError(f"Duplicate ID in {path}:{i}: {row['id']}")
        seen.add(row["id"])
        validate_training_row(row)
        rows.append(row)
    return rows


def assemble(workflows, games_raw, game_labels, toy):
    raw = {r["id"]: r for r in games_raw}
    labels = {r["id"]: r for r in game_labels}
    unknown = set(labels) - set(raw)
    if unknown:
        raise ValueError(f"Game label IDs absent from the raw source: {sorted(unknown)[:3]}")
    games = []
    for row in games_raw:
        merged = dict(row)
        labelled = labels.get(row["id"])
        if labelled is not None:
            for key, value in row.items():
                # Candidate order affects serialization, so preserve and compare JSON insertion order.
                same = (json.dumps(labelled.get(key), ensure_ascii=False) == json.dumps(value, ensure_ascii=False)
                        if key in {"state", "questions"} else labelled.get(key) == value)
                if not same:
                    raise ValueError(f"Label source differs from raw record {row['id']} field {key}")
            for key in ("teacher", "input_sha256", "labeled_at"):
                if key in labelled:
                    merged[key] = labelled[key]
        games.append(merged)
    rows = workflows + games + toy
    ids, state_splits, source_splits = set(), {}, {}
    coverage = {}
    for row in rows:
        if row["id"] in ids:
            raise ValueError(f"Record ID collides across sources: {row['id']}")
        ids.add(row["id"])
        for key, registry in ((row["state_id"], state_splits),
                              (row.get("metadata", {}).get("source_group_id"), source_splits)):
            if key is not None:
                if key in registry and registry[key] != row["split"]:
                    raise ValueError(f"State/source group leaks across splits: {key}")
                registry[key] = row["split"]
        targets = validate_training_row(row)
        for qid, t in targets.items():
            q = row["questions"][qid]
            k = 2 if q["type"] == "boolean" else len(q["criteria"])
            group = (row["split"], row["family_id"], q["type"], k)
            bucket = coverage.setdefault(group, Counter())
            bucket["questions"] += 1
            bucket["gold_distribution_usable"] += t["gold_distribution_probs"] is not None
            bucket["teacher_response_present"] += t["teacher_raw_mapping"] is not None
            bucket["teacher_usable"] += t["teacher_probs"] is not None
            bucket["teacher_quarantined"] += t["teacher_raw_mapping"] is not None and t["teacher_probs"] is None
            bucket["teacher_missing"] += t["teacher_raw_mapping"] is None
    outer_fields = {"id", "state_id", "family_id", "split", "state", "questions", "gold", "gold_probs",
                    "gold_probs_kind", "gold_label_kind", "optimal_actions", "metadata", "teacher"}
    teacher_fields = {"native_probs", "rounding", "label_source", "target_kind", "model"}
    metadata_fields = {"source", "license", "source_group_id", "template_id", "language", "environment_state"}
    removed = {"record_fields": set(), "teacher_fields": set(), "metadata_fields": set()}
    minimized = []
    for row in rows:
        removed["record_fields"].update(set(row) - outer_fields)
        item = {k: v for k, v in row.items() if k in outer_fields}
        if "teacher" in item:
            removed["teacher_fields"].update(set(item["teacher"]) - teacher_fields)
            item["teacher"] = {k: v for k, v in item["teacher"].items() if k in teacher_fields}
        if "metadata" in item:
            removed["metadata_fields"].update(set(item["metadata"]) - metadata_fields)
            item["metadata"] = {k: v for k, v in item["metadata"].items() if k in metadata_fields}
        validate_training_row(item)
        minimized.append(item)
    manifest = {"schema_version": "openjev-pipeline-assembly-v1", "split_transform": "none",
                "source_states": {"workflows": len(workflows), "games_raw": len(games_raw),
                                  "games_labeled_available": len(game_labels), "legacy_toy": len(toy)},
                **data_schema_summary(rows),
                "teacher_coverage_by_split_family_type_K": [
                    {"split": g[0], "family_id": g[1], "type": g[2], "K": g[3], **dict(c)}
                    for g, c in sorted(coverage.items())],
                "unlabeled_game_ids": sorted(set(raw) - set(labels)),
                "teacher_failures_remove_no_gold_records": True,
                "split_state_and_source_group_leakage": False,
                "data_minimization": {"removed_fields": {k: sorted(v) for k, v in removed.items()},
                                      "teacher_fields_retained": sorted(teacher_fields),
                                      "purpose": "Only synthetic training inputs, programmatic targets, source groups and authorized teacher distributions; no provider metadata, usage, account/call IDs or credentials"}}
    return minimized, manifest


def token_audit(rows, tokenizer_dir, max_length, token_budget):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir), local_files_only=True, trust_remote_code=False)
    maxima = {"max_path_tokens": 0, "max_complete_question_padded_tokens": 0, "max_candidate_paths": 0}
    worst = {}
    by_family = {}
    for row in rows:
        examples = prepare_examples({"states": [{k: row[k] for k in ("id", "state", "questions")}]}, tokenizer, max_length)
        for ex in examples:
            n = len(ex["leaf_tokens"])
            length = max(map(len, ex["leaf_tokens"]))
            values = {"max_path_tokens": length, "max_complete_question_padded_tokens": n * length,
                      "max_candidate_paths": n}
            if token_budget and n * length > token_budget:
                raise ValueError(f"Question {ex['id']} needs {n*length} tokens, over {token_budget}; no truncation")
            fam = by_family.setdefault(row["family_id"], {"questions": 0, **dict.fromkeys(maxima, 0)})
            fam["questions"] += 1
            for key, value in values.items():
                fam[key] = max(fam[key], value)
                if value > maxima[key]:
                    maxima[key], worst[key] = value, ex["id"]
    return {**maxima, "worst_question_ids": worst, "by_family": by_family,
            "max_length_limit": max_length, "complete_question_token_budget": token_budget,
            "tokenizer_directory": str(tokenizer_dir), "gpu_calls": 0, "truncated_records": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workflows", required=True, type=Path)
    p.add_argument("--games-raw", required=True, type=Path)
    p.add_argument("--games-labels", required=True, type=Path)
    p.add_argument("--toy", required=True, type=Path)
    p.add_argument("--freeze", action="store_true", help="Write final input only after operator confirms label collection ended")
    p.add_argument("--output-dir", type=Path, default=Path("research/private_pipeline_v2"))
    p.add_argument("--report", type=Path, help="Optional preflight metadata report; no merged records are written")
    p.add_argument("--expected-states", type=int, default=2312)
    p.add_argument("--expected-questions", type=int, default=6936)
    p.add_argument("--tokenizer-dir", type=Path, help="Optional local-only CPU tokenizer audit")
    p.add_argument("--max-length", type=int, default=512)
    p.add_argument("--max-microbatch-tokens", type=int, default=6000)
    args = p.parse_args()
    paths = {"workflows": args.workflows, "games_raw": args.games_raw, "games_labels": args.games_labels, "toy": args.toy}
    snapshots = {key: path.read_bytes() for key, path in paths.items()}
    rows, manifest = assemble(*(load_rows(paths[key]) for key in ("workflows", "games_raw", "games_labels", "toy")))
    # Detect concurrent collection between the snapshot digest and parsing; rerun preflight, never silently freeze changing input.
    if any(path.read_bytes() != snapshots[key] for key, path in paths.items()):
        raise ValueError("A source changed during assembly; freeze only after collection ends")
    questions = sum(len(row["questions"]) for row in rows)
    if len(rows) != args.expected_states or questions != args.expected_questions:
        raise ValueError(f"Unexpected state/question count: {len(rows)}/{questions}")
    manifest.update(source_sha256={k: hashlib.sha256(v).hexdigest() for k, v in snapshots.items()},
                    source_paths={k: str(v) for k, v in paths.items()}, final_frozen=bool(args.freeze))
    if args.tokenizer_dir:
        manifest["token_audit"] = token_audit(rows, args.tokenizer_dir, args.max_length, args.max_microbatch_tokens)
    if args.freeze:
        destination = args.output_dir / "merged.jsonl"
        if destination.exists() or (args.output_dir / "manifest.json").exists():
            raise ValueError("Frozen dataset exists; refusing to overwrite")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        data = "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows)
        destination.write_text(data, encoding="utf-8")
        manifest["merged_sha256"] = hashlib.sha256(data.encode("utf-8")).hexdigest()
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("source_states", "records", "questions_by_split", "eligible_by_split_objective", "final_frozen")}, ensure_ascii=False))
    if "token_audit" in manifest:
        print(json.dumps(manifest["token_audit"], ensure_ascii=False))


if __name__ == "__main__":
    main()
