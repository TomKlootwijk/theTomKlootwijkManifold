# Projected 7-Torus demo notes

1. Install this package in a Unity 6000.3.22f1 URP project.
2. Choose **GameObject > Tom Klootwijk Manifold > Create Projected 7-Torus Slice**.
3. Position the camera at roughly `(0, 0, -3)` looking at the origin.
4. Enter Play Mode to animate the phase slice.
5. Select the object to see seven projected direction gizmos.
6. Optionally create **Rounded SDF Surrogate**. Keep its transform scale uniform; the volume shader is a visual surrogate and does not render the exact 7D torus.

Default projected mesh complexity:
- Vertices: `(96+1)*(48+1) = 4,753`.
- Triangles: `2*96*48 = 9,216`.
- Vertex update work: proportional to `7*4,753` trigonometric phase contributions per animated frame.
