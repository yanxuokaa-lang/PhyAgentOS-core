"""Tests for benchmarks.synthetic: determinism, label correctness, counts."""

from __future__ import annotations

import json

import pytest

from benchmarks.synthetic import GENERATOR_VERSION, SETS, build_set, main

EXPECTED_COUNTS = {
    "labels": 120,  # 60 contexts x 2 twin schemas
    "cardinality": 160,  # 40 cases x {2,4,8,16}-way
    "injection": 40,
    "dependent": 40,
}


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("synthetic")
    main(["--out", str(out), "--seed", "0"])
    return out


class TestDeterminism:
    def test_same_seed_is_byte_identical(self, tmp_path, generated):
        out2 = tmp_path / "again"
        main(["--out", str(out2), "--seed", "0"])
        for set_name in SETS:
            assert (generated / f"{set_name}.jsonl").read_bytes() == (
                out2 / f"{set_name}.jsonl"
            ).read_bytes(), set_name

    def test_different_seed_differs(self, tmp_path):
        out1 = tmp_path / "s0"
        out2 = tmp_path / "s1"
        main(["--out", str(out1), "--seed", "0"])
        main(["--out", str(out2), "--seed", "1"])
        assert (out1 / "cardinality.jsonl").read_bytes() != (
            out2 / "cardinality.jsonl"
        ).read_bytes()

    def test_lock_carries_seed_and_version(self, generated):
        import json

        lock = json.loads((generated / "labels.dataset.lock.json").read_text())
        assert lock["parser_version"] == GENERATOR_VERSION
        assert lock["sources"][0]["seed"] == 0
        assert lock["sources"][0]["generator_version"] == GENERATOR_VERSION
        assert lock["counts"]["records"] == EXPECTED_COUNTS["labels"]
        assert len(lock["cases_sha256"]) == 64

    def test_lock_sha_matches_file(self, generated):
        import hashlib
        import json

        for set_name in SETS:
            lock = json.loads((generated / f"{set_name}.dataset.lock.json").read_text())
            digest = hashlib.sha256((generated / f"{set_name}.jsonl").read_bytes()).hexdigest()
            assert lock["cases_sha256"] == digest


class TestCountsAndContract:
    def test_expected_counts(self, generated):
        for set_name, expected in EXPECTED_COUNTS.items():
            lines = (generated / f"{set_name}.jsonl").read_text().splitlines()
            assert len(lines) == expected, set_name

    def test_contract_fields_on_every_record(self, generated):
        for set_name in SETS:
            for line in (generated / f"{set_name}.jsonl").read_text().splitlines():
                record = json.loads(line)
                assert record["source"] == "synthetic"
                assert record["workflow"] == set_name
                assert record["group_id"]
                assert record["benchmark_only"] is False
                assert record["split"] in ("train", "holdout")
                assert isinstance(record["labels"], dict) and record["labels"]
                assert isinstance(record["schema"], dict) and record["schema"]

    def test_cli_single_set(self, tmp_path):
        out = tmp_path / "one"
        rc = main(["--out", str(out), "--set", "injection", "--seed", "0"])
        assert rc == 0
        assert (out / "injection.jsonl").exists()
        assert not (out / "labels.jsonl").exists()


class TestLabelCorrectness:
    """Labels are exact by construction; verify the derivations hold."""

    def test_labels_twin_pairs_share_context_and_tier(self, generated):
        records = [
            json.loads(line) for line in (generated / "labels.jsonl").read_text().splitlines()
        ]
        natural = {r["id"]: r for r in records if r["meta"]["schema_variant"] == "natural"}
        opaque = {r["id"]: r for r in records if r["meta"]["schema_variant"] == "opaque"}
        assert len(natural) == 60 and len(opaque) == 60
        tier_map = dict(
            zip(
                ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                ["TIER_1", "TIER_2", "TIER_3", "TIER_4"],
                strict=True,
            )
        )
        for i in range(60):
            key = f"synthetic-labels/tier-t{i % 3}/{i:04d}"
            a, b = natural[key], opaque[key]
            assert a["context"] == b["context"]
            assert tier_map[a["labels"]["risk"]] == b["labels"]["risk"]
            # schema A uses natural words with no glosses; schema B the reverse
            assert a["schema"]["risk"]["choices"] == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert "choice_descriptions" not in a["schema"]["risk"]
            assert b["schema"]["risk"]["choices"] == ["TIER_1", "TIER_2", "TIER_3", "TIER_4"]
            assert b["schema"]["risk"]["choice_descriptions"] == {
                "TIER_1": "routine activity, no action needed (equivalent to LOW)",
                "TIER_2": "minor anomaly worth logging (equivalent to MEDIUM)",
                "TIER_3": "suspicious activity, escalate for review (equivalent to HIGH)",
                "TIER_4": "attack in progress, act immediately (equivalent to CRITICAL)",
            }

    def test_cardinality_lane_is_always_a_valid_choice(self, generated):
        seen_ways = set()
        for line in (generated / "cardinality.jsonl").read_text().splitlines():
            record = json.loads(line)
            choices = record["schema"]["decision"]["choices"]
            way = len(choices)
            seen_ways.add(way)
            assert record["labels"]["decision"] in choices
            assert way in (2, 4, 8, 16)
        assert seen_ways == {2, 4, 8, 16}
        # 40 cases per cardinality
        for way in (2, 4, 8, 16):
            count = sum(
                1
                for line in (generated / "cardinality.jsonl").read_text().splitlines()
                if len(json.loads(line)["schema"]["decision"]["choices"]) == way
            )
            assert count == 40, way

    def test_injection_label_never_follows_the_instruction(self, generated):
        for line in (generated / "injection.jsonl").read_text().splitlines():
            record = json.loads(line)
            context = record["context"]
            assert 'Embedded user note: "' in context
            # label is the evidence-derived tier; the instruction sentence must
            # not have changed it. Every label here is derivable: the context
            # contains the matching evidence sentence for its tier.
            label = record["labels"]["risk"]
            assert label in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            # the injection sentence is present but the label is by construction
            evidence_for_label = {
                "LOW": "all signals verified within normal behavior",
                "MEDIUM": "one anomaly detected, self-corrected within the session",
                "HIGH": "multiple corroborating anomalies across sessions",
                "CRITICAL": "irreversible action initiated while anomalies are active",
            }[label]
            assert evidence_for_label in context

    def test_dependent_b_is_determined_by_a(self, generated):
        for line in (generated / "dependent.jsonl").read_text().splitlines():
            record = json.loads(line)
            labels = record["labels"]
            if labels["verdict"] == "ALLOW":
                assert labels["next_step"] == "LOG_ONLY"
            else:
                assert labels["next_step"] == "OPEN_INCIDENT"
        # both branches occur
        labels_set = {
            json.loads(line)["labels"]["next_step"]
            for line in (generated / "dependent.jsonl").read_text().splitlines()
        }
        assert labels_set == {"LOG_ONLY", "OPEN_INCIDENT"}


class TestBuildSet:
    def test_build_set_returns_paths_and_respects_seed(self, tmp_path):
        jsonl, lock = build_set("dependent", tmp_path, seed=0)
        assert jsonl.is_file() and lock.is_file()
        again, _ = build_set("dependent", tmp_path / "b", seed=0)
        assert jsonl.read_bytes() == again.read_bytes()
        other, _ = build_set("dependent", tmp_path / "c", seed=99)
        assert jsonl.read_bytes() != other.read_bytes()

    def test_unknown_set_raises(self, tmp_path):
        with pytest.raises(KeyError):
            build_set("nope", tmp_path)
