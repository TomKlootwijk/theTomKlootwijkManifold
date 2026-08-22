# The Tom Klootwijk Manifold - Unity 6.3 delivery v1.1

This private archive contains the original rigorous 7-torus specification, a new formal
spatiotemporal signed-distance-field addendum, public/private PDF editions, an installable
Unity Package Manager package, source dossiers, validators, reports, and checksums.

## Core manifold

```text
K_TK(r) = Product[i=0..6] S^1(r[i])
        = { x in R^14 : x[2i]^2 + x[2i+1]^2 = r[i]^2, i=0..6 }.
```

For positive radii this is a smooth compact connected 7-torus in R^14. Its product metric
has seven globally defined pairwise orthonormal tangent directions.

## Spatiotemporal tubular SDF addendum

For time `t`, a rigid frame `(Q(t), c(t))`, positive radii `r[i](t)`, and a tube radius
`0 < tau(t) < min_i r[i](t)`, put

```text
y = transpose(Q(t)) * (x - c(t))
Delta[i](x,t) = length(y[2i:2i+1]) - r[i](t)
delta(x,t) = length(Delta(x,t))
D_tau(x,t) = delta(x,t) - tau(t)
```

`delta` is the exact Euclidean distance to the moving 7-torus core. The scalar field
`D_tau` is the signed distance to the regular tube boundary. Its zero set is a smooth
spatial 13-manifold diffeomorphic to `T^7 x S^6`; including time gives
`T^7 x S^6 x I`. In the regular band, `|grad_x D_tau| = 1`, and the shell's normal
velocity is `V_n = -partial_t D_tau`.

The lowercase condition

```text
sup_B |D_hat_h - D_tau| = o(1), h -> 0
```

means vanishing approximation error. It is deliberately separated from algorithmic
complexity: one exact seven-factor field query is fixed-size `O(7)=O(1)` relative to
variable scene size, while an image still scales with pixels and march steps.

## Unity target and installation

- Package: `com.tomklootwijk.manifold@1.1.0`
- Unity API line: `6000.3`
- Universal Render Pipeline: `17.3.0`

Install either by selecting
`UnityPackage/com.tomklootwijk.manifold/package.json` with **Add package from disk**, or
by selecting `UnityPackage/com.tomklootwijk.manifold-1.1.0.tgz` with
**Add package from tarball**.

After installation, use **GameObject > Tom Klootwijk Manifold** to create:

1. a projected periodic 2D slice of the exact 7-torus;
2. an explicitly labelled rounded artistic SDF surrogate; or
3. an animated exact 3D ring-torus SDF witness for the spatiotemporal field machinery.

The 3D witness is not represented as the entire 14-dimensional shell.

## Validation status

The mathematical validator passed 500 randomized samples, exact-distance checks,
zero-set checks, Eikonal checks, regularity-guard checks, and a temporal Taylor remainder
check demonstrating `R(h)/h -> 0`. Static package validation passed structure, JSON,
assembly-definition, delimiter, formula-presence, shader-presence, and privacy checks.
The full proofs are written in the PDF and `Validation/FORMAL_VALIDATION.md`.

A Unity Editor import, C# compilation by Unity, URP shader compilation, and GPU execution
were not performed because no Unity Editor executable was available in the build
environment. NUnit tests are included for the target editor.

## Occasion and attribution record

- Original document: `TKM-U63-A36-20260822-063439`
- Addendum document: `TKM-STSDF-U63-A36-20260822-072511`
- Addendum occasion: `2026-08-22T07:25:11+02:00` / `2026-08-22T05:25:11Z`
- Addendum private-record fingerprint:
  `ee007f23936d94c39d1f96cd1806b2a4f15177a4ba56debb8eb8a23f85027f18`

The chosen names identify this specification edition. They do not by themselves establish
external academic recognition, legal ownership, priority, patent status, or identity
verification.

## Privacy

This is a private delivery. The supplied BSN and birth date occur in expressly marked
private documentation and in the user-supplied source dossiers. They do not occur in the
runtime UPM package. Use the public PDFs for ordinary sharing and do not publish the ZIP.
