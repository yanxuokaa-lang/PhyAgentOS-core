"""Tests for benchmarks.typesafe.published: strict common subset + agreement.

Hand-built 3-record fixture, no fetching: two published models (opus, sol),
one ambiguous field, one field missing for one model — the subset and
agreement numbers are computed by hand below.
"""

from __future__ import annotations

import json

import pytest

from benchmarks.typesafe.published import (
    common_subset_field_ids,
    main,
    published_agreement,
)


def _record(rid, workflow, schema, labels, models, ambiguous=()):
    return {
        "id": rid,
        "group_id": rid,
        "source": "typesafe",
        "workflow": workflow,
        "benchmark_only": True,
        "schema": schema,
        "context": "c",
        "labels": labels,
        "split": "train",
        "meta": {
            "consensus": {},
            "margin": {},
            "ambiguous": list(ambiguous),
            "models": models,
        },
        "skipped_questions": 0,
    }


@pytest.fixture()
def records():
    """Three records, two models (opus, sol).

    - r1/bool_field: both models answered, clean consensus. opus picks
      0.9 -> True (label False: DISAGREE); sol picks 0.2 -> False (agree).
    - r1/enum_field: both answered, clean consensus, both agree ('refund').
    - r2/score_field: both answered, clean consensus; label '2'.
      opus raw 1.6 -> round 2 (agree); sol raw 0.4 -> round 0 (disagree).
    - r2/ambiguous_field: both answered but consensus top1-top2 < 0.1 ->
      flagged ambiguous -> NOT in the subset.
    - r3/missing_field: only opus answered -> NOT in the subset (sol did
      not answer); opus would agree, but the subset is strict.
    """
    bool_schema = {"type": "boolean", "description": "d"}
    enum_schema = {"type": "enum", "description": "d", "choices": ["refund", "dispute"]}
    score_schema = {"type": "enum", "description": "d", "choices": ["0", "1", "2", "3"]}
    return [
        _record(
            "typesafe/wf1/case-1",
            "wf1",
            {"bool_field": bool_schema, "enum_field": enum_schema},
            {"bool_field": False, "enum_field": "refund"},
            {
                "bool_field": {"opus": 0.9, "sol": 0.2},
                "enum_field": {"opus": "refund", "sol": "refund"},
            },
        ),
        _record(
            "typesafe/wf2/case-2",
            "wf2",
            {"score_field": score_schema, "ambiguous_field": enum_schema},
            {"score_field": "2", "ambiguous_field": "refund"},
            {
                "score_field": {"opus": 1.6, "sol": 0.4},
                "ambiguous_field": {"opus": "refund", "sol": "refund"},
            },
            ambiguous=["ambiguous_field"],
        ),
        _record(
            "typesafe/wf1/case-3",
            "wf1",
            {"missing_field": enum_schema},
            {"missing_field": "refund"},
            {"missing_field": {"opus": "refund"}},  # sol did not answer
        ),
    ]


class TestCommonSubset:
    def test_subset_ids(self, records):
        ids = common_subset_field_ids(records)
        assert ids == [
            "typesafe/wf1/case-1::bool_field",
            "typesafe/wf1/case-1::enum_field",
            "typesafe/wf2/case-2::score_field",
        ]

    def test_ambiguous_field_excluded(self, records):
        ids = common_subset_field_ids(records)
        assert not any(k.endswith("ambiguous_field") for k in ids)

    def test_field_missing_for_one_model_excluded(self, records):
        ids = common_subset_field_ids(records)
        assert not any(k.endswith("missing_field") for k in ids)

    def test_empty_records(self):
        assert common_subset_field_ids([]) == []

    def test_no_models_at_all(self, records):
        stripped = [dict(r, meta={"models": {}}) for r in records]
        assert common_subset_field_ids(stripped) == []

    def test_ids_unique_across_records_with_same_field_name(self, records):
        """The same field name in two records yields two distinct ids."""
        dup = _record(
            "typesafe/wf1/case-9",
            "wf1",
            {"bool_field": {"type": "boolean", "description": "d"}},
            {"bool_field": True},
            {"bool_field": {"opus": 0.9, "sol": 0.9}},
        )
        ids = common_subset_field_ids(records + [dup])
        assert sum(k.endswith("::bool_field") for k in ids) == 2


class TestAgreement:
    def test_model_rows_exact_numbers(self, records):
        result = published_agreement(records)
        by_name = {m["name"]: m for m in result["models"]}
        assert set(by_name) == {"opus", "sol"}
        # opus: bool disagree (0.9 -> True vs False), enum agree, score agree
        # (1.6 -> '2'): 2/3. sol: bool agree, enum agree, score disagree
        # (0.4 -> '0' vs '2'): 2/3.
        assert by_name["opus"]["agreed"] == 2 and by_name["opus"]["total"] == 3
        assert by_name["sol"]["agreed"] == 2 and by_name["sol"]["total"] == 3
        assert by_name["opus"]["agreement"] == pytest.approx(2 / 3)
        assert by_name["sol"]["agreement"] == pytest.approx(2 / 3)

    def test_by_workflow_split(self, records):
        result = published_agreement(records)
        opus = next(m for m in result["models"] if m["name"] == "opus")
        assert opus["by_workflow"]["wf1"] == {
            "agreed": 1,
            "total": 2,
            "agreement": pytest.approx(0.5),
        }
        assert opus["by_workflow"]["wf2"] == {
            "agreed": 1,
            "total": 1,
            "agreement": 1.0,
        }

    def test_score_uses_round_of_raw(self, records):
        """Score raw 1.6 -> '2' (agree), 0.4 -> '0' (disagree)."""
        result = published_agreement(records)
        # Verified through the exact totals above; here we pin the rule by
        # flipping the label and watching opus's score agreement flip.
        records[1]["labels"]["score_field"] = "0"
        result = published_agreement(records)
        opus = next(m for m in result["models"] if m["name"] == "opus")
        assert opus["agreed"] == 1  # bool still disagrees, score now disagrees

    def test_boolean_pick_threshold(self, records):
        """raw >= 0.5 picks True; 0.9 -> True disagrees with label False."""
        records[0]["labels"]["bool_field"] = True
        result = published_agreement(records)
        opus = next(m for m in result["models"] if m["name"] == "opus")
        assert opus["agreed"] == 3  # bool now agrees: 3/3

    def test_subset_block_shape(self, records):
        result = published_agreement(records)
        subset = result["subset"]
        assert subset["n_fields"] == 3
        assert subset["n_cases"] == 2  # case-1 and case-2 own subset fields
        assert subset["workflows"] == ["wf1", "wf2"]
        assert len(subset["field_ids"]) == 3

    def test_names_as_published(self, records):
        """Model names are used exactly as found in meta.models."""
        records[0]["meta"]["models"]["bool_field"]["GLM-4.6-Preview"] = 0.1
        result = published_agreement(records)
        names = {m["name"] for m in result["models"]}
        assert "GLM-4.6-Preview" in names  # not renamed
        # The strict subset is now empty for bool_field? No: the third model
        # answered bool_field on case-1 only, so bool_field drops out of the
        # subset (not answered by all three everywhere it is labelled)...
        # Actually the subset requires ALL published models to have answered
        # each field: bool_field now lacks GLM on case-1? It HAS GLM on
        # case-1. sol/opus too. So bool_field stays; enum_field drops (GLM
        # never answered it).
        subset_ids = result["subset"]["field_ids"]
        assert "typesafe/wf1/case-1::bool_field" in subset_ids
        assert "typesafe/wf1/case-1::enum_field" not in subset_ids


class TestCli:
    def test_main_writes_json(self, records, tmp_path, capsys):
        data = tmp_path / "cases.jsonl"
        data.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        out = tmp_path / "published_agreement.json"
        rc = main(["--data", str(data), "--out", str(out)])
        assert rc == 0
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["subset"]["n_fields"] == 3
        assert {m["name"] for m in payload["models"]} == {"opus", "sol"}
        printed = capsys.readouterr().out
        assert "opus" in printed and "common subset" in printed
