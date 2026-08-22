# CUDA/GPU execution validation report
**Overall status:** `PASS_WITH_DOCUMENTED_FULL_HORIZON_SUPPORT_BOUNDARY`
## What was established
The supplied implementation contains CUDA 12.8 build output for native `sm_120` plus `compute_120` PTX, three PE executables with NVIDIA fatbinary sections, and internally consistent execution records from an NVIDIA GeForce RTX 5070 Ti Laptop GPU (compute capability 12.0). The documented acceptance checks pass: the 4,096-epoch CPU/GPU oracle prefix is exact, direct and dense GPU counters/event payloads agree, compact event output is not truncated, and Compute Sanitizer reports zero errors.
A fresh Linux CPU build was performed in the audit environment. Both CTest suites passed, KLOC1 integrity verified, and the newly generated seven-day pass-event CSV is byte-for-byte identical to the bundled 717-event reference.
## Important boundary
A strict full-horizon CPU/GPU counter run in the supplied evidence records one support-gate difference: CPU `19,214,155` versus GPU `19,214,154`. Both produce `717` verified events, and direct/dense GPU results remain identical. This is why the shipped acceptance command uses a 4,096-epoch exact CPU/GPU oracle plus full-horizon GPU direct/dense event-set equality. The package is therefore marked pass with a documented numerical boundary, not as bit-identical across the entire seven-day support counter.
## Reproduction status
No NVIDIA device, `nvidia-smi`, `nvcc`, CUDA libraries, Nsight Compute, or Compute Sanitizer were available in the independent audit container. Consequently, the GPU execution delivered here is the supplied actual hardware run plus an independent artifact audit; it is not a newly generated GPU run in this container. The package includes one-command Windows and Linux rerun scripts for a CUDA 12.8+ `sm_120` host.
## Check matrix
| Check | Status | Result |
|---|---:|---|
| `original_manifest` | **PASS** | 82/82 original manifest entries verified |
| `fresh_cpu_build_and_tests` | **PASS** | Fresh Linux CPU build completed and both CTest suites passed |
| `fresh_cpu_full_horizon_determinism` | **PASS** | Fresh 7-day CPU pass-event CSV is byte-for-byte identical to the bundled reference |
| `cuda_build_artifacts` | **PASS** | Supplied Windows build evidence shows NVCC 12.8, native sm_120 cubin, compute_120 PTX, and passing host tests |
| `cuda_binary_sections` | **PASS** | All three supplied CUDA benchmark executables contain NVIDIA fatbinary sections |
| `actual_gpu_execution_evidence` | **PASS** | Supplied execution logs satisfy the package's documented GPU acceptance checks and Compute Sanitizer reports zero errors |
| `gpu_results_file` | **PASS** | file GPU CSV has six consistent modes |
| `gpu_results_laptop` | **PASS** | laptop GPU CSV has six consistent modes |
| `gpu_results_vram` | **PASS** | vram GPU CSV has six consistent modes |
| `gpu_telemetry` | **PASS** | nvidia-smi telemetry contains sustained active samples and reaches 100% reported utilization in all three primary runs |
| `full_horizon_cpu_gpu_boundary` | **DOCUMENTED_BOUNDARY** | Full-horizon CPU/GPU support counters differ by one candidate, while verified event count remains 717; the shipped acceptance test therefore uses an exact 4096-epoch oracle prefix |
| `new_gpu_run_in_audit_environment` | **NOT_RUN** | No NVIDIA device, driver tools, CUDA toolkit, or CUDA libraries were exposed in the independent audit environment; the GPU portion is an audit of supplied hardware execution evidence, not a newly generated run |

## Performance interpretation
- **file:** direct-seed p50 is `4.696x` the already-resident dense query, and `0.991x` the dense materialize-plus-query path. Dense working set: `295.313 MiB`; compact events: `717`.
- **laptop:** direct-seed p50 is `4.483x` the already-resident dense query, and `0.978x` the dense materialize-plus-query path. Dense working set: `512.000 MiB`; compact events: `1243`.
- **vram:** direct-seed p50 is `4.512x` the already-resident dense query, and `0.975x` the dense materialize-plus-query path. Dense working set: `2048.000 MiB`; compact events: `4970`.

The result is a measured memory-versus-compute trade-off, not evidence of zero-byte VRAM, constant-time rendering, or a universal speedup. The included predictor remains a coarse Kepler+J2 benchmark model, not SGP4/navigation.
