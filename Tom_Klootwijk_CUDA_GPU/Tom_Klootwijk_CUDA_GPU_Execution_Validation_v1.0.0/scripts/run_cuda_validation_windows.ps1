param(
    [string]$OutputDirectory = "",
    [switch]$RunVramPreset
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Source = Join-Path $Root "implementation\klb_seedchain_gpu_v0.3.0"
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $Root ("rerun_results\windows-{0}" -f $Stamp)
}
$Build = Join-Path $OutputDirectory "build-cuda"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$Transcript = Join-Path $OutputDirectory "run.log"
Start-Transcript -Path $Transcript -Force | Out-Null

try {
    foreach ($Command in @("nvidia-smi.exe", "nvcc.exe", "cmake.exe")) {
        if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
            throw "$Command was not found. Run this from an x64 Native Tools prompt with CUDA Toolkit 12.8+ configured."
        }
    }

    & nvidia-smi.exe --query-gpu=timestamp,name,driver_version,compute_cap,memory.total,l2_cache_size,multiprocessor_count,memory.bus_width,power.limit --format=csv |
        Set-Content -Encoding utf8 (Join-Path $OutputDirectory "gpu_identity.csv")
    & nvidia-smi.exe -q | Set-Content -Encoding utf8 (Join-Path $OutputDirectory "nvidia_smi_q.txt")
    & nvcc.exe --version | Set-Content -Encoding utf8 (Join-Path $OutputDirectory "nvcc_version.txt")
    & cmake.exe --version | Set-Content -Encoding utf8 (Join-Path $OutputDirectory "cmake_version.txt")

    & cmake.exe -S $Source -B $Build -A x64 `
        -DKLB_BUILD_CUDA=ON -DKLB_REQUIRE_CUDA=ON -DKLB_CUDA_ARCH=120 2>&1 |
        Tee-Object -FilePath (Join-Path $OutputDirectory "configure.log")
    if ($LASTEXITCODE -ne 0) { throw "CMake configure failed" }

    & cmake.exe --build $Build --config Release --parallel 2 2>&1 |
        Tee-Object -FilePath (Join-Path $OutputDirectory "build.log")
    if ($LASTEXITCODE -ne 0) { throw "CUDA build failed" }

    & ctest.exe --test-dir $Build -C Release --output-on-failure -V 2>&1 |
        Tee-Object -FilePath (Join-Path $OutputDirectory "ctest.log")
    if ($LASTEXITCODE -ne 0) { throw "CTest failed" }

    $Bin = Join-Path $Build "Release"
    $Data = Join-Path $Source "data\orbit\gps_ops_2026-08-16_7d_1s.kloc"
    & (Join-Path $Bin "klb_orbit.exe") inspect $Data 2>&1 |
        Tee-Object -FilePath (Join-Path $OutputDirectory "orbit_inspect.log")
    & (Join-Path $Bin "klb_orbit.exe") verify $Data 2>&1 |
        Tee-Object -FilePath (Join-Path $OutputDirectory "orbit_verify.log")
    & (Join-Path $Bin "klb_orbit.exe") passes $Data `
        --lat 52 --lon 5 --alt-km 0.05 --elevation-deg 10 `
        --crossing-band-deg 0.25 --hours 168 --step-seconds 1 `
        --output (Join-Path $OutputDirectory "pass_events.csv") 2>&1 |
        Tee-Object -FilePath (Join-Path $OutputDirectory "orbit_passes.log")

    function Invoke-OrbitBench([string]$Preset, [int]$Samples, [int]$MinimumMs) {
        & (Join-Path $Bin "klb_orbit_bench.exe") $Data `
            --preset $Preset --query crossing --mode all --write-events `
            --samples $Samples --min-sample-ms $MinimumMs --verify-epochs 4096 `
            --csv (Join-Path $OutputDirectory ("orbit_{0}_results.csv" -f $Preset)) 2>&1 |
            Tee-Object -FilePath (Join-Path $OutputDirectory ("orbit_{0}_console.log" -f $Preset))
        if ($LASTEXITCODE -ne 0) { throw "Orbit benchmark preset '$Preset' failed" }
    }

    Invoke-OrbitBench "file" 9 150
    Invoke-OrbitBench "laptop" 11 250
    if ($RunVramPreset) { Invoke-OrbitBench "vram" 11 250 }

    if (Get-Command compute-sanitizer.exe -ErrorAction SilentlyContinue) {
        & compute-sanitizer.exe --tool memcheck --error-exitcode=99 `
            (Join-Path $Bin "klb_orbit_bench.exe") $Data `
            --preset smoke --query crossing --mode all --write-events `
            --samples 1 --warmup 0 --min-sample-ms 1 --verify-epochs 4096 2>&1 |
            Tee-Object -FilePath (Join-Path $OutputDirectory "compute_sanitizer.log")
        if ($LASTEXITCODE -ne 0) { throw "Compute Sanitizer reported an error" }
    } else {
        "compute-sanitizer.exe not found; sanitizer stage skipped" |
            Set-Content -Encoding utf8 (Join-Path $OutputDirectory "compute_sanitizer_SKIPPED.txt")
    }

    if (Get-Command cuobjdump.exe -ErrorAction SilentlyContinue) {
        & cuobjdump.exe --list-elf (Join-Path $Bin "klb_orbit_bench.exe") |
            Set-Content -Encoding utf8 (Join-Path $OutputDirectory "cuobjdump_list_elf.txt")
        & cuobjdump.exe --dump-resource-usage (Join-Path $Bin "klb_orbit_bench.exe") |
            Set-Content -Encoding utf8 (Join-Path $OutputDirectory "cuobjdump_resources.txt")
    }

    Get-ChildItem -Path $OutputDirectory -File -Recurse |
        Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
        Sort-Object FullName |
        ForEach-Object {
            $Hash = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLowerInvariant()
            $Relative = $_.FullName.Substring($OutputDirectory.Length).TrimStart('\')
            "{0}  .\{1}" -f $Hash, $Relative
        } | Set-Content -Encoding ascii (Join-Path $OutputDirectory "SHA256SUMS.txt")

    "PASS: CUDA validation completed at $OutputDirectory" |
        Set-Content -Encoding utf8 (Join-Path $OutputDirectory "RUN_STATUS.txt")
    Write-Host "PASS: CUDA validation completed at $OutputDirectory"
}
finally {
    Stop-Transcript | Out-Null
}
