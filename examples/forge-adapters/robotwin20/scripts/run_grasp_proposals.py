"""Run an adapter grasp provider and materialize its provider-neutral bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from robotwin20_adapter.grasp_profile import build_grasp_provider, load_grasp_profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text(encoding="utf-8"))
    provider = build_grasp_provider(load_grasp_profile(args.profile))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bundle: dict[str, Any] = {"request": request}
    try:
        result = provider.propose(request)
        bundle["result"] = result
    except Exception as exc:
        bundle["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        args.output.write_text(json.dumps(bundle, indent=2, default=list) + "\n", encoding="utf-8")
        args.output.with_suffix(".worker.log").write_text("\n".join(provider.client.stderr_tail), encoding="utf-8")
    print(json.dumps({"status": "available" if result["provider_available"] else "unavailable", "candidate_count": len(result["candidates"]), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
