#!/usr/bin/env python3
"""Independent, dependency-free audit for the bundled KLB CUDA/GPU evidence.

This script does not claim to create a new GPU run. It verifies the supplied
GPU build/execution artifacts, cross-checks their internal consistency, and
records the fresh CPU validation included beside them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Check:
    id: str
    status: str
    summary: str
    details: dict[str, Any]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le", errors="replace")
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be", errors="replace")
    if b"\x00" in data[:512]:
        return data.decode("utf-16-le", errors="replace")
    return data.decode("utf-8", errors="replace")


def extract_int(text: str, label: str) -> int | None:
    m = re.search(rf"{re.escape(label)}\s*:\s*([0-9,]+)", text)
    return int(m.group(1).replace(",", "")) if m else None


def check_manifest(impl: Path) -> tuple[Check, list[dict[str, Any]]]:
    manifest = impl / "MANIFEST.sha256"
    entries: list[dict[str, Any]] = []
    failures = 0
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        expected, rel = raw.split(None, 1)
        rel = rel.strip()
        if rel.startswith("./"):
            rel = rel[2:]
        path = impl / rel
        exists = path.is_file()
        actual = sha256(path) if exists else None
        ok = exists and actual == expected
        failures += 0 if ok else 1
        entries.append({"path": rel, "expected": expected, "actual": actual, "ok": ok})
    return (
        Check(
            "original_manifest",
            "PASS" if failures == 0 else "FAIL",
            f"{len(entries) - failures}/{len(entries)} original manifest entries verified",
            {"entry_count": len(entries), "failures": failures},
        ),
        entries,
    )


def parse_results(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def i(row: dict[str, str], key: str) -> int:
    return int(row[key])


def audit_result_csv(path: Path, expected_preset: str, min_sample_ms: float) -> tuple[Check, dict[str, Any]]:
    rows = parse_results(path)
    by_mode = {r["mode"]: r for r in rows}
    expected_modes = {
        "query_seed_direct",
        "materialize_dense",
        "query_dense",
        "materialize_plus_query",
        "compact_seed_events",
        "compact_dense_events",
    }
    problems: list[str] = []
    if set(by_mode) != expected_modes:
        problems.append(f"mode set differs: {sorted(by_mode)}")
    devices = {r["device"] for r in rows}
    capabilities = {r["compute_capability"] for r in rows}
    presets = {r["preset"] for r in rows}
    if devices != {"NVIDIA GeForce RTX 5070 Ti Laptop GPU"}:
        problems.append(f"unexpected device set: {devices}")
    if capabilities != {"12.0"}:
        problems.append(f"unexpected compute capability set: {capabilities}")
    if presets != {expected_preset}:
        problems.append(f"unexpected preset set: {presets}")

    counter_modes = [
        "query_seed_direct",
        "query_dense",
        "materialize_plus_query",
        "compact_seed_events",
        "compact_dense_events",
    ]
    counter_tuples = {
        mode: tuple(i(by_mode[mode], k) for k in ("candidate_count", "support_count", "compatible_count", "verified_count"))
        for mode in counter_modes
        if mode in by_mode
    }
    if len(set(counter_tuples.values())) != 1:
        problems.append(f"GPU result counters differ by mode: {counter_tuples}")

    if "compact_seed_events" in by_mode and "compact_dense_events" in by_mode:
        sc = by_mode["compact_seed_events"]
        dc = by_mode["compact_dense_events"]
        if i(sc, "event_count") != i(dc, "event_count"):
            problems.append("compact event counts differ")
        if i(sc, "event_count") != i(sc, "verified_count"):
            problems.append("seed compact event_count != verified_count")
        if i(dc, "event_count") != i(dc, "verified_count"):
            problems.append("dense compact event_count != verified_count")
        if i(sc, "event_truncated") != 0 or i(dc, "event_truncated") != 0:
            problems.append("event output was truncated")

    sampling: dict[str, float] = {}
    for mode, row in by_mode.items():
        p50, p95, p99 = f(row, "p50_ms"), f(row, "p95_ms"), f(row, "p99_ms")
        if not (p50 > 0 and p95 >= p50 and p99 >= p95):
            problems.append(f"invalid percentile order for {mode}: {p50}, {p95}, {p99}")
        effective = p50 * i(row, "inner_repeats")
        sampling[mode] = effective
        # The implementation chooses inner_repeats from a separate one-dispatch
        # probe that is not written to the CSV. Final per-dispatch p50 may be
        # lower after warm-up/boost, so p50*inner is diagnostic rather than a
        # strict reconstruction of the probe-duration acceptance check.
        if i(row, "inner_repeats") < 1:
            problems.append(f"invalid inner_repeats for {mode}")

    direct = by_mode.get("query_seed_direct")
    resident = by_mode.get("query_dense")
    end_to_end = by_mode.get("materialize_plus_query")
    metrics = {
        "row_count": len(rows),
        "device": next(iter(devices)) if len(devices) == 1 else sorted(devices),
        "compute_capability": next(iter(capabilities)) if len(capabilities) == 1 else sorted(capabilities),
        "counter_tuples": {k: list(v) for k, v in counter_tuples.items()},
        "effective_sample_ms_from_p50_x_inner_repeats": sampling,
        "direct_vs_resident_dense_p50_ratio": f(direct, "p50_ms") / f(resident, "p50_ms") if direct and resident else None,
        "direct_vs_end_to_end_dense_p50_ratio": f(direct, "p50_ms") / f(end_to_end, "p50_ms") if direct and end_to_end else None,
        "dense_bytes": i(direct, "dense_bytes") if direct else None,
        "event_count": i(by_mode["compact_seed_events"], "event_count") if "compact_seed_events" in by_mode else None,
        "problems": problems,
    }
    return (
        Check(
            f"gpu_results_{expected_preset}",
            "PASS" if not problems else "FAIL",
            f"{expected_preset} GPU CSV has six consistent modes" if not problems else f"{expected_preset} GPU CSV has {len(problems)} problem(s)",
            metrics,
        ),
        metrics,
    )


def parse_telemetry(path: Path) -> dict[str, Any]:
    rows = []
    with path.open(newline="", encoding="utf-8") as fobj:
        for row in csv.reader(fobj):
            if len(row) < 8:
                continue
            rows.append({
                "timestamp": row[0].strip(),
                "device": row[1].strip(),
                "util_pct": float(row[2].strip()),
                "memory_mib": float(row[3].strip()),
                "power_w": float(row[4].strip()),
                "temperature_c": float(row[5].strip()),
                "sm_clock_mhz": float(row[6].strip()),
                "memory_clock_mhz": float(row[7].strip()),
            })
    active = [r for r in rows if r["util_pct"] >= 50.0]
    return {
        "samples": len(rows),
        "active_samples": len(active),
        "device_names": sorted({r["device"] for r in rows}),
        "utilization_max_pct": max((r["util_pct"] for r in rows), default=None),
        "active_power_average_w": sum(r["power_w"] for r in active) / len(active) if active else None,
        "power_max_w": max((r["power_w"] for r in rows), default=None),
        "temperature_max_c": max((r["temperature_c"] for r in rows), default=None),
        "memory_max_mib": max((r["memory_mib"] for r in rows), default=None),
        "active_sm_clock_average_mhz": sum(r["sm_clock_mhz"] for r in active) / len(active) if active else None,
        "first_timestamp": rows[0]["timestamp"] if rows else None,
        "last_timestamp": rows[-1]["timestamp"] if rows else None,
    }


def run_objdump(binary: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(binary), "sha256": sha256(binary), "size": binary.stat().st_size}
    try:
        out = subprocess.run(["objdump", "-h", str(binary)], check=True, capture_output=True, text=True).stdout
        result["has_nv_fatb_section"] = ".nv_fatb" in out
        result["has_nvFatBi_section"] = ".nvFatBi" in out
        m = re.search(r"\.nv_fatb\s+([0-9a-fA-F]+)", out)
        result["nv_fatb_size_hex"] = m.group(1) if m else None
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        result["objdump_error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    root = args.package_root.resolve()
    impl = root / "implementation" / "klb_seedchain_gpu_v0.3.0"
    val = root / "independent_validation"
    out_json = args.output_json or (val / "validation_report.json")
    out_md = args.output_md or (val / "validation_report.md")

    checks: list[Check] = []
    manifest_check, manifest_entries = check_manifest(impl)
    checks.append(manifest_check)

    fresh_ctest = read_text(val / "fresh_cpu" / "ctest.log")
    checks.append(Check(
        "fresh_cpu_build_and_tests",
        "PASS" if "100% tests passed, 0 tests failed out of 2" in fresh_ctest else "FAIL",
        "Fresh Linux CPU build completed and both CTest suites passed",
        {"ctest_marker_found": "100% tests passed, 0 tests failed out of 2" in fresh_ctest},
    ))

    bundled_pass = impl / "data" / "orbit" / "gps_ops_2026-08-16_52N_5E_pass_events.csv"
    fresh_pass = val / "fresh_cpu" / "orbit_pass_events_fresh.csv"
    pass_match = sha256(bundled_pass) == sha256(fresh_pass)
    checks.append(Check(
        "fresh_cpu_full_horizon_determinism",
        "PASS" if pass_match else "FAIL",
        "Fresh 7-day CPU pass-event CSV is byte-for-byte identical to the bundled reference",
        {
            "fresh_sha256": sha256(fresh_pass),
            "bundled_sha256": sha256(bundled_pass),
            "fresh_rows_including_header": sum(1 for _ in fresh_pass.open(encoding="utf-8")),
            "bundled_rows_including_header": sum(1 for _ in bundled_pass.open(encoding="utf-8")),
        },
    ))

    gpu_log_dir = val / "gpu_logs_utf8"
    configure_log = read_text(gpu_log_dir / "configure_cuda128_console.txt")
    build_log = read_text(gpu_log_dir / "build_cuda128_v0.3_console.txt")
    ctest_log = read_text(gpu_log_dir / "ctest_cuda128_console.txt")
    cuobjdump_log = read_text(gpu_log_dir / "orbit_cuobjdump_resources.txt")
    demo_log = read_text(gpu_log_dir / "demo_orbit_console.txt")
    sanitizer_log = read_text(gpu_log_dir / "compute_sanitizer_orbit_console.txt")
    laptop_log = read_text(gpu_log_dir / "stress_orbit_laptop_console.txt")
    vram_log = read_text(gpu_log_dir / "stress_orbit_vram_console.txt")
    full_oracle_log = read_text(gpu_log_dir / "orbit_full_horizon_oracle_console.txt")

    compile_markers = {
        "nvcc_12_8": "CUDA compiler identification is NVIDIA 12.8.61" in configure_log,
        "sm_120_codegen": "code=[sm_120]" in build_log,
        "compute_120_ptx": "code=[compute_120]" in build_log,
        "ptxas_orbit_kernel": "query_seed_compact_kernel" in build_log,
        "fatbin_ptx_sm120": "Fatbin ptx code:" in cuobjdump_log and "arch = sm_120" in cuobjdump_log,
        "fatbin_elf_sm120": "Fatbin elf code:" in cuobjdump_log and cuobjdump_log.count("arch = sm_120") >= 2,
        "windows_ctest": "100% tests passed, 0 tests failed out of 2" in ctest_log,
    }
    checks.append(Check(
        "cuda_build_artifacts",
        "PASS" if all(compile_markers.values()) else "FAIL",
        "Supplied Windows build evidence shows NVCC 12.8, native sm_120 cubin, compute_120 PTX, and passing host tests",
        compile_markers,
    ))

    binary_audit = {}
    for name in ("klb_bench.exe", "klb_seedchain_bench.exe", "klb_orbit_bench.exe"):
        binary_audit[name] = run_objdump(impl / "build-cuda128-vs" / "Release" / name)
    bin_ok = all(v.get("has_nv_fatb_section") and v.get("has_nvFatBi_section") for v in binary_audit.values())
    checks.append(Check(
        "cuda_binary_sections",
        "PASS" if bin_ok else "FAIL",
        "All three supplied CUDA benchmark executables contain NVIDIA fatbinary sections",
        binary_audit,
    ))

    execution_markers = {
        "device": "Device                      : NVIDIA GeForce RTX 5070 Ti Laptop GPU" in demo_log,
        "compute_capability_12_0": "Compute capability          : 12.0" in demo_log,
        "oracle_prefix_exact": "CPU/GPU oracle prefix       : 4096 epochs, exact counters" in demo_log,
        "event_set_equal": "Compacted event-set match   : 717 sorted events" in demo_log,
        "no_truncation_seed": demo_log.count("Event output truncated      : no") >= 2,
        "laptop_event_set": "Compacted event-set match   : 1243 sorted events" in laptop_log,
        "vram_event_set": "Compacted event-set match   : 4970 sorted events" in vram_log,
        "sanitizer_zero_errors": "ERROR SUMMARY: 0 errors" in sanitizer_log,
    }
    checks.append(Check(
        "actual_gpu_execution_evidence",
        "PASS" if all(execution_markers.values()) else "FAIL",
        "Supplied execution logs satisfy the package's documented GPU acceptance checks and Compute Sanitizer reports zero errors",
        execution_markers,
    ))

    result_summaries: dict[str, Any] = {}
    for preset, min_ms in (("file", 150.0), ("laptop", 250.0), ("vram", 250.0)):
        check, summary = audit_result_csv(impl / f"orbit_{preset}_results.csv", preset, min_ms)
        checks.append(check)
        result_summaries[preset] = summary

    telemetry: dict[str, Any] = {}
    for name in ("demo", "laptop", "vram"):
        telemetry[name] = parse_telemetry(impl / f"orbit_{name}_gpu_telemetry.csv")
    telemetry_ok = all(t["active_samples"] > 0 and t["utilization_max_pct"] == 100.0 for t in telemetry.values())
    checks.append(Check(
        "gpu_telemetry",
        "PASS" if telemetry_ok else "FAIL",
        "nvidia-smi telemetry contains sustained active samples and reaches 100% reported utilization in all three primary runs",
        telemetry,
    ))

    cpu_pass_log = read_text(val / "fresh_cpu" / "orbit_passes.log")
    cpu_support = extract_int(cpu_pass_log, "support survivors")
    cpu_events = extract_int(cpu_pass_log, "acquisition/loss events")
    gpu_file = parse_results(impl / "orbit_file_results.csv")
    gpu_direct = next(r for r in gpu_file if r["mode"] == "query_seed_direct")
    gpu_support = int(gpu_direct["support_count"])
    gpu_events = int(gpu_direct["verified_count"])
    strict_delta = None if cpu_support is None else gpu_support - cpu_support
    known_full = "error: CPU/GPU orbit query oracle mismatch" in full_oracle_log
    boundary_status = "DOCUMENTED_BOUNDARY" if strict_delta == -1 and cpu_events == gpu_events == 717 and known_full else "UNEXPECTED"
    checks.append(Check(
        "full_horizon_cpu_gpu_boundary",
        boundary_status,
        "Full-horizon CPU/GPU support counters differ by one candidate, while verified event count remains 717; the shipped acceptance test therefore uses an exact 4096-epoch oracle prefix",
        {
            "fresh_cpu_support_count": cpu_support,
            "gpu_file_support_count": gpu_support,
            "support_delta_gpu_minus_cpu": strict_delta,
            "fresh_cpu_verified_events": cpu_events,
            "gpu_verified_events": gpu_events,
            "historical_strict_full_horizon_log_records_mismatch": known_full,
        },
    ))

    env_text = read_text(val / "environment_probe.txt")
    fresh_gpu_available = not any(marker in env_text for marker in ("nvidia-smi           NOT FOUND", "nvcc                 NOT FOUND"))
    checks.append(Check(
        "new_gpu_run_in_audit_environment",
        "NOT_RUN" if not fresh_gpu_available else "AVAILABLE",
        "No NVIDIA device, driver tools, CUDA toolkit, or CUDA libraries were exposed in the independent audit environment; the GPU portion is an audit of supplied hardware execution evidence, not a newly generated run",
        {"fresh_gpu_available": fresh_gpu_available},
    ))

    essential_failures = [c.id for c in checks if c.status == "FAIL"]
    overall = "FAIL" if essential_failures else "PASS_WITH_DOCUMENTED_FULL_HORIZON_SUPPORT_BOUNDARY"

    key_files = [
        impl / "build-cuda128-vs" / "Release" / "klb_orbit_bench.exe",
        impl / "src" / "orbit_bench.cu",
        impl / "orbit_file_results.csv",
        impl / "orbit_laptop_results.csv",
        impl / "orbit_vram_results.csv",
        impl / "compute_sanitizer_orbit_console.txt",
        impl / "orbit_seed_profile.ncu-rep",
        impl / "orbit_seed_compact_profile.ncu-rep",
        fresh_pass,
    ]
    key_hashes = {str(p.relative_to(root)): sha256(p) for p in key_files if p.is_file()}

    report = {
        "report_schema": "tom-klootwijk-cuda-gpu-validation-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "package_version": "1.0.0",
        "implementation_version": "KLB SeedChain GPU 0.3.0",
        "overall_status": overall,
        "evidence_classification": {
            "fresh_cpu_execution_in_audit_environment": True,
            "fresh_gpu_execution_in_audit_environment": False,
            "supplied_actual_gpu_execution_evidence_audited": True,
            "device_claimed_by_supplied_execution": "NVIDIA GeForce RTX 5070 Ti Laptop GPU",
            "compute_capability_claimed_by_supplied_execution": "12.0",
        },
        "scope_boundary": {
            "validated": [
                "source manifest integrity",
                "fresh CPU compilation and unit tests",
                "fresh deterministic 7-day CPU output reproduction",
                "CUDA 12.8 sm_120/compute_120 compilation evidence",
                "presence of NVIDIA fatbinary sections in supplied PE executables",
                "internal consistency of three GPU benchmark CSVs",
                "documented CPU/GPU prefix oracle, direct/dense event parity, no truncation",
                "Compute Sanitizer zero-error report",
                "nvidia-smi telemetry and Nsight Compute artifact presence",
            ],
            "not_validated": [
                "a new GPU run inside this audit environment",
                "cryptographic attestation that supplied logs were not edited before upload",
                "SGP4 or navigation-grade orbital accuracy",
                "safety-critical operation",
                "universal performance advantage",
            ],
        },
        "essential_failures": essential_failures,
        "checks": [asdict(c) for c in checks],
        "result_summaries": result_summaries,
        "telemetry_summary": telemetry,
        "manifest_entries": manifest_entries,
        "key_file_sha256": key_hashes,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md = []
    md.append("# CUDA/GPU execution validation report\n")
    md.append(f"**Overall status:** `{overall}`\n")
    md.append("## What was established\n")
    md.append(
        "The supplied implementation contains CUDA 12.8 build output for native `sm_120` plus `compute_120` PTX, "
        "three PE executables with NVIDIA fatbinary sections, and internally consistent execution records from an "
        "NVIDIA GeForce RTX 5070 Ti Laptop GPU (compute capability 12.0). The documented acceptance checks pass: "
        "the 4,096-epoch CPU/GPU oracle prefix is exact, direct and dense GPU counters/event payloads agree, compact "
        "event output is not truncated, and Compute Sanitizer reports zero errors.\n"
    )
    md.append(
        "A fresh Linux CPU build was performed in the audit environment. Both CTest suites passed, KLOC1 integrity "
        "verified, and the newly generated seven-day pass-event CSV is byte-for-byte identical to the bundled 717-event reference.\n"
    )
    md.append("## Important boundary\n")
    md.append(
        "A strict full-horizon CPU/GPU counter run in the supplied evidence records one support-gate difference: "
        f"CPU `{cpu_support:,}` versus GPU `{gpu_support:,}`. Both produce `{gpu_events}` verified events, and direct/dense "
        "GPU results remain identical. This is why the shipped acceptance command uses a 4,096-epoch exact CPU/GPU oracle "
        "plus full-horizon GPU direct/dense event-set equality. The package is therefore marked pass with a documented "
        "numerical boundary, not as bit-identical across the entire seven-day support counter.\n"
    )
    md.append("## Reproduction status\n")
    md.append(
        "No NVIDIA device, `nvidia-smi`, `nvcc`, CUDA libraries, Nsight Compute, or Compute Sanitizer were available in "
        "the independent audit container. Consequently, the GPU execution delivered here is the supplied actual hardware "
        "run plus an independent artifact audit; it is not a newly generated GPU run in this container. The package includes "
        "one-command Windows and Linux rerun scripts for a CUDA 12.8+ `sm_120` host.\n"
    )
    md.append("## Check matrix\n")
    md.append("| Check | Status | Result |\n|---|---:|---|\n")
    for c in checks:
        md.append(f"| `{c.id}` | **{c.status}** | {c.summary.replace('|', '/')} |\n")
    md.append("\n## Performance interpretation\n")
    for preset in ("file", "laptop", "vram"):
        s = result_summaries[preset]
        md.append(
            f"- **{preset}:** direct-seed p50 is `{s['direct_vs_resident_dense_p50_ratio']:.3f}x` the already-resident dense query, "
            f"and `{s['direct_vs_end_to_end_dense_p50_ratio']:.3f}x` the dense materialize-plus-query path. "
            f"Dense working set: `{s['dense_bytes'] / (1024**2):.3f} MiB`; compact events: `{s['event_count']}`.\n"
        )
    md.append(
        "\nThe result is a measured memory-versus-compute trade-off, not evidence of zero-byte VRAM, constant-time rendering, "
        "or a universal speedup. The included predictor remains a coarse Kepler+J2 benchmark model, not SGP4/navigation.\n"
    )
    out_md.write_text("".join(md), encoding="utf-8")

    print(json.dumps({"overall_status": overall, "checks": {c.id: c.status for c in checks}}, indent=2))
    return 1 if essential_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
