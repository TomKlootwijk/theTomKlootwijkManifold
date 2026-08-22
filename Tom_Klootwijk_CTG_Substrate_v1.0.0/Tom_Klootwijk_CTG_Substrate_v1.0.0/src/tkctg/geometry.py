"""Geometry, KLB37 records and implicit-field helpers."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable, Sequence

RHO_BITS = 11
THETA_BITS = 12
PHI_BITS = 10
SYMBOL_BITS = 3
RECORD_BITS = 37
RHO_MASK = (1 << RHO_BITS) - 1
THETA_MASK = (1 << THETA_BITS) - 1
PHI_MASK = (1 << PHI_BITS) - 1
SYMBOL_MASK = (1 << SYMBOL_BITS) - 1
RECORD_MASK = (1 << RECORD_BITS) - 1
THETA_SHIFT = RHO_BITS
PHI_SHIFT = THETA_SHIFT + THETA_BITS
SYMBOL_SHIFT = PHI_SHIFT + PHI_BITS
PARITY_SHIFT = SYMBOL_SHIFT + SYMBOL_BITS


def _clamp(value: float, lower: float, upper: float) -> float:
    return lower if value < lower else upper if value > upper else value


def parity(value: int) -> int:
    return value.bit_count() & 1


def make_record_code(q_rho: int, q_theta: int, q_phi: int, symbol: int) -> int:
    lower = (
        (q_rho & RHO_MASK)
        | ((q_theta & THETA_MASK) << THETA_SHIFT)
        | ((q_phi & PHI_MASK) << PHI_SHIFT)
        | ((symbol & SYMBOL_MASK) << SYMBOL_SHIFT)
    )
    return lower | (parity(lower) << PARITY_SHIFT)


def record_has_even_parity(code: int) -> bool:
    return parity(code & RECORD_MASK) == 0


def record_symbol(code: int) -> int:
    return (code >> SYMBOL_SHIFT) & SYMBOL_MASK


@dataclass(frozen=True)
class DecodeParameters:
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius_scale: float = 1.0
    log_k: float = 15.0

    def __post_init__(self) -> None:
        if self.radius_scale <= 0.0:
            raise ValueError("radius_scale must be positive")
        if self.log_k <= 0.0:
            raise ValueError("log_k must be positive")


def encode_klb37(
    point: Sequence[float],
    parameters: DecodeParameters = DecodeParameters(),
    *,
    symbol: int = 0,
) -> int:
    if len(point) != 3:
        raise ValueError("KLB37 encodes exactly three spatial coordinates")
    local = tuple((float(point[index]) - parameters.center[index]) / parameters.radius_scale for index in range(3))
    radius = math.sqrt(sum(component * component for component in local))
    radius_n = _clamp(radius, 0.0, 1.0)
    rho_n = math.log1p(parameters.log_k * radius_n) / math.log1p(parameters.log_k)
    theta = math.atan2(local[2], local[0]) % (2.0 * math.pi)
    if radius > 1.0e-20:
        phi = math.asin(_clamp(local[1] / radius, -1.0, 1.0))
    else:
        phi = 0.0
    phi_n = phi / math.pi + 0.5

    q_rho = int(round(rho_n * RHO_MASK))
    q_theta = int(round(theta * (1 << THETA_BITS) / (2.0 * math.pi))) & THETA_MASK
    q_phi = int(round(_clamp(phi_n, 0.0, 1.0) * PHI_MASK))
    return make_record_code(q_rho, q_theta, q_phi, symbol)


def decode_klb37(code: int, parameters: DecodeParameters = DecodeParameters()) -> tuple[float, float, float]:
    code &= RECORD_MASK
    q_rho = code & RHO_MASK
    q_theta = (code >> THETA_SHIFT) & THETA_MASK
    q_phi = (code >> PHI_SHIFT) & PHI_MASK
    rho_n = q_rho / RHO_MASK
    theta = q_theta * (2.0 * math.pi / (1 << THETA_BITS))
    phi_n = q_phi / PHI_MASK
    phi = (phi_n - 0.5) * math.pi
    radius_n = math.expm1(rho_n * math.log1p(parameters.log_k)) / parameters.log_k
    radius = radius_n * parameters.radius_scale
    cos_phi = math.cos(phi)
    return (
        parameters.center[0] + radius * cos_phi * math.cos(theta),
        parameters.center[1] + radius * math.sin(phi),
        parameters.center[2] + radius * cos_phi * math.sin(theta),
    )


@dataclass(frozen=True)
class ImplicitField:
    evaluator: Callable[[Sequence[float]], float]
    exact_signed_distance: bool = False
    name: str = "implicit-field"

    def __call__(self, point: Sequence[float]) -> float:
        value = float(self.evaluator(point))
        if not math.isfinite(value):
            raise ValueError(f"{self.name} returned a non-finite value")
        return value

    def sign_class(self, point: Sequence[float], *, tolerance: float = 0.0) -> int:
        value = self(point)
        if abs(value) <= tolerance:
            return 0
        return -1 if value < 0.0 else 1


def sphere_sdf(center: Sequence[float], radius: float) -> ImplicitField:
    if radius <= 0.0:
        raise ValueError("sphere radius must be positive")
    c = tuple(float(value) for value in center)

    def evaluate(point: Sequence[float]) -> float:
        if len(point) != len(c):
            raise ValueError("point dimension does not match sphere center")
        return math.sqrt(sum((float(point[i]) - c[i]) ** 2 for i in range(len(c)))) - radius

    return ImplicitField(evaluate, exact_signed_distance=True, name="sphere-sdf")


def csg_union(first: ImplicitField, second: ImplicitField) -> ImplicitField:
    return ImplicitField(
        lambda point: min(first(point), second(point)),
        exact_signed_distance=False,
        name=f"union({first.name},{second.name})",
    )


def csg_intersection(first: ImplicitField, second: ImplicitField) -> ImplicitField:
    return ImplicitField(
        lambda point: max(first(point), second(point)),
        exact_signed_distance=False,
        name=f"intersection({first.name},{second.name})",
    )


def csg_difference(first: ImplicitField, second: ImplicitField) -> ImplicitField:
    return ImplicitField(
        lambda point: max(first(point), -second(point)),
        exact_signed_distance=False,
        name=f"difference({first.name},{second.name})",
    )


def euclidean_dot(first: Sequence[float], second: Sequence[float]) -> float:
    if len(first) != len(second):
        raise ValueError("dot-product dimensions differ")
    return sum(float(a) * float(b) for a, b in zip(first, second))


def standard_axes(dimension: int) -> tuple[tuple[float, ...], ...]:
    if dimension <= 0:
        raise ValueError("dimension must be positive")
    return tuple(
        tuple(1.0 if row == column else 0.0 for row in range(dimension))
        for column in range(dimension)
    )


def pairwise_orthogonal(vectors: Iterable[Sequence[float]], *, tolerance: float = 1.0e-12) -> bool:
    values = tuple(tuple(float(component) for component in vector) for vector in vectors)
    return all(
        abs(euclidean_dot(values[i], values[j])) <= tolerance
        for i in range(len(values))
        for j in range(i + 1, len(values))
    )
