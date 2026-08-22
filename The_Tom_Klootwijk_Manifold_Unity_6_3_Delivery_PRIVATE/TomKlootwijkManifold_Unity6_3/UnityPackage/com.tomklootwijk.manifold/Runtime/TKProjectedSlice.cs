using UnityEngine;
using UnityEngine.Rendering;

namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// Samples X(u,v,t) = P(Phi(A_t(u,v))), a projected 2D periodic slice of the exact 7-torus.
    /// The 3D image may self-intersect and cannot preserve seven-way orthogonality.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public sealed class TKProjectedSlice : MonoBehaviour
    {
        [SerializeField, Range(8, 256)] private int uSegments = 96;
        [SerializeField, Range(8, 256)] private int vSegments = 48;
        [SerializeField, Min(0.001f)] private float projectionScale = 0.36f;
        [SerializeField, Min(0.001f)] private float commonRadius = 1f;
        [SerializeField] private bool animate = true;
        [SerializeField] private float animationRate = 1f;

        private Mesh generatedMesh;
        private Vector3[] vertices;
        private Vector2[] uv;
        private int[] triangles;
        private int builtUSegments = -1;
        private int builtVSegments = -1;

        public int USegments { get => uSegments; set { uSegments = Mathf.Clamp(value, 8, 256); Rebuild(true); } }
        public int VSegments { get => vSegments; set { vSegments = Mathf.Clamp(value, 8, 256); Rebuild(true); } }
        public float ProjectionScale { get => projectionScale; set { projectionScale = Mathf.Max(0.001f, value); Rebuild(false); } }
        public float CommonRadius { get => commonRadius; set { commonRadius = Mathf.Max(0.001f, value); Rebuild(false); } }

        private void OnEnable() => Rebuild(true);

        private void OnValidate()
        {
            uSegments = Mathf.Clamp(uSegments, 8, 256);
            vSegments = Mathf.Clamp(vSegments, 8, 256);
            projectionScale = Mathf.Max(0.001f, projectionScale);
            commonRadius = Mathf.Max(0.001f, commonRadius);
            Rebuild(true);
        }

        private void Update()
        {
            if (!animate || !Application.isPlaying) return;
            UpdateVertices(Time.time * animationRate);
        }

        private void OnDestroy()
        {
            if (generatedMesh == null) return;
            if (Application.isPlaying) Destroy(generatedMesh);
            else DestroyImmediate(generatedMesh);
        }

        public Vector3 Evaluate(float u, float v, float time)
        {
            Vector3 p = Vector3.zero;
            float normalization = projectionScale * commonRadius / Mathf.Sqrt(TKManifoldMath.IntrinsicDimension);

            for (int i = 0; i < TKManifoldMath.IntrinsicDimension; i++)
            {
                Vector2Int f = TKPersonalizedParameters.SliceFrequency(i);
                float angle = f.x * u + f.y * v
                            + TKPersonalizedParameters.Phase(i)
                            + TKPersonalizedParameters.AngularSpeed(i) * time;

                p += Mathf.Cos(angle) * TKPersonalizedParameters.CosineBasis(i)
                   + Mathf.Sin(angle) * TKPersonalizedParameters.SineBasis(i);
            }

            return normalization * p;
        }

        [ContextMenu("Rebuild Projected Slice")]
        public void RebuildNow() => Rebuild(true);

        private void Rebuild(bool forceTopology)
        {
            EnsureMesh();
            bool topologyChanged = forceTopology || builtUSegments != uSegments || builtVSegments != vSegments;
            if (topologyChanged) BuildTopology();
            UpdateVertices(Application.isPlaying ? Time.time * animationRate : 0f);
        }

        private void EnsureMesh()
        {
            if (generatedMesh != null) return;
            generatedMesh = new Mesh { name = "TK Projected 7-Torus Slice" };
            generatedMesh.MarkDynamic();
            GetComponent<MeshFilter>().sharedMesh = generatedMesh;
        }

        private void BuildTopology()
        {
            int width = uSegments + 1;
            int height = vSegments + 1;
            int vertexCount = width * height;
            int indexCount = uSegments * vSegments * 6;

            vertices = new Vector3[vertexCount];
            uv = new Vector2[vertexCount];
            triangles = new int[indexCount];

            for (int y = 0; y < height; y++)
            {
                float vv = (float)y / vSegments;
                for (int x = 0; x < width; x++)
                {
                    float uu = (float)x / uSegments;
                    uv[y * width + x] = new Vector2(uu, vv);
                }
            }

            int k = 0;
            for (int y = 0; y < vSegments; y++)
            {
                for (int x = 0; x < uSegments; x++)
                {
                    int a = y * width + x;
                    int b = a + 1;
                    int c = a + width;
                    int d = c + 1;
                    triangles[k++] = a; triangles[k++] = c; triangles[k++] = b;
                    triangles[k++] = b; triangles[k++] = c; triangles[k++] = d;
                }
            }

            generatedMesh.Clear();
            generatedMesh.indexFormat = vertexCount > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16;
            generatedMesh.vertices = vertices;
            generatedMesh.uv = uv;
            generatedMesh.triangles = triangles;
            builtUSegments = uSegments;
            builtVSegments = vSegments;
        }

        private void UpdateVertices(float time)
        {
            if (generatedMesh == null || vertices == null) return;
            int width = uSegments + 1;
            int height = vSegments + 1;

            for (int y = 0; y < height; y++)
            {
                float v = 2f * Mathf.PI * y / vSegments;
                for (int x = 0; x < width; x++)
                {
                    float u = 2f * Mathf.PI * x / uSegments;
                    vertices[y * width + x] = Evaluate(u, v, time);
                }
            }

            generatedMesh.vertices = vertices;
            generatedMesh.RecalculateNormals();
            generatedMesh.RecalculateBounds();
        }
    }
}
