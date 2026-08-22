# Factual-correctness assessment

## Verdict

The corrected package is factually correct **within its explicit bounded profile**.
The original universal or literal runtime `o(1)` claim is not correct.

## Audit of the supplied KLB SeedChain GPU 0.3.0 package

The supplied source package was unpacked, its SHA-256 manifest checked, rebuilt in
a clean CPU-only directory, and both included CTest suites passed under GCC 14.2,
CMake 3.31.6 and Python 3.13.5.

Useful ideas retained:

- direct seed reconstruction instead of mandatory dense frame materialization;
- fixed predictor loops, such as the five-iteration orbit solve;
- bounded checkpoint depth;
- sparse novelty records;
- explicit support, compatibility, guard and event gates;
- exact CPU/direct/dense comparison as an acceptance requirement.

Missing conditions that prevented a strict general constant-query statement:

1. `KLSC1` stores one 96-byte node per frame, so archive storage is `Theta(N)` in
   frame count even when the compression factor is favorable.
2. Per-node novelty lookup is a binary search over variable `novelty_count`; the
   checkpoint walk is bounded, but lookup work is not profile-bounded unless a
   maximum novelty count is also enforced.
3. A high horizon-relative model ratio is not lossless compression of an arbitrary
   pre-existing dense trajectory.
4. GPU wall-clock performance, cache residency, launch overhead and energy are
   hardware- and workload-dependent.

## Corrections implemented here

- segment records occur only for model/event changes, not every display frame;
- each segment carries a fixed compile-time correction-slot array;
- each query scans fixed segment and correction bounds;
- corrections are cumulative, so the hot query has no parent traversal;
- overflow is rejected instead of silently changing the complexity class;
- lowercase `o(1)` is used only for normalized storage versus increasing dense
  sampling of a fixed represented interval;
- the implementation separates mathematical state, field/guard, interval
  certification, event and transition semantics.

## Remaining boundaries

- CPU correctness was executed here; CUDA compilation and physical-GPU execution
  were not available in this environment.
- The bundled quadratic predictor is an exact evaluation of its declared model,
  not a universal exact model of physical motion.
- Floating-point evaluation is finite precision.
- A workload with dense, unpredictable novelty can fail the profile and lose the
  storage advantage.
- Producing `N` output states still requires `Theta(N)` work and output memory.
- Requester attribution is recorded but not independently verified.
