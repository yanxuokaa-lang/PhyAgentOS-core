"""Replay grasp task-affordance gate funnel from a persisted run.

Diagnostic-only: loads one entity's same-capture grasp candidates, point cloud,
rim feature and calibration from an existing run's ``artifacts/labutopia``
tree, re-runs the geometric qualification gates offline, and prints the
per-gate reject histogram. Issues no motion, creates no task, and never
rewrites run evidence. Funnel receipts are written to a scratch directory.

Usage (from the PAOS repository root):

    PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
      .venv/bin/python examples/forge-adapters/isaacsim_lab/scripts/replay_task_affordance_funnel.py \
      --artifacts out/<run>/artifacts/labutopia --entity R05 [--top 10]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


class _ReplayStore:
    """Read evidence from the persisted run tree; write replay receipts to scratch."""

    def __init__(self, run_root: Path, scratch: str):
        from isaacsim_lab.visual_perception import LabArtifactStore
        self.scratch = LabArtifactStore(scratch)
        self.run = LabArtifactStore(run_root)

    def path(self, ref):
        path = self.scratch.path(ref)
        return path if path.is_file() else self.run.path(ref)

    def write(self, kind, value):
        return self.scratch.write(kind, value)


def _entity_geometry(root: Path, label: str) -> dict:
    for path in sorted(root.joinpath("observed-geometry").glob("*.json")):
        data = _load_json(path)
        if data.get("label") == label:
            return data
    raise SystemExit(f"no observed-geometry artifact for label {label!r}")


def _predictions_for(root: Path, entity_ref: str) -> dict:
    for path in sorted(root.joinpath("grasp-predictions").glob("*.json")):
        data = _load_json(path)
        if data["request"]["targets"] and data["request"]["targets"][0]["entity_ref"] == entity_ref:
            return data
    raise SystemExit(f"no grasp-prediction artifact for {entity_ref!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path,
                        help="run artifacts/labutopia directory")
    parser.add_argument("--entity", required=True, help="entity label, e.g. R05")
    parser.add_argument("--destination", default="BEAKER", help="destination label for pour pairing")
    parser.add_argument("--top", type=int, default=10, help="print top surviving candidate ranks")
    args = parser.parse_args()

    from isaacsim_lab.visual_geometry import world_from_camera
    from isaacsim_lab.visual_perception import LabGraspTaskAffordanceProvider

    root = args.artifacts
    source = _entity_geometry(root, args.entity)
    destination = _entity_geometry(root, args.destination)
    entity_ref = source["entity_ref"]
    destination_ref = destination["entity_ref"]
    predictions = _predictions_for(root, entity_ref)

    identity = {key: source[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
    calibration = _load_json(root / Path(source["calibration_ref"]).relative_to("artifact://labutopia"))
    transform = world_from_camera(calibration).tolist()

    points_ref = next(ref for ref in source["source_refs"] if "/object-point-cloud/" in ref)
    records = {
        entity_ref: {**identity, "entity_ref": entity_ref, "category": source["category"],
                     "world_from_camera": transform, "points_ref": points_ref},
        destination_ref: {**identity, "entity_ref": destination_ref, "category": destination["category"],
                          "world_from_camera": transform, "points_ref": points_ref},
    }

    rim = next(feature for feature in source["process_feature_candidates"]
               if feature.get("feature_kind") == "rim")
    source_feature = {**rim, "feature_role": "pour_lip",
                      "pour_direction_world": [1.0, 0.0, 0.0]}
    destination_rim = next(feature for feature in destination["process_feature_candidates"]
                           if feature.get("feature_kind") == "rim")

    candidates = predictions["result"]["candidates"]
    captured = {candidate["candidate_ref"]: candidate for candidate in candidates}
    candidate_set_key = (f"candidate-set://replay/{args.entity}", identity["calibration_ref"])
    source_feature_ref = "process-feature://replay/source"
    destination_feature_ref = "process-feature://replay/destination"

    with tempfile.TemporaryDirectory(prefix="paos-funnel-replay-") as scratch:
        provider_from_tcp = np.eye(4)
        for path in sorted(root.joinpath("perception-configuration").glob("*.json")):
            configured = _load_json(path).get("configuration", {}).get("provider_from_tcp")
            if configured:
                provider_from_tcp = np.asarray(configured, dtype=float)
                break
        perception = SimpleNamespace(
            store=_ReplayStore(root, scratch),
            provider_from_tcp=provider_from_tcp,
            observations={identity["calibration_ref"]: records},
            grasps=SimpleNamespace(
                candidate_sets={candidate_set_key: {
                    **identity, "candidate_set_ref": candidate_set_key[0],
                    "entities": {entity_ref}, "candidate_refs": set(captured)},
                },
                captures={identity["calibration_ref"]: captured},
            ),
            process_feature_sets={"process-feature-set://replay/current": {
                **identity, "candidate_set_ref": "process-feature-set://replay/current",
                "entity_refs": (entity_ref, destination_ref),
                "candidates": {
                    source_feature_ref: (entity_ref, 0, source_feature),
                    destination_feature_ref: (destination_ref, 1, destination_rim),
                },
            }},
            _records=lambda _request: records,
        )
        provider = LabGraspTaskAffordanceProvider(perception, approach_feasibility=None)
        request = {
            "operation": "pour", "entity_refs": [entity_ref, destination_ref],
            "grasp_candidate_set_ref": candidate_set_key[0],
            "process_feature_candidate_set_ref": "process-feature-set://replay/current",
            "selected_process_feature_refs": [source_feature_ref, destination_feature_ref],
            **identity,
        }
        result = provider.propose(request)
        funnel = provider.candidate_sets[result["candidate_set_ref"]]
        receipt = _load_json(perception.store.path(funnel["funnel_ref"]))

    print(f"entity={args.entity} candidates={len(candidates)} status={result['status']}")
    print(f"evaluated={receipt['evaluated']} geometry_qualified={receipt['geometry_qualified']} "
          f"final_qualified={receipt['qualified']}")
    print("\n=== gate rejects (first-failure attribution, ordered) ===")
    for reason, count in sorted(receipt["gate_rejects"].items(), key=lambda item: -item[1]):
        print(f"  {count:4d}  {reason}")
    print("\n=== survivors ===")
    for item in result.get("candidates", [])[:args.top]:
        print(f"  {item['grasp_candidate_ref']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
