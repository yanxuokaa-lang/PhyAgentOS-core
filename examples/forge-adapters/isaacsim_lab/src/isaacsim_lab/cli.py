"""Inspect the PAOS input that will be sent to a LabUtopia cycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import LabUtopiaBackend, diagnose_pour_observations
from .profile import LabUtopiaProfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--previous-input", type=Path)
    parser.add_argument("--result", type=Path, help="inspect a completed worker result without starting Isaac Sim")
    parser.add_argument("--operation", choices=("pour_cycle", "stir_cycle", "manipulation_cycle"), default="pour_cycle")
    parser.add_argument("--dry-run", action="store_true", help="resolve controller capability without starting Isaac Sim")
    args = parser.parse_args()
    profile = LabUtopiaProfile.from_json(args.profile)
    previous = None
    if args.previous_input:
        previous = json.loads(args.previous_input.read_text(encoding="utf-8"))
    output = {
        "profile": str(args.profile),
        "lab_root": str(profile.lab_root),
        "scene_usd_path": str(profile.scene_usd_path),
        "source_path": profile.source_path,
        "destination_path": profile.destination_path,
        "paos_input": profile.paos_input(previous, operation=args.operation),
        "feedback_source_profile": profile.source_profile(),
        "evaluation_profile": profile.evaluation_profile(),
        "motion_authorized": False,
    }
    if args.dry_run:
        output["dry_run"] = LabUtopiaBackend(profile).dry_run_cycle(output["paos_input"])
    if args.result:
        result = json.loads(args.result.read_text(encoding="utf-8"))
        output["result_status"] = result.get("status")
        output["result_outcome_known"] = result.get("outcome_known")
        output["pour_diagnosis"] = diagnose_pour_observations(result.get("feedback_observations", []), profile)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
