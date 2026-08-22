using UnityEngine;

namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// Feeds seven deterministic projected directions to the optional capsule-union SDF shader.
    /// This is a rounded 3D surrogate and is deliberately not labeled as the exact 7D manifold.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Renderer))]
    public sealed class TKManifoldVolume : MonoBehaviour
    {
        [SerializeField, Min(0.001f)] private float halfLength = 0.36f;
        [SerializeField, Min(0.001f)] private float radius = 0.055f;
        [SerializeField, Min(0f)] private float smoothUnion = 0.035f;
        [SerializeField, Range(8, 128)] private int maxSteps = 72;
        [SerializeField, Min(0.00001f)] private float hitEpsilon = 0.0015f;
        [SerializeField, Range(0.25f, 1f)] private float stepScale = 0.8f;
        [SerializeField] private Color baseColor = new Color(0.16f, 0.56f, 0.92f, 1f);
        [SerializeField] private Color emissionColor = new Color(0.02f, 0.09f, 0.18f, 1f);
        [SerializeField] private bool animate = true;
        [SerializeField] private float animationRate = 1f;

        private static readonly int DirectionsId = Shader.PropertyToID("_TKDirections");
        private static readonly int HalfLengthId = Shader.PropertyToID("_HalfLength");
        private static readonly int RadiusId = Shader.PropertyToID("_Radius");
        private static readonly int SmoothUnionId = Shader.PropertyToID("_SmoothUnion");
        private static readonly int MaxStepsId = Shader.PropertyToID("_MaxSteps");
        private static readonly int HitEpsilonId = Shader.PropertyToID("_HitEpsilon");
        private static readonly int StepScaleId = Shader.PropertyToID("_StepScale");
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        private static readonly int EmissionColorId = Shader.PropertyToID("_EmissionColor");

        private readonly Vector4[] directions = new Vector4[TKManifoldMath.IntrinsicDimension];
        private MaterialPropertyBlock block;
        private Renderer targetRenderer;

        private void OnEnable() => Apply(0f);
        private void OnValidate() => Apply(0f);

        private void LateUpdate()
        {
            if (!animate || !Application.isPlaying) return;
            Apply(Time.time * animationRate);
        }

        private void Apply(float time)
        {
            if (targetRenderer == null) targetRenderer = GetComponent<Renderer>();
            if (block == null) block = new MaterialPropertyBlock();
            if (targetRenderer == null) return;

            for (int i = 0; i < directions.Length; i++)
            {
                float angle = TKPersonalizedParameters.Phase(i)
                            + TKPersonalizedParameters.AngularSpeed(i) * time;
                Vector3 d = Mathf.Cos(angle) * TKPersonalizedParameters.CosineBasis(i)
                          + Mathf.Sin(angle) * TKPersonalizedParameters.SineBasis(i);
                d.Normalize();
                directions[i] = new Vector4(d.x, d.y, d.z, 0f);
            }

            targetRenderer.GetPropertyBlock(block);
            block.SetVectorArray(DirectionsId, directions);
            block.SetFloat(HalfLengthId, halfLength);
            block.SetFloat(RadiusId, radius);
            block.SetFloat(SmoothUnionId, smoothUnion);
            block.SetFloat(MaxStepsId, maxSteps);
            block.SetFloat(HitEpsilonId, hitEpsilon);
            block.SetFloat(StepScaleId, stepScale);
            block.SetColor(BaseColorId, baseColor);
            block.SetColor(EmissionColorId, emissionColor);
            targetRenderer.SetPropertyBlock(block);
        }
    }
}
