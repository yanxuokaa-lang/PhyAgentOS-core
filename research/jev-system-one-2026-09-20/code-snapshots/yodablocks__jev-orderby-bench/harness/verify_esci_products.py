"""Check the ESCI corpus's product fields against Amazon's original file.

The corpus may have been built from the Hugging Face US re-encoding of
the products file (see corpus_esci.py). This compares every product the
corpus used, field by field, against the original
shopping_queries_dataset_products.parquet, applying the same
normalisation the builder applies (trim, empty -> null, 600-char cut).

Run: python3 harness/verify_esci_products.py
"""
from __future__ import annotations

import json
import sys

import duckdb

from corpus_esci import CORPUS_OUT, ESCI_DIR, EXAMPLES, MAX_CHARS, PRODUCTS, PRODUCTS_MIRROR


def main() -> int:
    for f in (CORPUS_OUT, EXAMPLES, PRODUCTS, PRODUCTS_MIRROR):
        if not f.exists():
            sys.exit(f"missing {f}")
    rows = [json.loads(l) for l in CORPUS_OUT.open() if l.strip()]
    con = duckdb.connect()
    con.execute("CREATE TABLE used (row_id VARCHAR, query_id INT, title VARCHAR, brand VARCHAR, "
                "color VARCHAR, bullets VARCHAR, descr VARCHAR)")
    con.executemany("INSERT INTO used VALUES (?,?,?,?,?,?,?)", [
        (r["row_id"], r["query_id"], r["text"]["product"].get("title"),
         r["text"]["product"].get("brand"), r["text"]["product"].get("color"),
         r["text"]["product"].get("bullet_points"), r["text"]["product"].get("description"))
        for r in rows])
    con.execute(f"CREATE VIEW ex AS SELECT * FROM '{EXAMPLES}'")
    con.execute(f"CREATE VIEW mirror AS SELECT * FROM '{PRODUCTS_MIRROR}'")
    con.execute(f"CREATE VIEW orig AS SELECT * FROM '{PRODUCTS}'")
    b, d = MAX_CHARS["product_bullet_point"], MAX_CHARS["product_description"]
    # Recover each used row's product_id through the examples file and the
    # mirror (title match within the query), then compare with the original.
    q = f"""
      WITH ids AS (
        SELECT DISTINCT u.row_id, e.product_id, u.title, u.brand, u.color, u.bullets, u.descr
        FROM used u
        JOIN ex e ON e.query_id = u.query_id AND e.product_locale = 'us'
        JOIN mirror m ON m.product_id = e.product_id AND m.product_title = u.title
      ),
      cmp AS (
        SELECT i.row_id, i.product_id,
          o.product_title = i.title AS title_ok,
          coalesce(nullif(trim(o.product_brand), ''), '') = coalesce(i.brand, '') AS brand_ok,
          coalesce(nullif(trim(o.product_color), ''), '') = coalesce(i.color, '') AS color_ok,
          left(coalesce(nullif(trim(o.product_bullet_point), ''), ''), {b}) = coalesce(i.bullets, '') AS bullets_ok,
          left(coalesce(nullif(trim(o.product_description), ''), ''), {d}) = coalesce(i.descr, '') AS descr_ok,
          i.color AS corpus_color, o.product_color AS original_color
        FROM ids i JOIN orig o ON o.product_id = i.product_id AND o.product_locale = 'us'
      )
      SELECT * FROM cmp"""
    cmp = con.execute(q).fetchall()
    cols = [c[0] for c in con.description]
    n = len({c[0] for c in cmp})
    print(f"corpus rows: {len(rows)}, matched against original: {n}")
    for field in ("title_ok", "brand_ok", "color_ok", "bullets_ok", "descr_ok"):
        k = cols.index(field)
        bad = [c for c in cmp if not c[k]]
        print(f"  {field:11s} {len(cmp) - len(bad)}/{len(cmp)}" +
              ("" if not bad else "  mismatches: " + "; ".join(
                  f"{c[1]} corpus={c[cols.index('corpus_color')]!r} original={c[cols.index('original_color')]!r}"
                  if field == "color_ok" else c[1] for c in bad)))
    return 0 if n == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
