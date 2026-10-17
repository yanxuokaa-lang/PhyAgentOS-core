from PhyAgentOS.agent.experience.redaction import redact_text


def test_redact_text_removes_internal_opaque_uris_from_remote_text():
    value = (
        "choose entity://e1 from observation://scene/head using "
        "calibration://fixture/current; see artifact://plans/rev, "
        "candidate://e1/1, destination://targets/bin, task://task-1, "
        "record://record-1 and revision://rev-1"
    )

    redacted = redact_text(value)

    assert "[REDACTED_REFERENCE]" in redacted
    assert "://" not in redacted
    assert "entity://" not in redacted
    assert "choose" in redacted


def test_redact_text_keeps_non_reference_semantic_text():
    assert redact_text("candidate 1 (red block)") == "candidate 1 (red block)"
