# Tom Klootwijk CUDA/GPU Execution & Validation Package v1.0.0

## Delivery status

**Overall result:** `PASS_WITH_DOCUMENTED_FULL_HORIZON_SUPPORT_BOUNDARY`

This package delivers the KLB SeedChain GPU 0.3.0 CUDA implementation, the supplied actual RTX execution artifacts, the Tom Klootwijk chrono-topological-geometric formal specification, and an independent validation layer.

The supplied hardware records identify:

- GPU: **NVIDIA GeForce RTX 5070 Ti Laptop GPU**
- compute capability: **12.0**
- CUDA compiler: **NVCC 12.8.61**
- code generation: native **`sm_120`** plus **`compute_120` PTX**
- GPU global memory reported by the run: **12,226.5625 MiB**
- SM count: **46**
- memory bus: **192 bits**

The audit found real CUDA fatbinary sections in all three supplied benchmark executables and cross-checked build output, execution logs, benchmark CSVs, nvidia-smi telemetry, Compute Sanitizer output, cuobjdump evidence, and Nsight Compute reports.

## Validated acceptance results

- Original implementation manifest: **82/82 hashes pass**.
- Fresh Linux CPU build: **2/2 CTest suites pass**.
- Fresh seven-day CPU schedule: **byte-for-byte identical** to the bundled 717-event CSV.
- CUDA build evidence: **NVCC 12.8**, `sm_120` cubin, `compute_120` PTX.
- File workload: **19,353,600 candidates**, **717 events**, direct/dense GPU counters equal, compact payloads equal, no truncation.
- Laptop workload: **33,554,432 candidates**, **1,243 events**, direct/dense GPU counters equal, compact payloads equal, no truncation.
- VRAM workload: **134,217,728 candidates**, **4,970 events**, direct/dense GPU counters equal, compact payloads equal, no truncation.
- Compute Sanitizer smoke run: **0 errors**.
- Telemetry: all three primary runs contain sustained active samples and reach **100% reported GPU utilization**.

## Documented numerical boundary

A supplied strict full-seven-day CPU/GPU counter attempt reports one support-gate difference:

```text
CPU support survivors  19,214,155
GPU support survivors  19,214,154
Difference             -1 candidate
Verified events         717 on both paths
```

The delivered implementation therefore uses an exact **4,096-epoch CPU/GPU oracle prefix**, followed by full-workload equality between direct-seed and dense GPU counters and compact event payloads. Those documented acceptance checks pass. The package is not labeled bit-identical for the entire seven-day support counter.

## Performance result—not a universal speedup

The direct procedural seed path saves the large dense working set and is slightly faster than materializing and then querying dense positions in the three supplied runs. It is nevertheless about **4.48–4.70 times slower** than querying positions that are already resident in dense form. This is a measured memory-versus-compute trade-off:

| Preset | Dense working set | Direct seed p50 | Resident dense p50 | Dense materialize + query p50 | Events |
|---|---:|---:|---:|---:|---:|
| file | 295.313 MiB | 3.689 ms | 0.786 ms | 3.724 ms | 717 |
| laptop | 512.000 MiB | 6.608 ms | 1.474 ms | 6.757 ms | 1,243 |
| vram | 2,048.000 MiB | 26.501 ms | 5.873 ms | 27.180 ms | 4,970 |

The result does **not** establish zero-byte VRAM, constant-time rendering, infinite detail at zero cost, or a general advantage over ray tracing/raymarching. The orbit predictor remains coarse Kepler plus secular J2, not SGP4 or navigation-grade ephemerides.

## Fresh-run disclosure

The independent audit environment exposed no NVIDIA device, `nvidia-smi`, `nvcc`, CUDA libraries, Nsight Compute, or Compute Sanitizer. Accordingly:

- the **CPU verification was freshly executed** during this audit;
- the **GPU execution is the supplied actual RTX hardware run**, independently audited for internal and binary consistency;
- it is **not a newly generated GPU run inside the audit container**.

One-command rerun harnesses are included for a CUDA 12.8+ host:

```bash
./scripts/run_cuda_validation_linux.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_cuda_validation_windows.ps1
```

Set `RUN_VRAM_PRESET=1` on Linux or add `-RunVramPreset` on Windows to include the approximately 2 GiB dense baseline.

## Package map

- `formal_spec/` — Tom Klootwijk CTG substrate/manifold PDF.
- `implementation/klb_seedchain_gpu_v0.3.0/` — complete supplied implementation, CUDA binaries, source, data, original logs, profiler reports, and telemetry.
- `independent_validation/validation_report.md` — human-readable audit.
- `independent_validation/validation_report.json` — machine-readable audit and all check details.
- `independent_validation/fresh_cpu/` — new build, tests, KLOC verification, and deterministic seven-day output.
- `independent_validation/gpu_logs_utf8/` — decoded UTF-8 copies of the principal GPU logs.
- `independent_validation/cuda_binary_audit.txt` — PE/fatbinary/hash inspection.
- `scripts/audit_evidence.py` — dependency-free repeatable evidence audit.
- `scripts/run_cuda_validation_*.{sh,ps1}` — full CUDA rerun harnesses.
- `checksums/SHA256SUMS.txt` — checksums for every delivered file.

## Start here

1. Read `independent_validation/validation_report.md`.
2. Inspect `independent_validation/validation_report.json` for exact check data and hashes.
3. Run `python3 scripts/audit_evidence.py` to repeat the non-GPU artifact audit.
4. Run the platform CUDA validation script on compatible NVIDIA hardware to create a fresh hardware evidence directory.
