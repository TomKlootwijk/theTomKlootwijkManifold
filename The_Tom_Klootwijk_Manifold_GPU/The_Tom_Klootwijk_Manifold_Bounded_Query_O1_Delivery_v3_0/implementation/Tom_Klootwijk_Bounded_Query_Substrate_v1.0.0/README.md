# Tom Klootwijk Bounded-Query Manifold Substrate 1.0.0

This package is a clean formal and executable correction derived from the supplied
`klb_seedchain_gpu_v0.3.0(4).zip` and UGTS-KC 2.0 report.

It does **not** claim little-o runtime. The precise claims are:

1. A single `state_at(object, time)` query has worst-case `O(1)` work with respect
   to represented dense sample count and history length, because the profile fixes
   the maximum segment and patch slot counts at compile time.
2. For a fixed continuous model interval, the encoded-to-dense storage ratio is
   `o(1)` as the number of omitted dense samples tends to infinity, provided
   external novelty remains bounded or sublinear.
3. A batch of `Q` queries performs `Theta(Q)` work and produces `Theta(Q)` output.

## Formal carrier

The reference implementation uses the smooth carrier

```text
M = R^3 x S^1
```

and a finite mode label. A finite discrete union of copies of `M` is again a
(possibly disconnected) 4-dimensional smooth manifold. The architecture is
parameterized in the formal specification and does not depend on a seven-line
construction, a Sierpinski address, a parity mutation, or a renderer.

## What was retained from the supplied implementation

- fixed-size seed records;
- closed-form state-at-time evaluation;
- sparse novelty/correction records;
- explicit support, compatibility, interval certification, guard, transition and lineage separation;
- CPU/device-shared functions and one-query-per-thread CUDA mapping;
- hard rejection when a bounded profile is exceeded.

## What was changed

- no node is stored for every display frame;
- no parent-chain traversal is used in the hot query;
- no variable-size binary search is used in the hot query;
- every segment contains a fixed number of cumulative correction slots;
- segment and patch limits are compile-time profile constants;
- lowercase `o(1)` is reserved for a normalized storage ratio, not execution time;
- topology or mode changes are explicit, not inferred from an SDF zero alone.

## Build

CPU reference and tests:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DTKM_BUILD_CUDA=OFF
cmake --build build -j
ctest --test-dir build --output-on-failure
./build/tkm_demo
```

CUDA, when a supported NVIDIA toolkit and device are available:

```bash
cmake -S . -B build-cuda -DCMAKE_BUILD_TYPE=Release \
  -DTKM_BUILD_CUDA=ON -DTKM_CUDA_ARCH=native
cmake --build build-cuda -j
./build-cuda/tkm_cuda_smoke
```

The CUDA kernel performs one independent bounded query per thread. GPU launch,
transfer, scheduling, cache and throughput costs remain target-dependent and are
not implied by the asymptotic query bound.

## Profile failure rule

If an archive needs more segments or more active corrections per segment than the
chosen compile-time profile permits, the builder must reject it, split it into a
new explicitly addressed archive, select a larger profile, or use a variable-cost
representation. It must not silently retain the `O(1)` claim.

## Privacy and attribution

The runtime headers and CUDA source contain no personal identifier. The private
delivery contains a separate requester-supplied attribution notice. That notice is
not independent proof of identity, authorship, ownership, patentability or priority.
