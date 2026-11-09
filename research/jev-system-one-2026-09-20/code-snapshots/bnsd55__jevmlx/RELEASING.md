# Releasing jevmlx

Exact ordered command list to publish `jevmlx X.Y.Z` to PyPI. Nothing is
published automatically; every step below is manual. Work on an Apple
Silicon Mac with a green `main`.

## Prereq (once)

```bash
uv tool install twine
```

## Steps (run from a clone of `main`, up to date)

```bash
# 0. Gates on main: full suites + lint green
pytest -m "not slow" -q && pytest -m slow -q && ruff check . && ruff format --check .

# 1. Version must already read X.Y.Z in pyproject.toml and CHANGELOG.md must
#    have the matching "## [X.Y.Z] - YYYY-MM-DD" section (edit + commit if not).
#    In the SAME release commit, switch the README install lines to the PyPI
#    names (pip install jevmlx / uv tool install jevmlx — they are a lie until
#    the upload in step 4 lands, which is why the commit goes out with the tag).

# 2. Build distributions and validate them
rm -rf dist && uv build
twine check dist/*

# 3. Tag the release commit and push it (triggers the release-check workflow:
#    build + twine check + clean-venv wheel smoke test; wait for green)
git tag vX.Y.Z
git push origin vX.Y.Z

# 4. Publish to PyPI (needs a PyPI token with upload rights for the project)
twine upload dist/jevmlx-X.Y.Z*

# 5. Cut the GitHub release from the tag
open https://github.com/bnsd55/jevmlx/releases/new?tag=vX.Y.Z
#   - title: "jevmlx X.Y.Z"
#   - notes: paste the CHANGELOG "## [X.Y.Z]" section

# 6. Verify: fresh venv, install from PyPI, smoke test
uv venv /tmp/jevmlx-release-check && uv pip install --python /tmp/jevmlx-release-check/bin/python jevmlx
/tmp/jevmlx-release-check/bin/jevmlx --version
/tmp/jevmlx-release-check/bin/jevmlx doctor --json
```

## Hard rules

- Never publish a version whose README numbers are not backed by files under
  `benchmarks/results/` — every accuracy/latency claim must link to a
  committed result file.
- The `release-check` workflow run for the tag must be green before step 4.
