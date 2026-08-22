"""Support, compatibility, certified crossings and chrono-latches."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from .geometry import ImplicitField
from .model import HybridState


@dataclass(frozen=True)
class Evaluation:
    guard: float
    supported: bool
    compatible: bool
    confidence: float = 1.0


@dataclass(frozen=True)
class Crossing:
    verified: bool
    entering: bool
    interpolation: float
    crossing_time: float
    minimum_abs_guard: float
    reason: str


def certify_crossing(
    previous: Evaluation,
    current: Evaluation,
    previous_time: float,
    current_time: float,
    *,
    crossing_band: float,
    confidence_minimum: float = 0.0,
) -> Crossing:
    if current_time <= previous_time:
        raise ValueError("crossing times must be strictly increasing")
    if crossing_band < 0.0:
        raise ValueError("crossing_band must be non-negative")
    sign_change = (previous.guard > 0.0 >= current.guard) or (
        previous.guard <= 0.0 < current.guard
    )
    minimum_abs = min(abs(previous.guard), abs(current.guard))
    bounded = minimum_abs <= crossing_band
    gates = (previous.supported or current.supported) and previous.compatible and current.compatible
    confidence = min(previous.confidence, current.confidence) >= confidence_minimum
    denominator = previous.guard - current.guard
    interpolation = previous.guard / denominator if abs(denominator) > 1.0e-20 else 0.5
    interpolation = min(1.0, max(0.0, interpolation))
    crossing_time = previous_time + interpolation * (current_time - previous_time)
    verified = sign_change and bounded and gates and confidence
    if not sign_change:
        reason = "no-sign-change"
    elif not bounded:
        reason = "outside-crossing-band"
    elif not gates:
        reason = "support-or-compatibility-rejected"
    elif not confidence:
        reason = "confidence-below-minimum"
    else:
        reason = "verified"
    return Crossing(
        verified=verified,
        entering=previous.guard > 0.0 >= current.guard,
        interpolation=interpolation,
        crossing_time=crossing_time,
        minimum_abs_guard=minimum_abs,
        reason=reason,
    )


def evaluate_implicit_guard(
    field: ImplicitField,
    point: Sequence[float],
    *,
    epsilon: float,
    supported: bool = True,
    compatible: bool = True,
    confidence: float = 1.0,
) -> Evaluation:
    if epsilon < 0.0:
        raise ValueError("epsilon must be non-negative")
    guard = abs(field(point)) - epsilon
    return Evaluation(guard, supported, compatible, confidence)


def apply_chrono_latch(
    state: HybridState,
    crossing: Crossing,
    *,
    target_mode: str,
    transition_id: str,
    auxiliary_patch: Mapping[str, object] | None = None,
) -> HybridState:
    if not crossing.verified:
        return state
    patch = {"latch": 1, "crossing_reason": crossing.reason}
    if auxiliary_patch:
        patch.update(auxiliary_patch)
    return state.transitioned(
        time=crossing.crossing_time,
        target_mode=target_mode,
        transition_id=transition_id,
        auxiliary_patch=patch,
    )
