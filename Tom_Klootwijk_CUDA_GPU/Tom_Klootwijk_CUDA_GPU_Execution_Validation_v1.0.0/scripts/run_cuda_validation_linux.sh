#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/implementation/klb_seedchain_gpu_v0.3.0"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-$ROOT/rerun_results/linux-$STAMP}"
BUILD="$OUT/build-cuda"
mkdir -p "$OUT"
exec > >(tee "$OUT/run.log") 2>&1

fail() { echo "ERROR: $*" >&2; exit 1; }
command -v nvidia-smi >/dev/null || fail "nvidia-smi not found"
command -v nvcc >/dev/null || fail "nvcc not found; CUDA Toolkit 12.8+ is required"
command -v cmake >/dev/null || fail "cmake not found"

nvidia-smi --query-gpu=timestamp,name,driver_version,compute_cap,memory.total,l2_cache_size,multiprocessor_count,memory.bus_width,power.limit --format=csv > "$OUT/gpu_identity.csv"
nvidia-smi -q > "$OUT/nvidia_smi_q.txt"
nvcc --version > "$OUT/nvcc_version.txt"
cmake --version > "$OUT/cmake_version.txt"

cmake -S "$SRC" -B "$BUILD" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DKLB_BUILD_CUDA=ON \
  -DKLB_REQUIRE_CUDA=ON \
  -DKLB_CUDA_ARCH=120 \
  2>&1 | tee "$OUT/configure.log"
cmake --build "$BUILD" -j 2 2>&1 | tee "$OUT/build.log"
ctest --test-dir "$BUILD" --output-on-failure -V 2>&1 | tee "$OUT/ctest.log"

DATA="$SRC/data/orbit/gps_ops_2026-08-16_7d_1s.kloc"
"$BUILD/klb_orbit" inspect "$DATA" | tee "$OUT/orbit_inspect.log"
"$BUILD/klb_orbit" verify "$DATA" | tee "$OUT/orbit_verify.log"
"$BUILD/klb_orbit" passes "$DATA" \
  --lat 52 --lon 5 --alt-km 0.05 --elevation-deg 10 \
  --crossing-band-deg 0.25 --hours 168 --step-seconds 1 \
  --output "$OUT/pass_events.csv" | tee "$OUT/orbit_passes.log"

run_bench() {
  local preset="$1" samples="$2" min_ms="$3"
  "$BUILD/klb_orbit_bench" "$DATA" \
    --preset "$preset" --query crossing --mode all --write-events \
    --samples "$samples" --min-sample-ms "$min_ms" --verify-epochs 4096 \
    --csv "$OUT/orbit_${preset}_results.csv" \
    2>&1 | tee "$OUT/orbit_${preset}_console.log"
}
run_bench file 9 150
run_bench laptop 11 250
if [[ "${RUN_VRAM_PRESET:-0}" == "1" ]]; then
  run_bench vram 11 250
fi

if command -v compute-sanitizer >/dev/null; then
  compute-sanitizer --tool memcheck --error-exitcode=99 \
    "$BUILD/klb_orbit_bench" "$DATA" \
    --preset smoke --query crossing --mode all --write-events \
    --samples 1 --warmup 0 --min-sample-ms 1 --verify-epochs 4096 \
    2>&1 | tee "$OUT/compute_sanitizer.log"
else
  echo "compute-sanitizer not found; sanitizer stage skipped" | tee "$OUT/compute_sanitizer_SKIPPED.txt"
fi

if command -v cuobjdump >/dev/null; then
  cuobjdump --list-elf "$BUILD/klb_orbit_bench" > "$OUT/cuobjdump_list_elf.txt"
  cuobjdump --dump-resource-usage "$BUILD/klb_orbit_bench" > "$OUT/cuobjdump_resources.txt"
fi

(
  cd "$OUT"
  find . -type f ! -path './SHA256SUMS.txt' -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt
)
echo "PASS: CUDA validation completed at $OUT" | tee "$OUT/RUN_STATUS.txt"
