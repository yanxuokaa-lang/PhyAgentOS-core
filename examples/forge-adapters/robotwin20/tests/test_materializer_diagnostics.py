import json
import sys

import materialize_complete_route as cli
import pytest

from robotwin20_adapter.route_generation import RouteCandidateRejectedError
from robotwin20_adapter.route_inputs import ContactShellRejectedError


def test_provenance_copy_preserves_the_unique_persisted_artifact_type(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    reference = "artifact://persistent/epoch/oracle-grasp"
    path = cli._artifact_path(source, reference, ".json")
    path.parent.mkdir(parents=True)
    path.write_text('{"motion_authorized":false}\n')

    cli._copy_provenance_artifact(source, output, reference)

    assert cli._artifact_path(output, reference, ".json").read_bytes() == path.read_bytes()
    assert not cli._artifact_path(output, reference, ".npy").exists()


def test_provenance_copy_rejects_missing_or_ambiguous_source_type(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    reference = "artifact://source/item"
    with pytest.raises(cli.MaterializationError, match="unavailable"):
        cli._copy_provenance_artifact(source, output, reference)
    for suffix in (".json", ".npy"):
        path = cli._artifact_path(source, reference, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"source")
    with pytest.raises(cli.MaterializationError, match="ambiguous"):
        cli._copy_provenance_artifact(source, output, reference)


@pytest.mark.parametrize("error,code", [
    (cli.MaterializationError("capabilities differ", code="motion_capability_qualification_mismatch"), "motion_capability_qualification_mismatch"),
    (RouteCandidateRejectedError("workspace bounds"), "route_candidate_rejected"),
    (ContactShellRejectedError("contact shell"), "route_candidate_rejected"),
])
def test_cli_persists_public_failure_and_exits_unsuccessfully(tmp_path, monkeypatch, capsys, error, code):
    flags = ["scene-facts", "source-capture-root", "grasp-results", "route-input-profile",
             "grasp-transform-attestation", "grasp-provider-source-root", "simulation-probe-profile",
             "simulation-probe-worker", "runtime-profile", "arm-planning-profile",
             "left-motion-capability", "right-motion-capability", "left-motion-capability-validation",
             "right-motion-capability-validation", "controller-qualification", "controller-qualification-plan",
             "controller-qualification-evidence", "controller-qualification-validation", "artifact-root",
             "candidate-ref", "entity-ref", "request-id"]
    argv = ["materializer"]
    for flag in flags:
        argv.extend(["--" + flag, str(tmp_path)])
    monkeypatch.setattr(sys, "argv", argv)

    def fail(_):
        raise error

    monkeypatch.setattr(cli, "materialize", fail)
    assert cli.main() == 1
    response = json.loads(capsys.readouterr().out)
    diagnostic = json.loads((tmp_path / "materialization_error.json").read_text())
    assert response["error"] == diagnostic
    assert diagnostic["code"] == code
    assert response["motion_authorized"] is False
    assert not (tmp_path / "route_request.json").exists()
