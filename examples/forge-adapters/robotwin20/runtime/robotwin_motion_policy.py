"""Shared no-motion admission for RoboTwin capability and controller evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from robotwin_capability_controller import CONTROLLER_SOURCE_SHA256, ControllerLimits
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


def controller_source_path() -> Path:
    """Return the regular file imported as the live bounded controller."""
    module = sys.modules.get(ControllerLimits.__module__)
    module_path = Path(getattr(module, "__file__", "")) if module is not None else None
    if (
        module_path is None
        or not module_path.is_absolute()
        or not module_path.is_file()
        or module_path.is_symlink()
    ):
        raise SimulationProbeError("qualified controller source is unavailable")
    return module_path


def controller_source_digest() -> str:
    """Read the current on-disk source identity for execution-time guards."""
    return _sha_bytes(controller_source_path().read_bytes())


def guard_controller_source_digest(expected_digest: str) -> None:
    """Reject source replacement after a route has been admitted."""
    if controller_source_digest() != expected_digest:
        raise SimulationProbeError("qualified controller source digest drifted")


def validate_controller_source_binding(
    capabilities: Mapping[str, MotionCapabilityDocument],
) -> str:
    """Bind capability evidence to the controller imported by this Runtime."""
    controller_source_path()
    source_digest = CONTROLLER_SOURCE_SHA256
    expected_version = f"source-{source_digest[:16]}"
    for capability in capabilities.values():
        if capability.provider.controller_id != "paos-robotwin-capability-bounded-drive-target":
            raise SimulationProbeError("route controller is not the qualified bounded provider")
        controller_sources = [
            item for item in capability.sources if item.role == "controller_source"
        ]
        if len(controller_sources) != 1:
            raise SimulationProbeError("qualified controller source binding is incomplete")
        source = controller_sources[0]
        if (
            source.sha256 != source_digest
            or capability.provider.controller_version != expected_version
        ):
            raise SimulationProbeError("qualified controller source digest drifted")
    return source_digest


def validate_configured_controller_sources(
    paths: Mapping[str, str | Path],
) -> str:
    """Validate configured capability files before a monitored Runtime starts."""
    required = ("left-motion-capability", "right-motion-capability")
    if any(key not in paths for key in required):
        raise SimulationProbeError("configured motion capability sources are incomplete")
    capabilities: dict[str, MotionCapabilityDocument] = {}
    for arm_id, key in (("left", required[0]), ("right", required[1])):
        try:
            path = Path(paths[key])
            payload = json.loads(path.read_text(encoding="utf-8"))
            capability = MotionCapabilityDocument.model_validate(payload)
        except (TypeError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise SimulationProbeError("configured motion capability source is invalid") from exc
        if capability.arm_id != arm_id:
            raise SimulationProbeError("configured motion capability arm binding is invalid")
        capabilities[arm_id] = capability
    return validate_controller_source_binding(capabilities)


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
    source_digest = validate_controller_source_binding(capabilities)
    return {
        "controller_qualification": qualification_binding,
        "motion_capability_documents": capabilities,
        "controller_source_sha256": source_digest,
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


__all__ = [
    "controller_limits",
    "controller_source_digest",
    "controller_source_path",
    "guard_controller_source_digest",
    "validate_configured_controller_sources",
    "validate_controller_source_binding",
    "validate_motion_policy_bindings",
]
