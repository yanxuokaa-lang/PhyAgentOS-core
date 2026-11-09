"""Build the hard probe: Amazon ESCI, human-graded product relevance.

Why a second corpus. The 20 Newsgroups probe is topic membership, an easy
judgment, and its graded-ranking result was measured against a 3-level
sampling stratum rather than a human relevance grade. ESCI (Amazon's
Shopping Queries Dataset, Apache 2.0) gives each query-product pair one
of four human labels:

    E  Exact       the product matches the query, including stated attributes
    S  Substitute  partly fulfils the query; not exactly what was asked
    C  Complement  does not fulfil the query but goes with something that does
    I  Irrelevant  nothing to do with the query

The KDD Cup 2022 ranking task scores them E > S > C > I (gains 1.0, 0.1,
0.01, 0), so this is a genuine 4-level ordinal target for jev_score, and
E-vs-rest is a binary target for jev_bool with S as the built-in near
miss. Product search is also what people will actually run a semantic
ORDER BY on.

Selection: US locale, small_version (the "hard" queries; Amazon filtered
the easy ones out), test split, queries that carry all four labels.
Per query, up to 4 E, 4 S, 2 C, 2 I products, so every query contributes
the full ladder and C, which is 4.5% of the data, is not lost.

State is a JSON object, not a string, so the model can find the query
and the product fields by name. Description and bullets are truncated
to keep a row under ~700 tokens.

Run: python3 harness/corpus_esci.py [.data/esci/corpus.jsonl] [--queries 30] [--seed 0]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import duckdb

from client import repo_root

ESCI_DIR = repo_root() / ".data" / "esci"
EXAMPLES = ESCI_DIR / "shopping_queries_dataset_examples.parquet"
PRODUCTS = ESCI_DIR / "shopping_queries_dataset_products.parquet"
# The original products file is 1.1 GB behind GitHub LFS. A US-only
# re-encoding of it (spacemanidol/ESCI-product-dataset-corpus-us on
# Hugging Face; same product_id, title, description, bullets, brand,
# colour) is used when the original is absent, and which one was used is
# recorded in every row so the provenance travels with the corpus.
PRODUCTS_MIRROR = ESCI_DIR / "products_us_mirror.parquet"
CORPUS_OUT = ESCI_DIR / "corpus.jsonl"

GRADE = {"I": 0, "C": 1, "S": 2, "E": 3}
PER_QUERY = {"E": 4, "S": 4, "C": 2, "I": 2}
MAX_CHARS = {"product_description": 600, "product_bullet_point": 600}


def build(n_queries: int, seed: int) -> list[dict]:
    if not EXAMPLES.exists():
        sys.exit(f"missing {EXAMPLES}: download it from "
                 "github.com/amazon-science/esci-data into .data/esci/")
    con = duckdb.connect()
    products = None
    if PRODUCTS.exists():
        try:  # a download still in progress has no parquet footer yet
            con.execute(f"SELECT count(*) FROM parquet_metadata('{PRODUCTS}')")
            products = PRODUCTS
        except duckdb.Error as e:
            print(f"note: {PRODUCTS.name} is not readable ({str(e)[:60]}); using the mirror",
                  file=sys.stderr)
    if products is None:
        if not PRODUCTS_MIRROR.exists():
            sys.exit(f"missing {PRODUCTS} (original) and {PRODUCTS_MIRROR} (mirror)")
        products = PRODUCTS_MIRROR
    source = "amazon-science/esci-data" if products == PRODUCTS \
        else "huggingface:spacemanidol/ESCI-product-dataset-corpus-us (US re-encoding)"
    con.execute(f"CREATE VIEW ex AS SELECT * FROM '{EXAMPLES}'")
    con.execute(f"CREATE VIEW pr AS SELECT * FROM '{products}'")
    qids = [r[0] for r in con.execute("""
        SELECT query_id FROM ex
        WHERE product_locale = 'us' AND small_version = 1 AND split = 'test'
        GROUP BY query_id HAVING count(DISTINCT esci_label) = 4
        ORDER BY query_id""").fetchall()]
    rng = random.Random(seed)
    rng.shuffle(qids)
    rows = []
    for qid in qids[:n_queries]:
        cands = con.execute("""
            SELECT e.query, e.esci_label, p.product_id, p.product_title, p.product_brand,
                   p.product_color, p.product_bullet_point, p.product_description
            FROM ex e JOIN pr p ON e.product_id = p.product_id AND e.product_locale = p.product_locale
            WHERE e.query_id = ? AND e.product_locale = 'us' AND p.product_title IS NOT NULL
            ORDER BY e.product_id""", [qid]).fetchall()
        by_label: dict[str, list] = {"E": [], "S": [], "C": [], "I": []}
        for c in cands:
            by_label[c[1]].append(c)
        for label, k in PER_QUERY.items():
            pool = by_label[label]
            rng.shuffle(pool)
            for c in pool[:k]:
                query, lab, pid, title, brand, color, bullets, desc = c
                product = {"title": title}
                if brand:
                    product["brand"] = brand
                if color:
                    product["color"] = color
                if bullets:
                    product["bullet_points"] = bullets[: MAX_CHARS["product_bullet_point"]]
                if desc:
                    product["description"] = desc[: MAX_CHARS["product_description"]]
                state = {"query": query, "product": product}
                rows.append({
                    "row_id": hashlib.sha256(f"{qid}|{pid}".encode()).hexdigest()[:16],
                    "probe": "esci",
                    "query_id": int(qid),
                    "text": state,                 # JSON state, not a string
                    "label": lab == "E",           # jev_bool target
                    "grade": GRADE[lab],           # jev_score target, 0..3
                    "esci": lab,
                    "choice_label": lab,
                    "stratum": lab,
                    "label_confident": True,       # every label is a human grade
                    "products_source": source,
                })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=str(ESCI_DIR / "corpus.jsonl"))
    ap.add_argument("--queries", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rows = build(args.queries, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    from collections import Counter
    print(f"wrote {len(rows)} rows from {len({r['query_id'] for r in rows})} queries to {out}")
    print("labels:", dict(Counter(r["esci"] for r in rows)))
    chars = [len(json.dumps(r["text"])) for r in rows]
    print(f"state chars: median {sorted(chars)[len(chars)//2]}, max {max(chars)}")


if __name__ == "__main__":
    main()
