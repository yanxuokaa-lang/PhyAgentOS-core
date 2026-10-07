"""Capability-driven command admission for the RoboTwin SAPIEN provider.

This is a provider controller boundary, not a PAOS planner or Gateway.  It
checks every arm command against the immutable MotionCapability snapshot before
forwarding it to SAPIEN drive targets and tracks stop/fault/step settlement.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Sequence


class ControllerCommandError(RuntimeError):
    """A command was rejected before reaching the SAPIEN drive API."""


class CapabilityBoundError(ValueError):
    """A finite command cannot be represented inside declared capability bounds."""


def _float32_boundary_error(value: float) -> float:
    """Return only the round-trip error introduced by a float32 trajectory."""
    try:
        quantized = struct.unpack("!f", struct.pack("!f", value))[0]
    except (OverflowError, struct.error):
        return 0.0
    return abs(quantized - value) + math.ulp(value)


def canonicalize_capability_values(
    values: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
    *,
    label: str,
) -> tuple[float, ...]:
    """Canonicalize float32 boundary round-off without expanding capability limits."""
    converted = tuple(float(value) for value in values)
    lows = tuple(float(value) for value in lower)
    highs = tuple(float(value) for value in upper)
    if not converted or len(converted) != len(lows) or len(converted) != len(highs):
        raise CapabilityBoundError(f"{label} vector length is invalid")
    if any(not math.isfinite(value) for value in (*converted, *lows, *highs)):
        raise CapabilityBoundError(f"{label} vector is non-finite")
    if any(low >= high for low, high in zip(lows, highs)):
        raise CapabilityBoundError(f"{label} capability bounds are invalid")

    admitted: list[float] = []
    for value, low, high in zip(converted, lows, highs):
        if value < low:
            if low - value > _float32_boundary_error(low):
                raise CapabilityBoundError(f"{label} exceeds capability bounds")
            value = low
        elif value > high:
            if value - high > _float32_boundary_error(high):
                raise CapabilityBoundError(f"{label} exceeds capability bounds")
            value = high
        admitted.append(value)
    return tuple(admitted)


class ControllerState(str, Enum):
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    FAULT = "fault"


@dataclass(frozen=True)
class ControllerLimits:
    joint_order: tuple[str, ...]
    position_lower_rad: tuple[float, ...]
    position_upper_rad: tuple[float, ...]
    velocity_lower_radps: tuple[float, ...]
    velocity_upper_radps: tuple[float, ...]

    def __post_init__(self) -> None:
        lengths = {
            len(self.joint_order),
            len(self.position_lower_rad),
            len(self.position_upper_rad),
            len(self.velocity_lower_radps),
            len(self.velocity_upper_radps),
        }
        if lengths != {len(self.joint_order)} or not self.joint_order:
            raise ControllerCommandError("controller limit vector lengths are inconsistent")
        if len(set(self.joint_order)) != len(self.joint_order):
            raise ControllerCommandError("controller joint order is duplicated")
        vectors = (
            self.position_lower_rad,
            self.position_upper_rad,
            self.velocity_lower_radps,
            self.velocity_upper_radps,
        )
        if any(not math.isfinite(value) for vector in vectors for value in vector):
            raise ControllerCommandError("controller limits must be finite")
        if any(low >= high for low, high in zip(self.position_lower_rad, self.position_upper_rad)):
            raise ControllerCommandError("controller position limits are invalid")
        if any(low >= high for low, high in zip(self.velocity_lower_radps, self.velocity_upper_radps)):
            raise ControllerCommandError("controller velocity limits are invalid")


class CapabilityBoundedDriveController:
    """Admit commands, forward accepted targets, and settle provider steps."""

    def __init__(
        self,
        limits: ControllerLimits,
        write_target: Callable[[Sequence[float], Sequence[float]], None],
    ) -> None:
        self.limits = limits
        self._write_target = write_target
        self._state = ControllerState.READY
        self._last_decision = "ready"
        self._pending_step = False
        self._accepted_commands = 0
        self._rejected_commands = 0
        self._settled_steps = 0

    @property
    def status(self) -> str:
        return self._last_decision if self._last_decision == "rejected" else self._state.value

    @property
    def counters(self) -> dict[str, int]:
        return {
            "accepted_commands": self._accepted_commands,
            "rejected_commands": self._rejected_commands,
            "settled_steps": self._settled_steps,
        }

    @property
    def has_pending_step(self) -> bool:
        """Whether this arm has an admitted command awaiting simulator ack."""
        return self._pending_step

    def command(self, position: Sequence[float], velocity: Sequence[float]) -> None:
        if self._state in {ControllerState.STOPPED, ControllerState.FAULT}:
            self._reject(f"controller is {self._state.value}", fault=False)
        if self._pending_step:
            self._reject("previous command has no settled simulator step", fault=True)
        q = self._vector(position, "position")
        dq = self._vector(velocity, "velocity")
        try:
            q = canonicalize_capability_values(
                q,
                self.limits.position_lower_rad,
                self.limits.position_upper_rad,
                label="joint position",
            )
            dq = canonicalize_capability_values(
                dq,
                self.limits.velocity_lower_radps,
                self.limits.velocity_upper_radps,
                label="joint velocity",
            )
        except CapabilityBoundError as exc:
            self._reject(str(exc), fault=False, cause=exc)
        try:
            self._write_target(q, dq)
        except Exception as exc:
            self._state = ControllerState.FAULT
            self._last_decision = "fault"
            raise ControllerCommandError("SAPIEN drive target write failed") from exc
        self._accepted_commands += 1
        self._pending_step = True
        self._state = ControllerState.RUNNING
        self._last_decision = "accepted"

    def before_step(self) -> None:
        if self._state == ControllerState.STOPPED:
            raise ControllerCommandError("controller stop prevents simulator step")
        if self._state == ControllerState.FAULT:
            raise ControllerCommandError("controller fault prevents simulator step")
        if not self._pending_step:
            self._state = ControllerState.FAULT
            self._last_decision = "fault"
            raise ControllerCommandError("simulator step lacks an admitted command")

    def after_step(self) -> None:
        if not self._pending_step:
            self._state = ControllerState.FAULT
            self._last_decision = "fault"
            raise ControllerCommandError("simulator step acknowledgement is unmatched")
        self._pending_step = False
        self._settled_steps += 1
        self._state = ControllerState.READY
        self._last_decision = "ready"

    def dropped_step(self) -> None:
        if not self._pending_step:
            raise ControllerCommandError("dropped-step signal has no pending command")
        self._pending_step = False
        self._state = ControllerState.FAULT
        self._last_decision = "fault"

    def stop(self) -> None:
        self._pending_step = False
        self._state = ControllerState.STOPPED
        self._last_decision = "stopped"

    def fault(self, reason: str) -> None:
        if not reason.strip():
            raise ControllerCommandError("controller fault requires a reason")
        self._pending_step = False
        self._state = ControllerState.FAULT
        self._last_decision = "fault"

    def reset(self) -> None:
        self._pending_step = False
        self._state = ControllerState.READY
        self._last_decision = "reset"

    def _vector(self, values: Sequence[float], label: str) -> tuple[float, ...]:
        try:
            result = tuple(float(value) for value in values)
        except (TypeError, ValueError) as exc:
            self._reject(f"controller {label} command is invalid", fault=True, cause=exc)
        if len(result) != len(self.limits.joint_order):
            self._reject(f"controller {label} command length is invalid", fault=True)
        if any(not math.isfinite(value) for value in result):
            self._reject(f"controller {label} command is non-finite", fault=True)
        return result

    def _reject(
        self,
        reason: str,
        *,
        fault: bool,
        cause: Exception | None = None,
    ) -> None:
        self._rejected_commands += 1
        if fault:
            self._state = ControllerState.FAULT
            self._last_decision = "fault"
        else:
            self._last_decision = "rejected"
        error = ControllerCommandError(reason)
        if cause is not None:
            raise error from cause
        raise error


__all__ = [
    "CapabilityBoundError",
    "CapabilityBoundedDriveController",
    "ControllerCommandError",
    "ControllerLimits",
    "ControllerState",
    "canonicalize_capability_values",
]
