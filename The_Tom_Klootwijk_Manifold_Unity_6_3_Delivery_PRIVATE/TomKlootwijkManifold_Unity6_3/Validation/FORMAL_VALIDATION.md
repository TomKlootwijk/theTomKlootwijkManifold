# Formal validation summary

## Definition

For positive radii `r[0]...r[6]`, define

```text
K_TK(r) = { x in R^14 : F_i(x)=x[2i]^2+x[2i+1]^2-r[i]^2=0, i=0..6 }.
```

Equivalently, `K_TK(r) = Product[i=0..6] S^1(r[i])`.

## Smooth-manifold proof

At any point of `K_TK`, row `i` of the Jacobian `DF` has nonzero entries only in columns `2i` and `2i+1`, namely `2*x[2i]` and `2*x[2i+1]`. Because `r[i] > 0`, that pair cannot be `(0,0)`. The seven rows have disjoint supports and are therefore linearly independent. Hence `rank(DF)=7` on the zero set. By the regular-value theorem, `K_TK` is a smooth embedded manifold of dimension `14-7=7`.

## Orthogonality proof

With angular coordinates `theta[i]`,

```text
Phi(theta)[2i]   = r[i] cos(theta[i]),
Phi(theta)[2i+1] = r[i] sin(theta[i]).
```

The coordinate tangent `dPhi/dtheta[i]` has support only in coordinate pair `i`, so tangent vectors for distinct indices have dot product zero. Its norm is `r[i]`; therefore `E_i=(1/r[i]) d/dtheta[i]` is a global orthonormal frame.

## Other properties

- Compact: finite product of circles.
- Connected: finite product of connected circles.
- Intrinsically flat under the product metric `g=sum r[i]^2 dtheta[i]^2`.
- Extrinsically curved in its R^14 embedding.
- Not a 7-sphere: it is a 7-torus, with different topology.

## Unity correspondence

The Unity mesh evaluates `X(u,v,t)=P(Phi(A_t(u,v)))`, where `A_t:T^2->T^7` is an integer-frequency periodic slice and `P:R^14->R^3` is a fixed linear projection. This is a faithful implementation of a projected 2D slice, not a direct rendering of all points of the 7D manifold.

## Validation limits

The included Python validator executes the mathematical checks and source-number checks. The proof above is explicit and self-contained, but it was not machine-checked in Lean, Coq, Isabelle, Agda, or another theorem prover. Unity import/compile/GPU execution was not possible in the build environment because no Unity Editor was installed. Runtime NUnit tests are included for execution in Unity 6.3.
