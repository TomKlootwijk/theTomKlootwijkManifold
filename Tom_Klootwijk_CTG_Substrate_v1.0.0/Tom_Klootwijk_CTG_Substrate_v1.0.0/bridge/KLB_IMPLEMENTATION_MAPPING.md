# Mapping to KLB SeedChain GPU 0.3.0

This bridge identifies where the supplied implementation realizes the formal objects. Paths are relative to the root of `klb_seedchain_gpu_v0.3.0`.

| Formal object | Supplied implementation | Notes |
|---|---|---|
| KLB37 packed chart | `include/klb/core.hpp`, `src/format.cpp` | 11-bit log radius, 12-bit azimuth, 10-bit elevation, 3-bit symbol, 1 parity bit. |
| Logical XOR swizzle | `include/klb/core.hpp::xor_swizzle_16x16` | Self-inverse address permutation inside each 16x16 tile. |
| Discrete Klein gluing | `include/klb/core.hpp::klein_coordinate` | X wraps; odd Y-seam crossings reflect X and set an orientation bit. |
| KLSC1 chrono nodes | `include/klb/seedchain.hpp::SeedChainNodeDisk` | Time, angle, velocity, acceleration, predictor, checkpoint and parent/self hashes. |
| KLSC1 reconstruction | `include/klb/seedchain.hpp::reconstruct_seedchain_point` | Decode, four-level parity grammar, Klein state, cone deformation, similarity transform, novelty sum. |
| Bounded novelty replay | `seedchain_accumulate_novelty` | At most the declared checkpoint stride, capped at 64. |
| KLOC1 seeds and time tiles | `include/klb/orbit.hpp` | 64-byte seed and 64-byte timeline node records. |
| Deterministic orbit flow | `propagate_orbit_seed` | Five fixed Newton iterations for Kepler plus pack-time secular J2 rates. |
| Support/compatibility | `evaluate_orbit_visibility` | Slant-range support and optional route-sector compatibility. |
| Certified sampled crossing | `evaluate_orbit_crossing` | Sign change, crossing band, gates, bounded interpolation and direction. |
| Lineage | `orbit_lineage`, KLSC1 lineage fields | Compact checks plus ordered parent/node state; not durable identity by themselves. |
| Binary integrity | KLSC1/KLOC1 loaders | FNV-1a parent/self and payload checks; not cryptographic signatures. |

## Formal/implementation distinctions

1. The formal definition registry uses SHA-256 content addresses. The binary KLSC1/KLOC1 formats retain their supplied FNV-1a integrity fields.
2. The formal TKM can use any declared geometric dimension. The current KLB37/KLSC1 implementation reconstructs three-dimensional point positions plus discrete topology state.
3. The optional TK7 profile is therefore a separate mathematical profile, not a claim about the current CUDA kernels.
4. The current KLOC1 predictor is coarse and not SGP4/navigation-grade.
5. The implementation proves neither zero VRAM nor zero compute cost; its own benchmark documentation measures reconstruction overhead and crossover conditions.
