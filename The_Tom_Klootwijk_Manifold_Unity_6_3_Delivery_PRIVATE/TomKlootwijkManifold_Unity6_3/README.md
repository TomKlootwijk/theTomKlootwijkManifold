# The Tom Klootwijk Manifold - Unity 6.3 delivery

This archive contains a mathematically rigorous replacement for the informal proposal in the supplied source dossier, plus a Unity 6.3 implementation.

## Formal object

```text
K_TK(r) = Product[i=0..6] Circle(r[i])
        = { x in R^14 : x[2i]^2 + x[2i+1]^2 = r[i]^2, i=0..6 }.
```

This is a smooth, compact, 7-dimensional flat torus embedded in R^14. It has seven globally defined pairwise orthonormal tangent directions. The Unity component renders a 3D projection of a periodic 2D slice of this 7D object; it does not claim that seven-way orthogonality survives projection into 3D.

## Target

- Unity Editor: 6000.3.22f1 baseline; package declares Unity 6000.3.
- Universal Render Pipeline: 17.3.0.
- Edition code: U6.3-A36 (Unity 6.3; author age 36 on the occasion date).
- Occasion capture: 2026-08-22T06:34:39+02:00 / 2026-08-22T04:34:39Z.
- Public author-record fingerprint: `7d85cc5019309659b8279866b0bf6dde69ef18373d25dc71051fe8824ee2e3b4`.

## Install

1. Create or open a Unity 6.3 URP project.
2. Open **Window > Package Manager**.
3. Select **+ > Add package from disk...**.
4. Choose `UnityPackage/com.tomklootwijk.manifold/package.json`. Alternatively, choose **Add package from tarball** and select `UnityPackage/com.tomklootwijk.manifold-1.0.0.tgz`.
5. Use **GameObject > Tom Klootwijk Manifold** to create either the exact projected slice or the optional rounded SDF surrogate.
6. Run the package tests in **Window > General > Test Runner**.

## Important status

The mathematical proof and independent numerical validator pass. The proof is explicit and self-contained, but it was not machine-checked in a theorem prover. This environment did not contain a Unity Editor executable, so an actual Unity import, C# compilation, shader compilation, and GPU run were not executed here. The package is written against Unity 6.3/URP 17.3 APIs and includes runtime tests for import-time verification.

## Privacy

The private PDF and `Documentation/PRIVATE_AUTHOR_RECORD.txt` contain the full BSN string supplied by the author. Do not publish those files. The runtime package contains only a SHA-256 fingerprint, not the supplied BSN itself.
