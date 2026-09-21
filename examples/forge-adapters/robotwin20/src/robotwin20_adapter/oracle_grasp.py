"""Explicit simulator-oracle grasp provider for the blocks-ranking profile."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any, Mapping

from .persistent_client import PersistentWorkerError

LOGGER = logging.getLogger(__name__)


class OracleGraspProviderError(RuntimeError):
    """The explicit oracle profile could not produce bound grasp evidence."""


class PersistentOracleGraspProvider:
    """Read task-adapter grasps through the existing persistent worker boundary."""

    def __init__(
        self,
        client: Any,
        *,
        provider_to_contact_flat: list[float],
        grounding: Any,
    ) -> None:
        if not callable(getattr(client, "query", None)):
            raise TypeError("oracle grasp provider requires a persistent worker client")
        if (
            not isinstance(provider_to_contact_flat, list)
            or len(provider_to_contact_flat) != 16
        ):
            raise ValueError("provider_T_contact_center must be a flattened 4x4 matrix")
        if not callable(getattr(grounding, "activate_observed_entities", None)):
            raise TypeError("oracle grasp provider requires Adapter grounding")
        self.client = client
        self.provider_to_contact_flat = list(provider_to_contact_flat)
        self.grounding = grounding

    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(request, Mapping):
            raise OracleGraspProviderError("oracle grasp request must be an object")
        try:
            binding_ref = self.grounding.activate_observed_entities(request)
            response = self.client.query(
                "oracle_grasp_candidates",
                {
                    "request": deepcopy(dict(request)),
                    "provider_T_contact_center": list(
                        self.provider_to_contact_flat
                    ),
                    "binding_ref": binding_ref,
                },
            )
        except (KeyError, TypeError, ValueError, OSError, PersistentWorkerError) as exc:
            LOGGER.exception(
                "oracle grasp worker query failed code=%s",
                getattr(exc, "code", None),
            )
            raise OracleGraspProviderError(
                "oracle grasp worker rejected the bound request"
            ) from exc
        response = dict(response)
        transport_ok = response.pop("ok", True)
        request_id = response.pop("request_id", None)
        for key in ("holding_state", "owner", "acquire_invocation_id", "entity_ref"):
            response.pop(key, None)
        required = {
            "candidates",
            "ambiguities",
            "funnel",
            "provider_available",
            "motion_authorized",
            "geometry_source",
            "oracle_evidence_ref",
        }
        if not isinstance(response, Mapping) or set(response) != required:
            LOGGER.error(
                "oracle grasp worker response fields are invalid keys=%s",
                sorted(response),
            )
            raise OracleGraspProviderError("oracle grasp worker response is invalid")
        if (
            transport_ok is not True
            or (request_id is not None and (not isinstance(request_id, str) or not request_id))
            or response["provider_available"] is not True
            or response["motion_authorized"] is not False
            or response["geometry_source"] != "oracle_actor"
            or not isinstance(response["oracle_evidence_ref"], str)
            or not response["oracle_evidence_ref"].startswith("artifact://")
        ):
            LOGGER.error(
                "oracle grasp worker provenance is invalid ok=%r request_id_present=%r "
                "provider_available=%r motion_authorized=%r geometry_source=%r",
                transport_ok,
                request_id is not None,
                response.get("provider_available"),
                response.get("motion_authorized"),
                response.get("geometry_source"),
            )
            raise OracleGraspProviderError("oracle grasp worker provenance is invalid")
        evidence_ref = response["oracle_evidence_ref"]
        candidates = deepcopy(response["candidates"])
        for candidate in candidates:
            provenance = candidate.get("provenance") if isinstance(candidate, dict) else None
            if not isinstance(provenance, list):
                raise OracleGraspProviderError(
                    "oracle grasp candidate provenance is invalid"
                )
            if evidence_ref not in provenance:
                provenance.append(evidence_ref)
        return {
            "candidates": candidates,
            "ambiguities": response["ambiguities"],
            "funnel": response["funnel"],
            "provider_available": response["provider_available"],
            "produced_evidence_refs": [evidence_ref],
        }


__all__ = ["OracleGraspProviderError", "PersistentOracleGraspProvider"]
