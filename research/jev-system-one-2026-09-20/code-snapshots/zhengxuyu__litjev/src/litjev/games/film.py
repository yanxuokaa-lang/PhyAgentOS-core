# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Minimal Labs
# Adapted from jevlike examples/film/build-film.mjs at
# 94f5fd1b0b11d52bbdfdf4e0ee6aa96b568f8452; rewritten for the LitJev trace schema.
"""Build a self-contained replay. Never fabricate upstream attention activations."""

import json
from pathlib import Path


def build_film(trace_path: Path, output: Path):
    trace = json.loads(trace_path.read_text())
    if trace.get("schema_version") != "litjev.trace.v1" or not trace.get("decisions"):
        raise ValueError("Expected a non-empty litjev.trace.v1 trace")
    template = (Path(__file__).parents[1] / "static" / "film.html").read_text()
    # Escape script delimiters, including malicious action labels in an imported trace.
    payload = json.dumps(trace, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e")
    payload = payload.replace("&", "\\u0026")
    html = template.replace('"__LITJEV_TRACE__"', payload, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
