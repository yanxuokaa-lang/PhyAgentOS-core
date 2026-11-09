# Contributing

LitJev is a research preview. The first supported checkpoint is Qwen/Qwen3.8-27B.
Distinguish tested behavior from proposed features or support for other models.

## Local setup

```bash
uv sync --locked --extra dev
uv run pytest -q
uv run ruff check .
uv build
```

Package code belongs in `src/litjev`, tests in `tests`, and request examples in
`examples`. UI assets live in `src/litjev/static` and must be bundled in wheels.
Use uv for dependency changes and include the updated lockfile.

- Add regression tests before changing inference, token positions, cache replication,
  schema validation, or response semantics.
- Preserve the two-forward reference path unless explicitly replacing it.
- Never include gold labels or CoT answers in inference prompts.
- Separate cold/warm timings; report hardware, precision, revisions, batch size,
  synchronization, and timing boundaries.
- Keep normalization separate from calibration claims.
- Do not commit weights, caches, credentials, private infrastructure configuration,
  or raw experiment logs. Review ignored artifacts before deliberately adding them.

For issues, provide a minimal request, expected behavior, sanitized error, versions,
model revision, and hardware details. For pull requests, explain the change and tests
run. Do not claim GPU or full-dataset verification unless performed.
