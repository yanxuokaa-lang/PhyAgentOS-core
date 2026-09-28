from __future__ import annotations

import pytest

from PhyAgentOS.planning import (
    ArgumentProjectionError,
    ArgumentProjectionPlan,
    execute_argument_projection,
    project_tool_spec,
)


def _plan() -> ArgumentProjectionPlan:
    return ArgumentProjectionPlan(
        projection_id="candidate_set_for_entity_v1",
        source_field_map={
            "observation_ref": ("observation_ref",),
            "scene_revision": ("scene_revision",),
            "frame_id": ("frame", "frame_id"),
            "calibration_ref": ("calibration_ref",),
            "freshness_ms": ("freshness_ms",),
            "max_age_ms": ("max_age_ms",),
            "candidate_set_ref": ("candidate_set_ref",),
        },
        filtered_collection="candidates",
        filtered_output_field="candidates",
        filtered_join_field="entity_ref",
    )


def test_direct_projection_filters_large_candidate_collection_by_bound_entity():
    candidates = [
        {"candidate_ref": "candidate://red/0", "entity_ref": "entity://red", "score": 0.9},
        {"candidate_ref": "candidate://green/0", "entity_ref": "entity://green", "score": 0.8},
        {"candidate_ref": "candidate://red/1", "entity_ref": "entity://red", "score": 0.7},
    ]
    result = execute_argument_projection(
        _plan(),
        records={
            "grasp-1": (
                {"freshness_ms": 12, "max_age_ms": 1000},
                {
                    "ok": True,
                    "data": {
                        "observation_ref": "observation://scene/camera",
                        "scene_revision": "scene-1",
                        "frame": {"frame_id": "camera", "unit": "m"},
                        "calibration_ref": "artifact://scene/calibration",
                        "candidate_set_ref": "candidate-set://scene/all",
                        "candidates": candidates,
                    },
                },
            )
        },
        literals={"entity_ref": "entity://red"},
        source_record_id="grasp-1",
    )

    assert result["observation_ref"] == "observation://scene/camera"
    assert result["frame_id"] == "camera"
    assert result["candidate_set_ref"] == "candidate-set://scene/all"
    assert result["freshness_ms"] == 12
    assert [item["candidate_ref"] for item in result["candidates"]] == [
        "candidate://red/0",
        "candidate://red/1",
    ]


def test_direct_projection_rejects_missing_source_or_entity_match():
    with pytest.raises(ArgumentProjectionError, match="missing field"):
        execute_argument_projection(
            _plan(),
            records={"grasp-1": ({}, {"data": {}})},
            literals={"entity_ref": "entity://red"},
            source_record_id="grasp-1",
        )

    response = {
        "data": {
            "observation_ref": "observation://scene/camera",
            "scene_revision": "scene-1",
            "frame": {"frame_id": "camera"},
            "calibration_ref": "artifact://scene/calibration",
            "freshness_ms": 0,
            "max_age_ms": 1000,
            "candidate_set_ref": "candidate-set://scene/all",
            "candidates": [{"entity_ref": "entity://green"}],
        }
    }
    with pytest.raises(ArgumentProjectionError, match="no entity_ref matching"):
        execute_argument_projection(
            _plan(),
            records={"grasp-1": ({}, response)},
            literals={"entity_ref": "entity://red"},
            source_record_id="grasp-1",
        )


def test_prepare_tool_spec_declares_projection_without_provider_specific_fields():
    policy = project_tool_spec(
        {
            "tool_id": "manipulation.prepare",
            "semantics": "query",
            "planning": {
                "schema_version": "paos-tool-spec-policy/v1",
                "capabilities": ["manipulation.prepare"],
                "argument_projection": "candidate_set_for_entity_v1",
                "argument_projection_plan": {
                    "projection_id": "candidate_set_for_entity_v1",
                    "source_field_map": {
                        "candidate_set_ref": ["candidate_set_ref"],
                    },
                    "filtered_collection": "candidates",
                    "filtered_output_field": "candidates",
                },
            },
        }
    )

    assert policy.argument_projection == "candidate_set_for_entity_v1"
    assert policy.argument_projection_plan is not None
    assert policy.argument_projection_plan.source_field_map["candidate_set_ref"] == (
        "candidate_set_ref",
    )
