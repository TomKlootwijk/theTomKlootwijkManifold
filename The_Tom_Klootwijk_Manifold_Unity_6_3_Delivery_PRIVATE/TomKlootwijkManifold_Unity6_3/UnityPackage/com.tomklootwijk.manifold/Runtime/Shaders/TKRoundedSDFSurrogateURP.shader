Shader "Tom Klootwijk/Rounded SDF Surrogate URP"
{
    Properties
    {
        [MainColor] _BaseColor("Base Color", Color) = (0.16, 0.56, 0.92, 1)
        _EmissionColor("Emission", Color) = (0.02, 0.09, 0.18, 1)
        _HalfLength("Capsule Half Length", Range(0.02, 0.48)) = 0.36
        _Radius("Capsule Radius", Range(0.005, 0.2)) = 0.055
        _SmoothUnion("Smooth Union", Range(0, 0.15)) = 0.035
        _MaxSteps("Maximum March Steps", Range(8, 128)) = 72
        _HitEpsilon("Hit Epsilon", Range(0.0001, 0.01)) = 0.0015
        _StepScale("Step Scale", Range(0.25, 1)) = 0.8
    }

    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent" }

        Pass
        {
            Name "Forward"
            Tags { "LightMode"="UniversalForward" }
            Cull Back
            ZWrite Off
            Blend SrcAlpha OneMinusSrcAlpha

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
            };

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
                half4 _EmissionColor;
                float _HalfLength;
                float _Radius;
                float _SmoothUnion;
                float _MaxSteps;
                float _HitEpsilon;
                float _StepScale;
            CBUFFER_END

            float4 _TKDirections[7];

            Varyings Vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs p = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = p.positionCS;
                output.positionWS = p.positionWS;
                return output;
            }

            float SdCapsule(float3 p, float3 a, float3 b, float radius)
            {
                float3 pa = p - a;
                float3 ba = b - a;
                float h = saturate(dot(pa, ba) / max(dot(ba, ba), 1e-8));
                return length(pa - ba * h) - radius;
            }

            float SmoothMin(float a, float b, float k)
            {
                if (k <= 1e-6) return min(a, b);
                float h = saturate(0.5 + 0.5 * (b - a) / k);
                return lerp(b, a, h) - k * h * (1.0 - h);
            }

            float Map(float3 p)
            {
                float d = 1e6;
                [unroll]
                for (int i = 0; i < 7; i++)
                {
                    float3 direction = normalize(_TKDirections[i].xyz + float3(1e-8, 0, 0));
                    float3 a = -direction * _HalfLength;
                    float3 b = direction * _HalfLength;
                    d = SmoothMin(d, SdCapsule(p, a, b, _Radius), _SmoothUnion);
                }
                return d;
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
                float e = max(_HitEpsilon * 1.5, 0.0005);
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
                for (int stepIndex = 0; stepIndex < 128; stepIndex++)
                {
                    if (stepIndex >= (int)_MaxSteps || t > tExit) break;
                    p = ro + rd * t;
                    float distanceEstimate = Map(p);
                    if (distanceEstimate < _HitEpsilon)
                    {
                        hit = true;
                        break;
                    }
                    t += max(distanceEstimate * _StepScale, _HitEpsilon * 0.5);
                }

                if (!hit) discard;
                float3 n = Normal(p);
                float3 l = normalize(float3(0.41, 0.77, 0.49));
                float diffuse = 0.18 + 0.82 * saturate(dot(n, l));
                float fresnel = pow(1.0 - saturate(dot(n, -rd)), 3.0);
                half3 color = _BaseColor.rgb * diffuse + _EmissionColor.rgb * (0.35 + fresnel);
                return half4(color, 0.94h);
            }
            ENDHLSL
        }
    }
}
