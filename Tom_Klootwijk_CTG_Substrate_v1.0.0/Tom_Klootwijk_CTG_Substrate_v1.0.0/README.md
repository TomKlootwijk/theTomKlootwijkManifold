# Tom Klootwijk Chrono-Topological-Geometric Substrate and Manifold 1.0.0

This package contains a rigorous, executable definition of the **Tom Klootwijk Manifold (TKM)** and the surrounding **chrono-topological-geometric substrate (TK-CTGS)**.

The central result is deliberately precise:

- the TKM is a **hybrid stratified quotient state space** whose regular strata are time-extended geometric manifolds;
- topology is represented by explicit boundary-port gluing, sheet/orientation/route state and guarded transitions;
- chronology is represented by a time domain, deterministic flows or predictors, certified event times and piecewise-constant latch state;
- `SDF = 0` is a boundary/event level set, not automatically a sphere and not automatically an exact distance;
- the supplied KLB37, KLSC1 and KLOC1 implementation paths are concrete profiles of the formal substrate;
- requester identity data is provenance metadata only.

## Package map

```text
report/      PDF and editable LaTeX source
spec/        JSON Schema, formal substrate instance, operator catalog, claims ledger
src/tkctg/   dependency-light Python reference implementation
examples/    executable example and deterministic output
bridge/      mapping to the supplied KLB SeedChain GPU 0.3.0 source tree
sources/     source register, hashes and source-to-definition mapping
validation/  test logs and validation report
checksums/   SHA-256 package checksums
```

## Reproduce the reference validation

From the package root:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python examples/demo.py
```

The PDF can be rebuilt with:

```bash
cd report
latexmk -pdf -interaction=nonstopmode -halt-on-error Tom_Klootwijk_CTG_Substrate_v1.0.0.tex
```

## Relationship to the supplied C++/CUDA implementation

The formal package does not replace the supplied KLB implementation. It names and types the mathematical objects that the implementation realizes. See `bridge/KLB_IMPLEMENTATION_MAPPING.md`.
