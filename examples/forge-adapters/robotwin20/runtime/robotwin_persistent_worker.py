"""JSON-lines entrypoint for one persistent simulation provider process."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from robotwin_persistent_engine import RoboTwinPersistentEngine

from robotwin20_adapter.persistent_manipulation import PersistentManipulationProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    output = sys.stdout
    # Simulator and planner diagnostics must never enter the JSON protocol.
    sys.stdout = sys.stderr
    provider = PersistentManipulationProvider(lambda: RoboTwinPersistentEngine(profile))

    def emit(value):
        output.write(json.dumps(value, separators=(",", ":")) + "\n")
        output.flush()

    emit({"event": "worker_ready"})
    try:
        for line in sys.stdin:
            request = {}
            try:
                request = json.loads(line)
                command = request["command"]
                if command == "shutdown":
                    provider.close()
                    emit({"request_id": request["request_id"], "status": "shutdown"})
                    return 0
                if command == "start":
                    provider.start(request["phase"], request["invocation_id"], request["owner"], request["arguments"])
                    result = {"status": "accepted"}
                elif command == "poll":
                    result = {"result": provider.poll(request["invocation_id"])}
                elif command == "cancel":
                    provider.cancel(request["invocation_id"])
                    result = {"status": "cancel_requested"}
                elif command == "query":
                    result = provider.query(request["operation"], request.get("arguments", {}))
                else:
                    raise ValueError("unsupported persistent worker command")
                emit({"request_id": request["request_id"], "ok": True, **result})
            except Exception as exc:
                emit({"request_id": request.get("request_id", "invalid"), "ok": False,
                      "error": {"code": type(exc).__name__, "message": str(exc)}})
    finally:
        provider.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
