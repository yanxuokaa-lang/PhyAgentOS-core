"""Complete dataset preparation pipeline for training Von's native decision models.

Aggregates:
1. ANLI (Rounds 1, 2, 3) - 162,865 adversarial multi-hop pairs
2. WANLI (Worker-AI NLI) - 102,885 high-disagreement reasoning pairs
3. MultiNLI (MNLI)       - 392,702 multi-genre reasoning pairs
4. SNLI                  - 550,152 sentence-level entailment pairs
Total candidate pool: > 1.2 Million decision pairs.
"""

import argparse
import json
import os
import random
from typing import Dict, List, Optional
from datasets import load_dataset


def map_nli_pair(premise: str, hypothesis: str, label_num: int, source: str) -> Optional[dict]:
    p = (premise or "").strip()
    h = (hypothesis or "").strip()

    if not p or not h or label_num not in (0, 1, 2):
        return None

    # Standard NLI mapping: 0 -> entailment, 1 -> neutral, 2 -> contradiction
    label_map = {0: "supported", 1: "insufficient", 2: "contradicted"}
    target = label_map[label_num]

    return {
        "state": p,
        "question": f"Is the following claim supported, contradicted, or is evidence insufficient: '{h}'?",
        "options": [
            {"id": "supported", "description": f"The evidence establishes that: {h}."},
            {"id": "contradicted", "description": f"The evidence contradicts that: {h}."},
            {"id": "insufficient", "description": f"The evidence is insufficient to verify: {h}."},
        ],
        "label": target,
        "source": source,
    }


def build_corpus(
    output_dir: str = "data",
    max_train_samples: int = 500000,
    val_samples: int = 5000,
    seed: int = 42,
    include_mnli: bool = True,
    include_snli: bool = True,
):
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    records: List[dict] = []

    # 1. ANLI (Hard Adversarial Multi-hop)
    print("Fetching ANLI (R1, R2, R3)...")
    for r in ["train_r1", "train_r2", "train_r3"]:
        split = load_dataset("facebook/anli", split=r)
        for row in split:
            rec = map_nli_pair(row.get("premise"), row.get("hypothesis"), row.get("label"), f"anli_{r}")
            if rec:
                records.append(rec)
    print(f"  -> Total with ANLI: {len(records)} records")

    # 2. WANLI (Worker-AI NLI)
    print("Fetching WANLI...")
    wanli_train = load_dataset("alisawuffles/WANLI", split="train")
    gold_to_num = {"entailment": 0, "neutral": 1, "contradiction": 2}
    for row in wanli_train:
        g = (row.get("gold") or "").lower().strip()
        num = gold_to_num.get(g, -1)
        rec = map_nli_pair(row.get("premise"), row.get("hypothesis"), num, "wanli")
        if rec:
            records.append(rec)
    print(f"  -> Total with WANLI: {len(records)} records")

    # 3. MultiNLI (Diverse Genres: Fiction, Government, Slate, Telephone)
    if include_mnli:
        print("Fetching MultiNLI (MNLI)...")
        mnli_train = load_dataset("nyu-mll/multi_nli", split="train")
        for row in mnli_train:
            rec = map_nli_pair(row.get("premise"), row.get("hypothesis"), row.get("label"), "mnli")
            if rec:
                records.append(rec)
        print(f"  -> Total with MultiNLI: {len(records)} records")

    # 4. SNLI (Stanford Grounded NLI)
    if include_snli:
        print("Fetching SNLI...")
        snli_train = load_dataset("stanfordnlp/snli", split="train")
        for row in snli_train:
            rec = map_nli_pair(row.get("premise"), row.get("hypothesis"), row.get("label"), "snli")
            if rec:
                records.append(rec)
        print(f"  -> Total with SNLI: {len(records)} records")

    print(f"\nTotal raw decision candidates collected: {len(records):,}")

    # Shuffle
    random.shuffle(records)

    # Balance classes (supported, contradicted, insufficient)
    by_label: Dict[str, List[dict]] = {"supported": [], "contradicted": [], "insufficient": []}
    for r in records:
        lbl = r["label"]
        if lbl in by_label:
            by_label[lbl].append(r)

    print(f"Raw Class distribution: supported={len(by_label['supported']):,}, contradicted={len(by_label['contradicted']):,}, insufficient={len(by_label['insufficient']):,}")

    min_count = min(len(v) for v in by_label.values())
    if max_train_samples > 0:
        per_class_limit = min(min_count, (max_train_samples + val_samples) // 3)
    else:
        per_class_limit = min_count

    balanced: List[dict] = []
    for lbl in ["supported", "contradicted", "insufficient"]:
        balanced.extend(by_label[lbl][:per_class_limit])

    random.shuffle(balanced)

    val_set = balanced[:val_samples]
    train_set = balanced[val_samples:]

    if max_train_samples > 0 and len(train_set) > max_train_samples:
        train_set = train_set[:max_train_samples]

    train_path = os.path.join(output_dir, "train.jsonl")
    val_path = os.path.join(output_dir, "val.jsonl")

    print(f"Exporting train set ({len(train_set):,} rows)...")
    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_set:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Exporting val set ({len(val_set):,} rows)...")
    with open(val_path, "w", encoding="utf-8") as f:
        for item in val_set:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\nCorpus build complete:")
    print(f"  -> Train set: {len(train_set):,} rows saved to {train_path}")
    print(f"  -> Val set:   {len(val_set):,} rows saved to {val_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build training corpus from ANLI + WANLI + MultiNLI + SNLI")
    parser.add_argument("--output_dir", type=str, default="data")
    parser.add_argument("--max_train", type=int, default=500000, help="0 for full balanced corpus (~1M+ rows)")
    parser.add_argument("--val_samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no_mnli", action="store_true", help="Skip MultiNLI")
    parser.add_argument("--no_snli", action="store_true", help="Skip SNLI")
    args = parser.parse_args()

    build_corpus(
        output_dir=args.output_dir,
        max_train_samples=args.max_train,
        val_samples=args.val_samples,
        seed=args.seed,
        include_mnli=not args.no_mnli,
        include_snli=not args.no_snli,
    )
