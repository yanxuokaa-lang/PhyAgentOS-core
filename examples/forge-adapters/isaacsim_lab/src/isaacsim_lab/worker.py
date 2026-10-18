"""Private child-process entry point for Isaac Sim lifecycle isolation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from threading import Event

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from isaacsim_lab.engine import LabUtopiaBackend
    from isaacsim_lab.profile import LabUtopiaProfile
else:
    from .engine import LabUtopiaBackend
    from .profile import LabUtopiaProfile


def main() -> int:
    profile = LabUtopiaProfile.from_json(Path(os.environ["PAOS_ISAAC_PROFILE"]))
    arguments = json.loads(Path(os.environ["PAOS_ISAAC_INPUT_PATH"]).read_text(encoding="utf-8"))
    LabUtopiaBackend(profile)._run_inprocess(
        arguments, Event(), Path(os.environ["PAOS_ISAAC_RESULT_PATH"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
