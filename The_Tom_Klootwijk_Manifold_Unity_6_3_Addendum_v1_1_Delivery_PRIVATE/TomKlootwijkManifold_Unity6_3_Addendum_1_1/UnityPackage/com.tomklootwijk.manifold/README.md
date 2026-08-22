# The Tom Klootwijk Manifold package

Target: Unity 6000.3 LTS / URP 17.3.0.

## Exact core

The original object is the 7-torus `Product S^1(r_i)` embedded in `R^14`. `TKProjectedSlice` displays a 3D linear projection of a periodic 2D slice.

## Spatiotemporal SDF addendum

`TKSpacetimeSubstrateMath` implements the exact addendum in fixed 0-indexed dimension:

- vector normal coordinates `Delta_i = length(pair_i) - r_i(t)`;
- exact distance to the core `delta = length(Delta)`;
- regular tubular SDF `D = delta - tau(t)` with `0 < tau(t) < min_i r_i(t)`;
- shell embedding with parameter domain `T^7 x S^6`;
- analytic spatial gradient and identity-frame temporal derivative;
- validation of optional row-major 14x14 transforms as orthogonal within tolerance;
- normal level-set velocity `V_n = -partial_t D` on the shell.

The lowercase `o(1)` clause refers to approximation error tending to zero as a numerical scale `h -> 0`. It is not a runtime-complexity claim. A field evaluation has fixed seven-factor work, so it is `O(1)` only with respect to variable scene size or mesh resolution; image rendering still scales with pixels and ray steps.

## Visual components

- `TKProjectedSlice`: 3D projection of a periodic 2D slice of the 7-torus.
- `TKManifoldVolume`: optional smooth capsule-union art surrogate; not the exact manifold.
- `TKSpacetimeTorusSdfWitness`: exact 3D ring-torus SDF at each time; a dimension-reduced witness, not the complete `T^7 x S^6` shell.

Use the **GameObject > Tom Klootwijk Manifold** menu after installation. Keep raymarched cube objects uniformly scaled.
