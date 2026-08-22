Shader "Tom Klootwijk/Spatiotemporal Torus SDF Witness URP"
{
    Properties
    {
        _MajorRadius("Major Radius", Range(0.08, 0.40)) = 0.275
        _MinorRadius("Minor Radius", Range(0.01, 0.18)) = 0.082
        _MaxSteps("Maximum March Steps", Range(8, 160)) = 96
        _HitEpsilon("Hit Epsilon", Float) = 0.0012
        _StepScale("Step Scale", Range(0.25, 1.0)) = 0.92
        _BaseColor("Base Color", Color) = (0.17, 0.60, 0.93, 1)
        _SecondaryColor("Secondary Color", Color) = (0.76, 0.25, 0.88, 1)
        _EmissionColor("Emission Color", Color) = (0.015, 0.08, 0.16, 1)
        _TKPhase("Temporal Phase", Float) = 0
    }

    SubShader
    {
        Tags
        {
            "RenderType"="Transparent"
            "Queue"="Transparent"
            "RenderPipeline"="UniversalPipeline"
        }

        Pass
        {
            Name "Forward"
            Tags { "LightMode"="UniversalForward" }
            Cull Front
            ZWrite On
            Blend SrcAlpha OneMinusSrcAlpha

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
            };

            CBUFFER_START(UnityPerMaterial)
                float _MajorRadius;
                float _MinorRadius;
                float _MaxSteps;
                float _HitEpsilon;
                float _StepScale;
                half4 _BaseColor;
                half4 _SecondaryColor;
                half4 _EmissionColor;
                float _TKPhase;
            CBUFFER_END

            Varyings Vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs positions = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = positions.positionCS;
                output.positionWS = positions.positionWS;
                return output;
            }

            // Exact object-space signed distance to a regular ring torus.
            float Map(float3 p)
            {
                float2 q = float2(length(p.xz) - _MajorRadius, p.y);
                return length(q) - _MinorRadius;
            }

            bool RayBox(float3 ro, float3 rd, out float tEnter, out float tExit)
            {
                float3 safeSign = sign(rd + float3(1e-7, 1e-7, 1e-7));
                float3 inv = safeSign / max(abs(rd), float3(1e-6, 1e-6, 1e-6));
                float3 t0 = (-0.5 - ro) * inv;
                float3 t1 = ( 0.5 - ro) * inv;
                float3 lo = min(t0, t1);
                float3 hi = max(t0, t1);
                tEnter = max(max(lo.x, lo.y), lo.z);
                tExit = min(min(hi.x, hi.y), hi.z);
                return tExit >= max(tEnter, 0.0);
            }

            float3 Normal(float3 p)
            {
                float e = max(_HitEpsilon * 1.5, 0.00045);
                float3 ex = float3(e, 0, 0);
                float3 ey = float3(0, e, 0);
                float3 ez = float3(0, 0, e);
                return normalize(float3(
                    Map(p + ex) - Map(p - ex),
                    Map(p + ey) - Map(p - ey),
                    Map(p + ez) - Map(p - ez)));
            }

            half4 Frag(Varyings input) : SV_Target
            {
                float3 cameraWS = GetCameraPositionWS();
                float3 rdWS = normalize(input.positionWS - cameraWS);
                float3 ro = mul(unity_WorldToObject, float4(cameraWS, 1.0)).xyz;
                float3 rd = normalize(mul((float3x3)unity_WorldToObject, rdWS));

                float tEnter, tExit;
                if (!RayBox(ro, rd, tEnter, tExit)) discard;

                float t = max(tEnter, 0.0);
                float3 p = ro;
                bool hit = false;
                [loop]
                for (int stepIndex = 0; stepIndex < 160; stepIndex++)
                {
                    if (stepIndex >= (int)_MaxSteps || t > tExit) break;
                    p = ro + rd * t;
                    float distanceValue = Map(p);
                    if (abs(distanceValue) < _HitEpsilon)
                    {
                        hit = true;
                        break;
                    }
                    t += max(distanceValue * _StepScale, _HitEpsilon * 0.5);
                }

                if (!hit) discard;
                float3 n = Normal(p);
                float3 l = normalize(float3(0.37, 0.82, 0.43));
                float diffuse = 0.17 + 0.83 * saturate(dot(n, l));
                float fresnel = pow(1.0 - saturate(dot(n, -rd)), 3.0);
                float band = 0.5 + 0.5 * sin(10.0 * atan2(p.z, p.x) + _TKPhase);
                half3 surface = lerp(_BaseColor.rgb, _SecondaryColor.rgb, 0.28 * band);
                half3 color = surface * diffuse + _EmissionColor.rgb * (0.28 + 0.85 * fresnel);
                return half4(color, 0.96h);
            }
            ENDHLSL
        }
    }
}
