from __future__ import annotations

import argparse
import json
import os
import sys
import time


def persistent_large_provider():
    from robotwin20_adapter.persistent_manipulation import PersistentManipulationProvider

    class Engine:
        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
            del phase, arguments, cancel, owner, invocation_id
            return {
                "status": "succeeded",
                "world_change_started": True,
                "outcome_known": True,
                "new_scene_revision": "scene-2",
                "failure_owner": "none",
                "failure_code": None,
                "retryable_in_revision": False,
                "requires_replan": False,
                "recommended_action": "continue",
                "phase": "acquire",
                "arm_attempts": [{
                    "arm": "arm-a",
                    "status": "pass",
                    "execution_plan": {"diagnostic": "x" * 2_000_000},
                }],
                "artifact_refs": ["artifact://persistent/action-large"],
                "evidence_refs": ["artifact://persistent/action-large"],
            }

        def query(self, operation, arguments):
            del operation, arguments
            return {"scene_revision": "scene-2"}

        def close(self):
            return None

    return PersistentManipulationProvider(Engine)


def emit(value):
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="normal")
    args = parser.parse_args()
    if args.mode == "unavailable":
        emit({"event": "worker_unavailable"})
        return 2
    provider = persistent_large_provider() if args.mode == "persistent-large" else None
    emit({"event": "worker_ready"})
    try:
        for line in sys.stdin:
            request = json.loads(line)
            if request.get("command") == "shutdown":
                emit({"request_id": request["request_id"], "status": "shutdown"})
                return 0
            if provider is not None:
                if request.get("command") == "start":
                    provider.start(
                        request["phase"],
                        request["invocation_id"],
                        request["owner"],
                        request["arguments"],
                    )
                    value = {"status": "accepted"}
                elif request.get("command") == "poll":
                    value = {"result": provider.poll(request["invocation_id"])}
                else:
                    value = provider.query(request.get("operation", "snapshot"), request.get("arguments", {}))
                emit({**value, "request_id": request["request_id"], "ok": True})
                continue
            if request.get("command") == "sleep":
                status = "unavailable" if args.mode == "sleep-fail" else "sleeping"
                emit({"request_id": request["request_id"], "status": status})
                continue
            if request.get("command") == "wake":
                emit({"request_id": request["request_id"], "status": "awake"})
                continue
            if args.mode == "timeout":
                time.sleep(2)
            elif args.mode == "kill":
                os.kill(os.getpid(), 9)
            elif args.mode == "invalid-json":
                sys.stdout.write("not-json\n")
                sys.stdout.flush()
                continue
            elif args.mode == "large-response":
                emit({"request_id": request["request_id"], "payload": "x" * 2_000_000})
                continue
            request_id = "wrong" if args.mode == "wrong-id" else request["request_id"]
            emit({"request_id": request_id, "status": "available", "pid": os.getpid()})
        return 0
    finally:
        if provider is not None:
            provider.close()


if __name__ == "__main__":
    raise SystemExit(main())
