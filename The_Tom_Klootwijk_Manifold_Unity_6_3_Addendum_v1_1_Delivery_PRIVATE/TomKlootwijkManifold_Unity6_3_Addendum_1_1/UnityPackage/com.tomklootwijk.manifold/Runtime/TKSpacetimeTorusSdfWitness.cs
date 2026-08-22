using UnityEngine;

namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// Drives the exact 3D torus SDF witness shader.
    ///
    /// The shader renders d(p,t) = length(float2(length(p.xz)-R(t), p.y)) - a(t),
    /// an exact signed distance to a ring torus in object space when 0 < a(t) < R(t).
    /// It is a dimension-reduced witness slice, not the complete T^7 x S^6 shell.
    /// Keep the host cube uniformly scaled so object-space sphere tracing remains valid.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Renderer))]
    public sealed class TKSpacetimeTorusSdfWitness : MonoBehaviour
    {
        [Header("Regular torus geometry")]
        [SerializeField, Range(0.08f, 0.40f)] private float majorRadius = 0.275f;
        [SerializeField, Range(0.01f, 0.18f)] private float minorRadius = 0.082f;
        [SerializeField, Range(0f, 0.08f)] private float majorAmplitude = 0.026f;
        [SerializeField, Range(0f, 0.04f)] private float minorAmplitude = 0.012f;
        [SerializeField] private float majorAngularSpeed = 0.43f;
        [SerializeField] private float minorAngularSpeed = -0.31f;
        [SerializeField] private float phaseOffset = 0.72f;

        [Header("Raymarching")]
        [SerializeField, Range(8, 160)] private int maxSteps = 96;
        [SerializeField, Min(0.00001f)] private float hitEpsilon = 0.0012f;
        [SerializeField, Range(0.25f, 1f)] private float stepScale = 0.92f;

        [Header("Appearance")]
        [SerializeField] private Color baseColor = new Color(0.17f, 0.60f, 0.93f, 1f);
        [SerializeField] private Color secondaryColor = new Color(0.76f, 0.25f, 0.88f, 1f);
        [SerializeField] private Color emissionColor = new Color(0.015f, 0.08f, 0.16f, 1f);
        [SerializeField] private bool animate = true;
        [SerializeField] private float animationRate = 1f;

        private static readonly int MajorRadiusId = Shader.PropertyToID("_MajorRadius");
        private static readonly int MinorRadiusId = Shader.PropertyToID("_MinorRadius");
        private static readonly int MaxStepsId = Shader.PropertyToID("_MaxSteps");
        private static readonly int HitEpsilonId = Shader.PropertyToID("_HitEpsilon");
        private static readonly int StepScaleId = Shader.PropertyToID("_StepScale");
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        private static readonly int SecondaryColorId = Shader.PropertyToID("_SecondaryColor");
        private static readonly int EmissionColorId = Shader.PropertyToID("_EmissionColor");
        private static readonly int PhaseId = Shader.PropertyToID("_TKPhase");

        private MaterialPropertyBlock block;
        private Renderer targetRenderer;

        private void OnEnable() => Apply(0f);
        private void OnValidate()
        {
            majorRadius = Mathf.Clamp(majorRadius, 0.08f, 0.40f);
            minorRadius = Mathf.Clamp(minorRadius, 0.01f, 0.18f);
            majorAmplitude = Mathf.Max(0f, majorAmplitude);
            minorAmplitude = Mathf.Max(0f, minorAmplitude);
            hitEpsilon = Mathf.Max(0.00001f, hitEpsilon);
            EnforceRegularity();
            Apply(0f);
        }

        private void LateUpdate()
        {
            float time = animate && Application.isPlaying ? Time.time * animationRate : 0f;
            Apply(time);
        }

        private void EnforceRegularity()
        {
            // Strong guard across all times: 0 < a(t) < R(t), and the whole torus fits in the cube.
            float minimumMinor = Mathf.Max(0.005f, minorRadius - minorAmplitude);
            if (minimumMinor <= 0f) minorAmplitude = Mathf.Max(0f, minorRadius - 0.005f);

            float minimumMajor = majorRadius - majorAmplitude;
            float maximumMinor = minorRadius + minorAmplitude;
            if (minimumMajor <= maximumMinor + 0.01f)
                majorAmplitude = Mathf.Max(0f, majorRadius - maximumMinor - 0.01f);

            float maximumExtent = majorRadius + majorAmplitude + maximumMinor;
            if (maximumExtent > 0.47f)
                majorRadius = Mathf.Max(0.08f, majorRadius - (maximumExtent - 0.47f));
        }

        private void Apply(float time)
        {
            if (targetRenderer == null) targetRenderer = GetComponent<Renderer>();
            if (targetRenderer == null) return;
            if (block == null) block = new MaterialPropertyBlock();

            EnforceRegularity();
            float currentMajor = majorRadius + majorAmplitude * Mathf.Sin(majorAngularSpeed * time + phaseOffset);
            float currentMinor = minorRadius + minorAmplitude * Mathf.Sin(minorAngularSpeed * time - phaseOffset);
            currentMinor = Mathf.Max(0.005f, currentMinor);
            currentMajor = Mathf.Max(currentMinor + 0.01f, currentMajor);

            targetRenderer.GetPropertyBlock(block);
            block.SetFloat(MajorRadiusId, currentMajor);
            block.SetFloat(MinorRadiusId, currentMinor);
            block.SetFloat(MaxStepsId, maxSteps);
            block.SetFloat(HitEpsilonId, hitEpsilon);
            block.SetFloat(StepScaleId, stepScale);
            block.SetColor(BaseColorId, baseColor);
            block.SetColor(SecondaryColorId, secondaryColor);
            block.SetColor(EmissionColorId, emissionColor);
            block.SetFloat(PhaseId, time);
            targetRenderer.SetPropertyBlock(block);
        }
    }
}
