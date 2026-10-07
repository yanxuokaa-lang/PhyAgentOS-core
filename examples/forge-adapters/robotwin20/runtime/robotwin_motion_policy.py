"""Shared no-motion admission for RoboTwin capability and controller evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from robotwin_capability_controller import ControllerLimits
from robotwin_planning_geometry import SimulationProbeError

from robotwin20_adapter.controller_qualification import (
    ControllerQualification,
    ControllerQualificationError,
    ControllerQualificationEvidence,
    ControllerQualificationPlan,
    ControllerQualificationValidation,
    controller_qualification_digest,
    validate_controller_qualification_result_package,
)
from robotwin20_adapter.motion_capabilities import (
    MotionCapabilityDocument,
    MotionCapabilityValidation,
    motion_capability_digest,
)
from robotwin20_adapter.route_evidence import RouteEvidenceError, _artifact_path


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _artifact(root: Path, ref: str) -> tuple[Path, Mapping[str, Any]]:
    try:
        path = _artifact_path(root, ref)
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RouteEvidenceError) as exc:
        raise SimulationProbeError("motion policy artifact is invalid") from exc
    if not isinstance(value, Mapping):
        raise SimulationProbeError("motion policy artifact must be an object")
    return path, value


def controller_limits(capability: MotionCapabilityDocument) -> ControllerLimits:
    """Adapt a validated public capability document to controller admission."""
    return ControllerLimits(
        joint_order=capability.joint_order,
        position_lower_rad=capability.limits.position_lower_rad,
        position_upper_rad=capability.limits.position_upper_rad,
        velocity_lower_radps=capability.limits.velocity_lower_radps,
        velocity_upper_radps=capability.limits.velocity_upper_radps,
    )


def validate_motion_policy_bindings(
    root: Path,
    request: Mapping[str, Any],
    *,
    robot_identity: str,
) -> dict[str, Any]:
    """Validate capability and qualification evidence before planning or Action."""
    validated_arms: set[str] = set()
    capabilities: dict[str, MotionCapabilityDocument] = {}
    for binding in request["motion_capabilities"]:
        capability_path, capability_payload = _artifact(root, binding["artifact_ref"])
        validation_path, validation_payload = _artifact(root, binding["validation_ref"])
        try:
            capability = MotionCapabilityDocument.model_validate(capability_payload)
            validation = MotionCapabilityValidation.model_validate(validation_payload)
        except ValueError as exc:
            raise SimulationProbeError("motion capability artifact is invalid") from exc
        if (
            capability.robot_identity != robot_identity
            or capability.arm_id != binding["arm_id"]
            or _sha_bytes(capability_path.read_bytes()) != binding["sha256"]
            or motion_capability_digest(capability) != binding["sha256"]
            or _sha_bytes(validation_path.read_bytes()) != binding["validation_sha256"]
            or validation.capability_sha256 != binding["sha256"]
        ):
            raise SimulationProbeError("motion capability binding is invalid")
        validated_arms.add(capability.arm_id)
        capabilities[capability.arm_id] = capability
    if validated_arms != {"left", "right"}:
        raise SimulationProbeError("motion capability arm coverage is invalid")

    qualification_binding = request["controller_qualification"]
    qualification_path, qualification_payload = _artifact(
        root, qualification_binding["artifact_ref"]
    )
    plan_path, plan_payload = _artifact(root, qualification_binding["plan_ref"])
    evidence_path, evidence_payload = _artifact(
        root, qualification_binding["evidence_ref"]
    )
    qualification_validation_path, qualification_validation_payload = _artifact(
        root, qualification_binding["validation_ref"]
    )
    try:
        qualification = ControllerQualification.model_validate(qualification_payload)
        plan = ControllerQualificationPlan.model_validate(plan_payload)
        evidence = ControllerQualificationEvidence.model_validate(evidence_payload)
        qualification_validation = ControllerQualificationValidation.model_validate(
            qualification_validation_payload
        )
        validate_controller_qualification_result_package(
            qualification=qualification,
            plan=plan,
            evidence=evidence,
            validation=qualification_validation,
            qualification_file_sha256=_sha_bytes(qualification_path.read_bytes()),
            plan_file_sha256=_sha_bytes(plan_path.read_bytes()),
            evidence_file_sha256=_sha_bytes(evidence_path.read_bytes()),
            validation_file_sha256=_sha_bytes(
                qualification_validation_path.read_bytes()
            ),
        )
    except (ValueError, ControllerQualificationError) as exc:
        raise SimulationProbeError("controller qualification package is invalid") from exc
    if qualification_binding != {
        "qualification_id": qualification.qualification_id,
        "artifact_ref": qualification_binding["artifact_ref"],
        "sha256": controller_qualification_digest(qualification),
        "plan_ref": qualification.plan_ref,
        "plan_sha256": qualification.plan_sha256,
        "evidence_ref": qualification.evidence_ref,
        "evidence_sha256": qualification.evidence_sha256,
        "validation_ref": qualification.validation_ref,
        "validation_sha256": qualification.validation_sha256,
    }:
        raise SimulationProbeError("controller qualification route binding is invalid")
    plan_bindings = {
        item.arm_id: item.model_dump(mode="json") for item in plan.capability_bindings
    }
    route_bindings = {
        item["arm_id"]: dict(item) for item in request["motion_capabilities"]
    }
    if plan_bindings != route_bindings:
        raise SimulationProbeError("controller qualification capability binding drifted")
    for capability in capabilities.values():
        provider = capability.provider
        identity = qualification.identity
        if (
            identity.robot_identity != capability.robot_identity
            or identity.simulator_id != provider.simulator_id
            or identity.simulator_version != provider.simulator_version
            or identity.controller_id != provider.controller_id
            or identity.controller_version != provider.controller_version
            or identity.runtime_python_version != provider.runtime_python_version
            or identity.robotwin_git_revision != provider.robotwin_git_revision
        ):
            raise SimulationProbeError("controller qualification provider identity drifted")
    return {
        "controller_qualification": qualification_binding,
        "motion_capability_documents": capabilities,
        "execution_input_digests": {
            **{
                item[field]: item[digest_field]
                for item in request["motion_capabilities"]
                for field, digest_field in (
                    ("artifact_ref", "sha256"),
                    ("validation_ref", "validation_sha256"),
                )
            },
            qualification_binding["artifact_ref"]: qualification_binding["sha256"],
            qualification_binding["plan_ref"]: qualification_binding["plan_sha256"],
            qualification_binding["evidence_ref"]: qualification_binding["evidence_sha256"],
            qualification_binding["validation_ref"]: qualification_binding[
                "validation_sha256"
            ],
        },
    }


__all__ = ["controller_limits", "validate_motion_policy_bindings"]
