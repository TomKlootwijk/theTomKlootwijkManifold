# Formal definition: TKM bounded-query manifold substrate

Let `M` be a finite-dimensional `C^1` manifold with a finite implementation atlas,
and let `Q` be a finite discrete mode set. The continuous/discrete carrier is

```text
X = M x Q.
```

Because `Q` is finite and discrete, `X` is a possibly disconnected manifold of
dimension `dim(M)`.

A fixed implementation profile is

```text
beta = (J, K, P, H, W),
```

where `J` is the maximum segment count, `K` the maximum cumulative correction
slots per segment, `P` a bound on predictor work/iterations, `H` a bound on guard
work, and `W` the fixed machine-word/record widths.

The Tom Klootwijk bounded-query substrate is

```text
TKM_beta(M) = (X, Sigma, G, Phi, Seg_J, Delta_K, S, C, R, T, I, L; beta),
```

with:

- `Sigma`: fixed-size seed records;
- `G`: a finite typed grammar/operator family;
- `Phi(s,i,t) in M`: a closed-form or fixed-iteration predictor;
- `Seg_J`: at most `J` non-overlapping time/model segments;
- `Delta_K`: at most `K` cumulative chart-local corrections in each segment;
- `S`: support predicates;
- `C`: compatibility predicates;
- `R`: guard/field functions with explicit error contracts;
- `T`: explicit reset/transition maps;
- `I`: topology and consistency invariants;
- `L`: lineage and external novelty metadata.

For entity `i` and time `t`, let `j(i,t)` be the unique selected segment. The state
query is

```text
base       = Phi(seed[i], i, t)
correction = Delta[j(i,t), i](t)
state      = Retr_base(correction)
```

where `Retr` is a declared retraction on `M`. In the bundled witness,
`M = R^3 x S^1`, so retraction is vector addition in `R^3` and phase addition
modulo `2*pi` in `S^1`.

A guard event is authoritative only when

```text
verified = interval_support_and_compatibility_certificate
        and continuous_guard_along_interval
        and guard_classification_is_certified
        and numeric_error <= event_margin.
```

Endpoint sign separation implies a zero by the intermediate value theorem only on a
certified continuous interval. A field zero is only a candidate. Mode, topology and lineage change only through an
explicit transition/reset map.

## Constant-query theorem

For a fixed profile `beta`, the hot query inspects exactly/boundedly `J` segment
slots, `K` patch slots, one fixed-expression seed, and a bounded guard family.
Therefore there is a constant `c_beta` independent of represented dense sample
count `N`, total archive history, and total entity count such that

```text
T_beta(one indexed entity/time query) <= c_beta,
```

hence the query is `O(1)` with respect to those variables. The constant changes
when the profile changes. A batch of `q` independent queries is `Theta(q)`.

## Correct use of lowercase little-o

Let `B_N` be encoded bytes for a fixed continuous interval and `D_N = N*n*b` the
bytes needed to materialize `N` dense samples for `n` entities with `b` bytes per
state. If the seed/segment model is fixed and external novelty count is bounded or
sublinear, then

```text
B_N / D_N = o(1) as N -> infinity.
```

This is a normalized storage statement. It is not an `o(1)` execution-time claim.
No nontrivial discrete query has wall-clock work tending to zero in the ordinary
RAM/GPU cost model.

## Admissibility conditions

- `segment_count <= J` and active patches per segment `<= K`;
- segments are ordered and non-overlapping, or an explicit priority rule is stored;
- patch object keys are unique per segment;
- all numeric values are finite and within the predictor/retraction domain;
- SDF labels are used only for exact/certified signed distance functions;
- predictor and field error are below the event margin;
- topology changes use declared reset/gluing maps;
- archive selection supplied outside the hot query is not hidden inside the claim.

If a condition fails, the representation must be rejected, split, enlarged under a
new profile, or replaced by a variable-cost/dense method.
