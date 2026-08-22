#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

OUT = Path(__file__).with_name("validation_report.json")

ORIGINAL_CANONICAL = "Tom Klootwijk|NL200678942|1990-07-10"
ORIGINAL_SHA = "7d85cc5019309659b8279866b0bf6dde69ef18373d25dc71051fe8824ee2e3b4"
ADDENDUM_CANONICAL = (
    "definition=The Tom Klootwijk Manifold\n"
    "addendum=Spatiotemporal SDF o(1) Geometrical Topological Substrate\n"
    "author=Tom Klootwijk\n"
    "bsn=NL200678942\n"
    "dob=1990-07-10\n"
    "age=36\n"
    "occasion_local=2026-08-22T07:25:11+02:00\n"
    "occasion_utc=2026-08-22T05:25:11Z\n"
    "document_id=TKM-STSDF-U63-A36-20260822-072511\n"
)
ADDENDUM_SHA = "ee007f23936d94c39d1f96cd1806b2a4f15177a4ba56debb8eb8a23f85027f18"

BASE_RADII = [1.00, 1.07, 0.93, 1.12, 0.88, 1.18, 0.97]
RELATIVE_AMPLITUDES = [0.045, 0.038, 0.041, 0.032, 0.036, 0.029, 0.043]
RADIUS_SPEEDS = [0.31, -0.27, 0.23, -0.19, 0.17, 0.29, -0.21]
RADIUS_PHASES = [
    3.080712791,
    5.014583196,
    0.618194258,
    3.690086659,
    4.519778518,
    3.740420404,
    4.338001794,
]


def norm(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def base4(n: int) -> str:
    if n == 0:
        return "0"
    digits = ""
    while n:
        digits = str(n % 4) + digits
        n //= 4
    return digits


def bsn_11_test(nine_digits: str) -> tuple[int, bool]:
    weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    total = sum(int(digit) * weight for digit, weight in zip(nine_digits, weights))
    return total, total % 11 == 0


def profile(time: float):
    radii: list[float] = []
    radii_velocity: list[float] = []
    for i in range(7):
        argument = RADIUS_SPEEDS[i] * time + RADIUS_PHASES[i]
        scale = 1.0 + RELATIVE_AMPLITUDES[i] * math.sin(argument)
        radii.append(BASE_RADII[i] * scale)
        radii_velocity.append(
            BASE_RADII[i]
            * RELATIVE_AMPLITUDES[i]
            * RADIUS_SPEEDS[i]
            * math.cos(argument)
        )

    center: list[float] = []
    center_velocity: list[float] = []
    for j in range(14):
        factor = j // 2
        amplitude = 0.018 + 0.002 * (j % 3)
        speed = 0.11 + 0.013 * (j + 1)
        phase = RADIUS_PHASES[factor] + 0.37 * (j % 2)
        argument = speed * time + phase
        center.append(amplitude * math.sin(argument))
        center_velocity.append(amplitude * speed * math.cos(argument))

    tube_argument = 0.37 * time + 0.43
    tube_radius = 0.19 + 0.018 * math.sin(tube_argument)
    tube_velocity = 0.018 * 0.37 * math.cos(tube_argument)
    return radii, radii_velocity, center, center_velocity, tube_radius, tube_velocity


def normal_coordinates(point: list[float], radii: list[float], center: list[float] | None = None):
    center = center or [0.0] * 14
    result = []
    for i in range(7):
        px = point[2 * i] - center[2 * i]
        py = point[2 * i + 1] - center[2 * i + 1]
        result.append(math.hypot(px, py) - radii[i])
    return result


def core_distance(point: list[float], radii: list[float], center: list[float] | None = None):
    return norm(normal_coordinates(point, radii, center))


def tubular_sdf(point: list[float], radii: list[float], tube_radius: float, center=None):
    return core_distance(point, radii, center) - tube_radius


def embed_core(theta: list[float], radii: list[float], center: list[float] | None = None):
    center = center or [0.0] * 14
    point = [0.0] * 14
    for i in range(7):
        point[2 * i] = center[2 * i] + radii[i] * math.cos(theta[i])
        point[2 * i + 1] = center[2 * i + 1] + radii[i] * math.sin(theta[i])
    return point


def embed_shell(theta, unit_normal, radii, tube_radius, center=None):
    center = center or [0.0] * 14
    point = [0.0] * 14
    for i in range(7):
        factor_radius = radii[i] + tube_radius * unit_normal[i]
        point[2 * i] = center[2 * i] + factor_radius * math.cos(theta[i])
        point[2 * i + 1] = center[2 * i + 1] + factor_radius * math.sin(theta[i])
    return point


def nearest_core_point(point, radii, center=None):
    center = center or [0.0] * 14
    nearest = [0.0] * 14
    for i in range(7):
        px = point[2 * i] - center[2 * i]
        py = point[2 * i + 1] - center[2 * i + 1]
        rho = math.hypot(px, py)
        if rho == 0.0:
            nearest[2 * i] = center[2 * i] + radii[i]
            nearest[2 * i + 1] = center[2 * i + 1]
        else:
            nearest[2 * i] = center[2 * i] + radii[i] * px / rho
            nearest[2 * i + 1] = center[2 * i + 1] + radii[i] * py / rho
    return nearest


def spatial_gradient(point, radii, center=None):
    center = center or [0.0] * 14
    delta = normal_coordinates(point, radii, center)
    distance = norm(delta)
    if distance == 0.0:
        raise ValueError("gradient undefined on core")
    gradient = [0.0] * 14
    for i in range(7):
        px = point[2 * i] - center[2 * i]
        py = point[2 * i + 1] - center[2 * i + 1]
        rho = math.hypot(px, py)
        coefficient = delta[i] / distance
        gradient[2 * i] = coefficient * px / rho
        gradient[2 * i + 1] = coefficient * py / rho
    return gradient


def temporal_derivative_identity(point, center, center_velocity, radii, radii_velocity, tube_velocity):
    delta = []
    delta_velocity = []
    for i in range(7):
        px = point[2 * i] - center[2 * i]
        py = point[2 * i + 1] - center[2 * i + 1]
        rho = math.hypot(px, py)
        delta.append(rho - radii[i])
        radial_center_velocity = (
            px * center_velocity[2 * i] + py * center_velocity[2 * i + 1]
        ) / rho
        delta_velocity.append(-radial_center_velocity - radii_velocity[i])
    distance = norm(delta)
    return sum(delta[i] * delta_velocity[i] / distance for i in range(7)) - tube_velocity


def main() -> None:
    assert hashlib.sha256(ORIGINAL_CANONICAL.encode()).hexdigest() == ORIGINAL_SHA
    assert hashlib.sha256(ADDENDUM_CANONICAL.encode()).hexdigest() == ADDENDUM_SHA
    assert base4(973) == "33031"
    assert base4(943) == "32233"
    assert base4(937) == "32221"
    assert (943 ^ 937).bit_count() == 2
    bsn_total, bsn_ok = bsn_11_test("200678942")
    assert bsn_total == 154 and bsn_ok

    rng = random.Random(20260822072511)
    max_core_residual = 0.0
    max_exact_distance_error = 0.0
    max_shell_residual = 0.0
    max_eikonal_error = 0.0
    minimum_shell_pair_radius = math.inf
    sample_count = 500

    for _ in range(sample_count):
        time = rng.uniform(-10.0, 10.0)
        radii, _, center, _, tube_radius, _ = profile(time)
        assert 0.0 < tube_radius < min(radii)

        theta = [rng.uniform(-math.pi, math.pi) for _ in range(7)]
        core = embed_core(theta, radii, center)
        max_core_residual = max(max_core_residual, norm(normal_coordinates(core, radii, center)))

        arbitrary = [rng.uniform(-2.0, 2.0) for _ in range(14)]
        nearest = nearest_core_point(arbitrary, radii, center)
        direct_distance = norm([x - y for x, y in zip(arbitrary, nearest)])
        max_exact_distance_error = max(
            max_exact_distance_error,
            abs(core_distance(arbitrary, radii, center) - direct_distance),
        )

        unit_normal = [rng.gauss(0.0, 1.0) for _ in range(7)]
        unit_normal_norm = norm(unit_normal)
        unit_normal = [value / unit_normal_norm for value in unit_normal]
        shell = embed_shell(theta, unit_normal, radii, tube_radius, center)
        max_shell_residual = max(
            max_shell_residual,
            abs(tubular_sdf(shell, radii, tube_radius, center)),
        )
        gradient = spatial_gradient(shell, radii, center)
        max_eikonal_error = max(max_eikonal_error, abs(norm(gradient) - 1.0))

        for i in range(7):
            px = shell[2 * i] - center[2 * i]
            py = shell[2 * i + 1] - center[2 * i + 1]
            minimum_shell_pair_radius = min(minimum_shell_pair_radius, math.hypot(px, py))

    # Lowercase o(1) is verified as a consistency remainder: R(h)/h -> 0.
    t0 = 0.83
    radii, radii_velocity, center, center_velocity, tube_radius, tube_velocity = profile(t0)
    theta = [0.3, 0.9, 1.5, 2.1, 2.8, 4.0, 5.4]
    unit_normal = [0.7, -0.2, 0.45, -0.6, 0.15, 0.3, -0.25]
    unit_normal_norm = norm(unit_normal)
    unit_normal = [value / unit_normal_norm for value in unit_normal]
    fixed_point = embed_shell(theta, unit_normal, radii, tube_radius, center)
    d0 = tubular_sdf(fixed_point, radii, tube_radius, center)
    d_dt = temporal_derivative_identity(
        fixed_point,
        center,
        center_velocity,
        radii,
        radii_velocity,
        tube_velocity,
    )

    step_sizes = [1e-2, 5e-3, 2.5e-3, 1.25e-3]
    remainder_over_h = []
    for h in step_sizes:
        next_radii, _, next_center, _, next_tube, _ = profile(t0 + h)
        next_value = tubular_sdf(fixed_point, next_radii, next_tube, next_center)
        remainder_over_h.append(abs(next_value - d0 - h * d_dt) / h)

    ratios = [
        remainder_over_h[index + 1] / remainder_over_h[index]
        for index in range(len(remainder_over_h) - 1)
    ]
    assert all(value < 0.55 for value in ratios)

    conservative_minimum_radius = min(
        base * (1.0 - amplitude)
        for base, amplitude in zip(BASE_RADII, RELATIVE_AMPLITUDES)
    )
    maximum_tube_radius = 0.19 + 0.018
    assert maximum_tube_radius < conservative_minimum_radius

    report = {
        "status": "PASS",
        "document_id": "TKM-STSDF-U63-A36-20260822-072511",
        "target": {
            "unity_api_line": "6000.3 LTS",
            "verified_patch_baseline": "6000.3.22f1",
            "current_6000_3_stream_observed": "6000.3.23f1",
            "urp": "17.3.0",
        },
        "canonical_definition": {
            "core_worldvolume": "Delta^{-1}(0) ~= T^7 x I",
            "shell_worldvolume": "D_tau^{-1}(0) ~= T^7 x S^6 x I",
            "delta_i": "norm(pair_i) - r_i(t)",
            "scalar_sdf": "D_tau = norm(Delta) - tau(t)",
            "regularity_guard": "0 < tau(t) < min_i r_i(t)",
            "little_o_clause": "sup_B |D_hat_h - D_tau| = o(1) as h -> 0",
        },
        "dimensions": {
            "core_spatial": 7,
            "core_worldvolume": 8,
            "shell_spatial": 13,
            "shell_worldvolume": 14,
            "normal_sphere": 6,
        },
        "randomized_checks": {
            "samples": sample_count,
            "max_core_normal_coordinate_norm": max_core_residual,
            "max_exact_core_distance_error": max_exact_distance_error,
            "max_shell_sdf_residual": max_shell_residual,
            "max_eikonal_norm_error": max_eikonal_error,
            "minimum_sampled_shell_pair_radius": minimum_shell_pair_radius,
        },
        "little_o_temporal_check": {
            "step_sizes": step_sizes,
            "absolute_remainder_divided_by_h": remainder_over_h,
            "successive_ratios": ratios,
            "interpretation": "Ratios approach 1/2 under step halving, consistent with an O(h^2) Taylor remainder and hence R(h)/h = o(1).",
        },
        "topology_guard": {
            "conservative_minimum_factor_radius": conservative_minimum_radius,
            "maximum_profile_tube_radius": maximum_tube_radius,
            "guard_margin": conservative_minimum_radius - maximum_tube_radius,
        },
        "source_number_checks": {
            "973_base4": base4(973),
            "943_base4": base4(943),
            "937_base4": base4(937),
            "943_xor_937": 943 ^ 937,
            "943_to_937_hamming_distance": (943 ^ 937).bit_count(),
            "single_bit_transition_claim": "FAIL",
        },
        "private_identifier_format_check": {
            "eleven_test_weighted_sum": bsn_total,
            "passes_arithmetic_checksum": bsn_ok,
            "identity_verified": False,
        },
        "fingerprints": {
            "original_private_author_record_sha256": ORIGINAL_SHA,
            "addendum_private_author_record_sha256": ADDENDUM_SHA,
        },
        "implementation_validation": {
            "python_math_validator": "PASS",
            "unity_editor_import_compile_shader_gpu_run": "NOT EXECUTED - Unity Editor unavailable in build environment",
        },
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
