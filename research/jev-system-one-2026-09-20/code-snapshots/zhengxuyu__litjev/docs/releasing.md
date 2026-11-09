# Release checklist

This document prepares a release; it does not publish anything automatically.

- [x] Select Apache-2.0 and include LICENSE, NOTICE, and package license metadata.
- [x] Add a README citation section and CITATION.cff.
- [x] Add the public repository URL to CITATION.cff and the README citation;
  keep citation authors/version current for each release.
- [x] Choose a public repository URL and add repository/issue URLs to pyproject.toml.
- [ ] Review staged files and all Git history for secrets, private infrastructure,
  proprietary material, and dataset redistribution constraints.
- [ ] Exclude `results/`, weights, environment files, logs, and cluster artifacts.
  Ignore rules do not remove previously tracked files or history.
- [ ] Enable private vulnerability reporting or supply a private security contact.
- [ ] Keep examples consistent with the implemented API. Jev-format support is
  pending: do not advertise `/v1/systemone`, Score, or Noul as available.
- [ ] Run tests, lint, and build. Inspect the wheel and source archive for included
  browser assets and excluded private artifacts.
- [ ] Smoke-test the installed wheel with Qwen: frontend, API, two observed forwards,
  zero generated answer tokens, and timing fields.

For PyPI, first confirm name ownership/availability. Choose a version, add release
notes, tag the tested revision, and use authenticated publishing (prefer trusted
publishing). A repository push, tag push, or package upload requires maintainer
approval; preparing local files does not perform these actions.
