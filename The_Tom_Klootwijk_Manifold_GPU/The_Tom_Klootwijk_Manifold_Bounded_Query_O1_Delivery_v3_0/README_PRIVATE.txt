The Tom Klootwijk Manifold - Bounded-Query O(1) Delivery v3.0
=============================================================

PRIVATE DELIVERY: contains requester-supplied personal data.

Full requester-supplied identifier/BSN string and date of birth appear in:
- documents/*_PRIVATE.pdf
- implementation/*/AUTHORITY_PRIVATE.md

Do not publish this ZIP or those private files in a repository, issue tracker,
shared workspace, screenshot, public build log, or package registry.

Correct formal result:
- one indexed query is O(1) under the fixed named profile;
- q queries and q outputs are Theta(q);
- encoded/dense storage ratio is o(1) only when novelty is fixed or sublinear as
  dense sampling count grows;
- literal nontrivial runtime o(1) is not claimed.

Validation completed:
- requester source manifest and 2/2 CPU tests passed;
- replacement GCC and Clang C++20 tests passed;
- ASan/UBSan tests passed;
- 20,000 randomized state comparisons passed;
- CUDA source passed a host-side Clang syntax parse with declarations.

Not completed:
- native nvcc compilation;
- physical NVIDIA GPU execution;
- hardware performance or energy measurements.

Document ID: TKM-BQ-O1-20260822-092536
Local record: 2026-08-22T09:25:36+02:00
UTC record: 2026-08-22T07:25:36Z
