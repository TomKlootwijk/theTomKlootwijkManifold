# Tom Klootwijk Manifold numerical render

This bundle contains a deterministic computational rendering of one **conforming instance** of the formal TKM 1.0 system. No image-generation model was used.

## What is rendered

The ambient coordinates are

`q = (x, y, z, time, phase, route_lift, profile)`

in a seven-dimensional product space. The typed field is a **generic implicit field**

`f(p,h) = ||p|| - R(p/||p||,h)`

and the Tom Klootwijk boundary is `B_TK = f^(-1)(0)`. The full regular boundary has dimension six. A monitor cannot directly display a six-dimensional set, so the PNG, MP4, GLB and HTML show the three-dimensional **position slice** obtained by fixing the four hidden coordinates. Its visible zero set is a smooth two-dimensional surface.

Seven mutually orthogonal coordinate axes in `R^7` are projected into `R^3` using the fixed matrix recorded in `Tom_Klootwijk_Manifold_Render_Spec.json`. They are guides, not claims that seven projected lines remain mutually orthogonal in three dimensions.

The bounded ternary address is `1021221` (decimal label 943). It modulates seven smooth axis terms. Frequencies 3, 9 and 27 form a finite depth-3 ternary harmonic grammar; this render does not claim an infinite Sierpinski boundary.

## Validation result

- Field kind: generic implicit field (not asserted to be exact signed distance)
- Maximum sampled zero residual: 1.332e-15
- Minimum finite-difference gradient norm: 1.000034
- Conservative analytic radius lower bound: 0.570200
- Sampled radius range: 0.687561 to 1.255301
- Mesh check: {"components": 1, "euler_number": 2, "watertight": true, "winding_consistent": true}

The regularity proof is structural: the radial derivative of `f` is exactly 1 on the zero set, so `df` cannot vanish there. This certifies the chosen field instance as a regular zero-level boundary on its declared domain; it does not certify unrelated physical, performance or authorship claims.

## Files

- `Tom_Klootwijk_Manifold_Render.png` - annotated high-resolution still.
- `Tom_Klootwijk_Manifold_Render.mp4` - bounded hidden-coordinate flow and turntable.
- `Tom_Klootwijk_Manifold_Render.glb` - canonical-slice 3D mesh.
- `Tom_Klootwijk_Manifold_Render.html` - interactive browser view.
- `Tom_Klootwijk_Manifold_Render_Spec.json` - exact formulas, parameters and validation.
- `Tom_Klootwijk_Manifold_Render_Events.json` - verified guard events for the displayed route.
- `render_tkm_manifold.py` - reproducible renderer.
- `SHA256SUMS.txt` - checksums.
