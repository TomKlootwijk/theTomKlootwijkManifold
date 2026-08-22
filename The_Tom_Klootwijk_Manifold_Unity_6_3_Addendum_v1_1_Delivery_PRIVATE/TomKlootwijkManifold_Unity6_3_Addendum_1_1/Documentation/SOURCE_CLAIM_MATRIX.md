# Formal assessment of the supplied dossiers

| Source idea | Verdict | Rigorous v1.1 replacement |
|---|---|---|
| Seven mutually perpendicular directions | Retained in the correct dimension | The product torus `T^7` has a global orthonormal tangent frame of seven directions. |
| `(4,4,4,4)` alone defines the substrate | Rejected | A tuple alone is a point/parameter list. The substrate is defined by explicit maps and zero sets in `R^14 x I`. |
| SDF sign separates inside, boundary, and outside | Retained for a codimension-one shell | The core has codimension seven and no canonical scalar inside/outside. The regular tube boundary has `D_tau<0`, `=0`, `>0`. |
| `SDF=0` alone creates geometry or makes a fractal round | Rejected | A zero value selects the zero set of an already specified field. The smooth shell comes from the explicit distance `D_tau=||Delta||-tau`. |
| `|grad d|=1` is automatic for any implicit field | Rejected as general; proved here | Seven pairwise orthonormal normal coordinates imply `|grad_x D_tau|=1` in the regular band. |
| The zero set permanently fixes topology | Narrowed | The shell remains `T^7 x S^6` only while smooth data and `0<tau<min r_i` persist. Guard failure or singularities can change topology. |
| Hadamard sign states give quantum phase to an SDF | Rejected | No quantum state follows from the sign of a classical distance field. |
| Time is the homogeneous graphics coordinate `w` | Rejected | Time is an independent parameter `t in I`; moving geometry is the worldvolume in `R^14 x I`. |
| A higher-order term “chronotemporally latches” slices | Replaced | Consecutive slices are linked by smooth time dependence and the level-set law `V_n=-partial_t D_tau`. |
| Lowercase `o(1)` means constant-time execution | Rejected | `o(1)` means a quantity tends to zero; here it is the approximation error as `h->0`. |
| One field query can be constant work | Retained with scope | Seven is fixed, so a query is `O(7)=O(1)` relative to scene size; rendering remains `O(P*S)` for pixels and samples. |
| 943 to 937 is one bit under LSB/0-indexing | Rejected | `943 XOR 937 = 6`; binary Hamming distance is 2. Index labels do not change it. |
| A parity/LSB flip can link past and future states | Rejected | Temporal evolution is governed by the continuous field data and `partial_t D_tau`; parity does not alter Hamming distance or encode time travel. |
| Base-4 strings 973, 943, 937 | Numerically retained only | `973=33031_4`, `943=32233_4`, `937=32221_4`; no topological or temporal theorem follows. |
| A Sierpinski object is the exact substrate | Not used in the formal object | A fractal can be an optional separate procedural signal, but the proven substrate is the smooth product torus and its regular tube. |
| Procedural representation has zero memory | Rejected | Code, uniforms, render targets, engine resources, and output buffers consume nonzero memory. |

The addendum preserves the source's useful intuition - sign classification, zero-level
surfaces, smooth temporal evolution, compact formulas, and fixed-factor field evaluation -
while replacing unsupported quantum, parity, fractal, and performance claims with a
well-defined tubular-neighborhood construction.
