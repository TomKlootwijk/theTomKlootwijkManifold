# Formal validation summary - v1.1

## 1. Original core

For positive radii `r_i`, define

```text
F_i(x) = x[2i]^2 + x[2i+1]^2 - r_i^2, i=0,...,6,
K_TK(r) = F^{-1}(0) = Product[i=0..6] S^1(r_i) subset R^14.
```

On the zero set, Jacobian row `i` is nonzero because its supported coordinate pair has
length `r_i>0`. Different rows have disjoint supports, hence rank seven. The regular-value
theorem gives a smooth embedded manifold of dimension `14-7=7`. The explicit angular
parameterization proves it is `T^7`. Coordinate tangents occupy disjoint coordinate pairs;
after division by `r_i` they form a global orthonormal frame.

## 2. Moving core and normal-coordinate map

Let `t in I`, let `Q(t)` be orthogonal, `c(t) in R^14`, and `r_i(t)>0`. Set

```text
y = Q(t)^T (x-c(t)),
Delta_i(x,t) = length(y[2i:2i+1]) - r_i(t).
```

The moving core is `K_t = Delta(.,t)^{-1}(0)`. Rigid motion preserves distance. In each
orthogonal coordinate pair, the distance to the circle of radius `r_i(t)` is
`|Delta_i|`. Product minimization separates, so

```text
dist(x,K_t)^2 = Sum_i Delta_i(x,t)^2,
delta(x,t) = length(Delta(x,t)) = dist(x,K_t).
```

This is an exact equality, not a distance estimator.

## 3. Regular tubular signed-distance shell

Choose a smooth tube radius satisfying

```text
0 < tau(t) < r_* := inf_{i,t} r_i(t).
```

Define `D_tau(x,t)=delta(x,t)-tau(t)`. The sign now belongs to the codimension-one tube
boundary, not to the codimension-seven core:

```text
D_tau < 0 inside the tube,
D_tau = 0 on the shell,
D_tau > 0 outside the tube.
```

For `theta in T^7` and `u in S^6`, the shell map is

```text
Psi(theta,u,t) = c(t) + Q(t) *
                 ((r_i(t)+tau(t)u_i)(cos theta_i, sin theta_i))_{i=0}^6.
```

The guard makes every factor radius positive. Every shell point uniquely recovers its
seven angles and `u=Delta/tau`, giving a diffeomorphism

```text
Sigma_t ~= T^7 x S^6,
Sigma_worldvolume ~= T^7 x S^6 x I.
```

Thus the spatial shell dimension is `7+6=13`, and the spatiotemporal shell dimension is
14. The moving core worldvolume is `T^7 x I`, dimension 8.

## 4. Eikonal identity

Where coordinate-pair radii are nonzero, the gradients `grad Delta_i` are pairwise
orthonormal. Off the core,

```text
grad D_tau = Sum_i (Delta_i/length(Delta)) grad Delta_i,
|grad D_tau|^2 = Sum_i Delta_i^2/length(Delta)^2 = 1.
```

The tube guard ensures the required regularity on the shell. Consequently the standard
level-set normal-speed identity reduces on `D_tau=0` to

```text
V_n = -partial_t D_tau / |grad_x D_tau| = -partial_t D_tau.
```

## 5. Meaning of lowercase o(1)

For a numerical scale `h` and approximation family `D_hat_h`, the consistency condition is

```text
||D_hat_h-D_tau||_{L-infinity(B)} = o(1), h -> 0,
```

on every compact regular band `B`. It means the error tends to zero. It is not a runtime
class. The deterministic-profile validator also checks

```text
D(t+h)=D(t)+h partial_t D(t)+R(h),   R(h)/h -> 0.
```

## 6. Complexity scope

One exact field evaluation uses seven pair lengths and one seven-vector length. Since the
factor count is fixed, this is `O(7)=O(1)` with respect to variable scene size or image
resolution. A raymarched image with `P` pixels and at most `S` samples remains `O(P*S)`;
all real implementations consume nonzero memory.

## 7. Implementation correspondence

- `TKSpacetimeSubstrateMath.cs`: exact `R^14` embedding, normal coordinates, core distance,
  tubular SDF, gradient, identity-frame temporal derivative, normal velocity, guard, and
  orthogonal-transform validation.
- `TKSpacetimeProfile.cs`: deterministic smooth data with a conservative regularity margin.
- `TKSpacetimeTorusSdfWitness.cs` and `TKSpatiotemporalTorusSDFURP.shader`: an exact animated
  3D ring-torus SDF witness, explicitly not the entire high-dimensional shell.
- `TKManifoldTests.cs`: target-editor NUnit tests for the original core and addendum.

## 8. Executed results and limitations

The standalone Python validator passed 500 randomized samples. Maximum observed errors
were approximately `3.69e-16` (core residual), `6.67e-16` (exact-distance comparison),
`4.72e-16` (shell residual), and `2.23e-16` (Eikonal norm). The deterministic profile has
conservative minimum factor radius `0.84832`, maximum tube radius `0.208`, and guard margin
`0.64032`.

Static package validation passed. Unity Editor import, Unity C# compilation, URP shader
compilation, and GPU execution were not available in the build environment and therefore
remain target-environment checks.
