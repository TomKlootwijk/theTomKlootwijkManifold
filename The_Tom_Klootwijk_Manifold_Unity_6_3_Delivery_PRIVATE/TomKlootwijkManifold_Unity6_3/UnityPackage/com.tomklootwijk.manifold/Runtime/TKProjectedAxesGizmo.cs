using UnityEngine;

namespace TomKlootwijk.Manifold
{
    /// <summary>Draws seven 3D projected directions. These are visual projections, not seven orthogonal 3D axes.</summary>
    [ExecuteAlways]
    public sealed class TKProjectedAxesGizmo : MonoBehaviour
    {
        [SerializeField, Min(0.01f)] private float length = 1f;

        private void OnDrawGizmosSelected()
        {
            Matrix4x4 old = Gizmos.matrix;
            Gizmos.matrix = transform.localToWorldMatrix;
            for (int i = 0; i < TKManifoldMath.IntrinsicDimension; i++)
            {
                Gizmos.color = Color.HSVToRGB(i / 7f, 0.75f, 1f);
                Vector3 d = TKPersonalizedParameters.CosineBasis(i).normalized * length;
                Gizmos.DrawLine(-d, d);
                Gizmos.DrawSphere(d, 0.025f * length);
            }
            Gizmos.matrix = old;
        }
    }
}
