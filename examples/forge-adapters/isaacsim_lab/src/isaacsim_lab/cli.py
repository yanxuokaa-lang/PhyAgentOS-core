"""Inspect the PAOS input that will be sent to a LabUtopia cycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .profile import LabUtopiaProfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--previous-input", type=Path)
    parser.add_argument("--operation", choices=("pour_cycle", "stir_cycle"), default="pour_cycle")
    args = parser.parse_args()
    profile = LabUtopiaProfile.from_json(args.profile)
    previous = None
    if args.previous_input:
        previous = json.loads(args.previous_input.read_text(encoding="utf-8"))
    print(json.dumps({
        "profile": str(args.profile),
        "lab_root": str(profile.lab_root),
        "scene_usd_path": str(profile.scene_usd_path),
        "source_path": profile.source_path,
        "destination_path": profile.destination_path,
        "paos_input": profile.paos_input(previous, operation=args.operation),
        "feedback_source_profile": profile.source_profile(),
        "evaluation_profile": profile.evaluation_profile(),
        "motion_authorized": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
