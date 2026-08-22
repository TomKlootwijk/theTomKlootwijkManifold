# Spatiotemporal SDF addendum sample notes

1. Use **GameObject > Tom Klootwijk Manifold > Create Spatiotemporal Torus SDF Witness**.
2. Keep the generated cube uniformly scaled. The shader evaluates an exact object-space ring-torus SDF and sphere-traces its zero set.
3. `TKSpacetimeTorusSdfWitness` varies the major and minor radii smoothly while enforcing `0 < minorRadius(t) < majorRadius(t)`.
4. The torus is a dimension-reduced witness slice. The exact full addendum mathematics is implemented by `TKSpacetimeSubstrateMath` in `R^14`.
5. Run the package Runtime tests to check shell residuals, the Eikonal identity, regular-tube guards, and the little-o temporal consistency test.
