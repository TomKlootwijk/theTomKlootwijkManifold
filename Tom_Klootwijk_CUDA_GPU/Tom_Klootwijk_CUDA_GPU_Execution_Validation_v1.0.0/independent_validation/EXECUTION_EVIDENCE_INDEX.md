# GPU execution evidence index

## Build and architecture

- `gpu_logs_utf8/configure_cuda128_console.txt` — CMake detects NVCC 12.8.61.
- `gpu_logs_utf8/build_cuda128_v0.3_console.txt` — compilation commands include native `sm_120` and `compute_120` PTX; ptxas resource output is included.
- `gpu_logs_utf8/ctest_cuda128_console.txt` — two Windows CTest suites pass.
- `gpu_logs_utf8/orbit_cuobjdump_resources.txt` — supplied cuobjdump record shows PTX and ELF fatbins for `sm_120` and kernel resource use.
- `cuda_binary_audit.txt` — independent PE inspection confirms `.nv_fatb` and `.nvFatBi` sections in all three CUDA executables.

## Actual primary GPU runs

- `gpu_logs_utf8/demo_orbit_console.txt` — seven-day file workload, 295.313 MiB dense baseline, 717 events.
- `gpu_logs_utf8/stress_orbit_laptop_console.txt` — 512.000 MiB dense baseline, 1,243 events.
- `gpu_logs_utf8/stress_orbit_vram_console.txt` — 2,048.000 MiB dense baseline, 4,970 events.
- `implementation/klb_seedchain_gpu_v0.3.0/orbit_{file,laptop,vram}_results.csv` — machine-readable timings and counters.
- `implementation/klb_seedchain_gpu_v0.3.0/orbit_{demo,laptop,vram}_gpu_telemetry.csv` — 200 ms nvidia-smi samples.

## Memory and profiling

- `gpu_logs_utf8/compute_sanitizer_orbit_console.txt` — Compute Sanitizer smoke workload, error summary zero.
- `implementation/klb_seedchain_gpu_v0.3.0/orbit_seed_profile.ncu-rep` — Nsight Compute seed-count kernel report.
- `implementation/klb_seedchain_gpu_v0.3.0/orbit_seed_compact_profile.ncu-rep` — Nsight Compute compact-event kernel report.
- `implementation/klb_seedchain_gpu_v0.3.0/orbit_seed_profile_details.txt` and `orbit_seed_compact_profile_details.txt` — exported profile details.

## Numerical boundary evidence

- `gpu_logs_utf8/orbit_full_horizon_oracle_console.txt` — strict full-horizon CPU/GPU support count differs by one candidate.
- `validation_report.md` — explains why the formal acceptance uses an exact 4,096-epoch CPU/GPU prefix plus full direct/dense GPU event equality.

## Fresh independent CPU work

- `fresh_cpu/configure.log`, `build.log`, `ctest.log` — fresh GNU C++ build and two passing test suites.
- `fresh_cpu/orbit_verify.log` — KLOC1 hash chain and payload valid.
- `fresh_cpu/orbit_passes.log` — fresh 19,353,600-candidate seven-day run.
- `fresh_cpu/orbit_pass_events_fresh.csv` — hash-identical to the bundled 717-event reference.
