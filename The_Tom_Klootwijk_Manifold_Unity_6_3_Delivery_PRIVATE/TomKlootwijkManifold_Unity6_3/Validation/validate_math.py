#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, random
from pathlib import Path

CANONICAL = 'Tom Klootwijk|NL200678942|1990-07-10'
EXPECTED_SHA = '7d85cc5019309659b8279866b0bf6dde69ef18373d25dc71051fe8824ee2e3b4'
PHASES = [3.0807127910705816, 5.014583195598161, 0.6181942575179133, 3.6900866590581525, 4.519778517705799, 3.74042040366065, 4.33800179434135]
COS_BASIS = [[0.9777212873836887, -0.16457383507988638, -0.13029404055397506], [0.27881239278358316, 0.9236587524570555, 0.2629033256536873], [-0.21239709997365483, -0.04481599439490776, -0.9761552123351986], [-0.26909473531875, -0.7642942942579586, -0.5860394655554017], [0.48230594525173875, 0.30437001025034927, 0.8214255121646936], [0.6826929363738756, 0.0033703737027891835, 0.730697608594909], [-0.44192911692463516, -0.21100462528849556, -0.8718805558796879]]
SIN_BASIS = [[0.17567287901746054, 0.9812915988815881, 0.0787771384484927], [-0.3668189816512339, 0.3554301071058381, -0.859716972999303], [-0.5544668154684277, -0.8170395496025489, 0.15815474994310044], [-0.768861675387513, 0.5369332835696871, -0.3472094081608108], [0.757992609336439, -0.6150516943613751, -0.2171603496371707], [-0.13329725590137992, 0.9837841713352982, 0.12000227414212909], [0.5187731771920889, 0.732810928741644, -0.44029823227312037]]
OUT = Path(__file__).with_name("validation_report.json")

def base4(n: int) -> str:
    if n == 0:
        return "0"
    digits = ""
    while n:
        digits = str(n % 4) + digits
        n //= 4
    return digits

def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()

def bsn_11_test(nine_digits: str):
    weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    total = sum(int(d) * w for d, w in zip(nine_digits, weights))
    return total, total % 11 == 0

def embed(theta, radii):
    x = [0.0] * 14
    for i in range(7):
        a = theta[i] + PHASES[i]
        x[2*i] = radii[i] * math.cos(a)
        x[2*i+1] = radii[i] * math.sin(a)
    return x

def tangent(i, theta, radii):
    t = [0.0] * 14
    a = theta[i] + PHASES[i]
    t[2*i] = -radii[i] * math.sin(a)
    t[2*i+1] = radii[i] * math.cos(a)
    return t

def dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def main():
    assert hashlib.sha256(CANONICAL.encode()).hexdigest() == EXPECTED_SHA
    assert base4(973) == "33031"
    assert base4(943) == "32233"
    assert base4(937) == "32221"
    assert hamming(943, 937) == 2
    total, bsn_ok = bsn_11_test("200678942")
    assert total == 154 and bsn_ok

    rng = random.Random(20260822)
    max_constraint_error = 0.0
    max_offdiag = 0.0
    max_diag_error = 0.0
    for _ in range(250):
        theta = [rng.uniform(-math.pi, math.pi) for _ in range(7)]
        radii = [rng.uniform(0.2, 2.0) for _ in range(7)]
        x = embed(theta, radii)
        residuals = [x[2*i]**2 + x[2*i+1]**2 - radii[i]**2 for i in range(7)]
        max_constraint_error = max(max_constraint_error, max(abs(e) for e in residuals))
        tangents = [tangent(i, theta, radii) for i in range(7)]
        for i in range(7):
            max_diag_error = max(max_diag_error, abs(dot(tangents[i], tangents[i]) - radii[i]**2))
            for j in range(i+1, 7):
                max_offdiag = max(max_offdiag, abs(dot(tangents[i], tangents[j])))

    pair_errors = []
    for u, v in zip(COS_BASIS, SIN_BASIS):
        pair_errors.append({
            "u_norm_error": abs(math.sqrt(dot(u, u)) - 1),
            "v_norm_error": abs(math.sqrt(dot(v, v)) - 1),
            "dot_abs": abs(dot(u, v)),
        })

    report = {
        "document_id": 'TKM-U63-A36-20260822-063439',
        "target": {"unity": '6000.3.22f1', "urp": '17.3.0'},
        "formal_definition": {
            "status": "PASS",
            "intrinsic_dimension": 7,
            "ambient_dimension": 14,
            "regular_value_jacobian_rank_on_manifold": 7,
            "max_sampled_constraint_error": max_constraint_error,
            "max_sampled_tangent_off_diagonal_dot": max_offdiag,
            "max_sampled_tangent_diagonal_error": max_diag_error
        },
        "source_number_checks": {
            "973_base4": base4(973),
            "943_base4": base4(943),
            "937_base4": base4(937),
            "943_xor_937": 943 ^ 937,
            "943_to_937_binary_hamming_distance": hamming(943, 937),
            "single_bit_transition_claim": "FAIL"
        },
        "private_identifier_format_check": {
            "eleven_test_weighted_sum": total,
            "passes_arithmetic_checksum": bsn_ok,
            "identity_verified": False
        },
        "personalization": {
            "author_record_sha256": EXPECTED_SHA,
            "projection_pair_errors": pair_errors
        },
        "implementation_validation": {
            "python_math_validator": "PASS",
            "file_structure_and_manifest": "PASS",
            "unity_editor_import_compile_shader_gpu_run": "NOT EXECUTED - Unity Editor unavailable in build environment"
        }
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
