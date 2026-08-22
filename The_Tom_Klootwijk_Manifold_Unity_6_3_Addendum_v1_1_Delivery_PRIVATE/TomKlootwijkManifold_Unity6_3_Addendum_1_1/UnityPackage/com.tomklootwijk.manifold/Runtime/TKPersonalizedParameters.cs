using System;
using UnityEngine;

namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// Deterministic visualization parameters derived once from the public author-record SHA-256.
    /// They personalize the chosen parameterization/projection, not the manifold proof itself.
    /// </summary>
    public static class TKPersonalizedParameters
    {
        private static readonly float[] PhaseValues =
        {
            3.080712791f,
            5.014583196f,
            0.618194258f,
            3.690086659f,
            4.519778518f,
            3.740420404f,
            4.338001794f
        };

        private static readonly Vector3[] CosineBasisValues =
        {
            new Vector3(0.977721287f, -0.164573835f, -0.130294041f),
            new Vector3(0.278812393f, 0.923658752f, 0.262903326f),
            new Vector3(-0.212397100f, -0.044815994f, -0.976155212f),
            new Vector3(-0.269094735f, -0.764294294f, -0.586039466f),
            new Vector3(0.482305945f, 0.304370010f, 0.821425512f),
            new Vector3(0.682692936f, 0.003370374f, 0.730697609f),
            new Vector3(-0.441929117f, -0.211004625f, -0.871880556f)
        };

        private static readonly Vector3[] SineBasisValues =
        {
            new Vector3(0.175672879f, 0.981291599f, 0.078777138f),
            new Vector3(-0.366818982f, 0.355430107f, -0.859716973f),
            new Vector3(-0.554466815f, -0.817039550f, 0.158154750f),
            new Vector3(-0.768861675f, 0.536933284f, -0.347209408f),
            new Vector3(0.757992609f, -0.615051694f, -0.217160350f),
            new Vector3(-0.133297256f, 0.983784171f, 0.120002274f),
            new Vector3(0.518773177f, 0.732810929f, -0.440298232f)
        };

        private static readonly Vector2Int[] SliceFrequencyValues =
        {
            new Vector2Int(1, 0),
            new Vector2Int(0, 1),
            new Vector2Int(1, 1),
            new Vector2Int(1, -1),
            new Vector2Int(2, 1),
            new Vector2Int(1, 2),
            new Vector2Int(2, -1)
        };

        private static readonly float[] AngularSpeedValues =
        {
            0.170000000f,
            -0.130000000f,
            0.110000000f,
            -0.190000000f,
            0.070000000f,
            0.230000000f,
            -0.090000000f
        };

        public static float Phase(int i) => PhaseValues[Checked(i)];
        public static Vector3 CosineBasis(int i) => CosineBasisValues[Checked(i)];
        public static Vector3 SineBasis(int i) => SineBasisValues[Checked(i)];
        public static Vector2Int SliceFrequency(int i) => SliceFrequencyValues[Checked(i)];
        public static float AngularSpeed(int i) => AngularSpeedValues[Checked(i)];

        public static void CopyPhases(float[] destination)
        {
            if (destination == null) throw new ArgumentNullException(nameof(destination));
            if (destination.Length != TKManifoldMath.IntrinsicDimension)
                throw new ArgumentException("Destination must have length 7.", nameof(destination));
            Array.Copy(PhaseValues, destination, PhaseValues.Length);
        }

        private static int Checked(int i)
        {
            if (i < 0 || i >= TKManifoldMath.IntrinsicDimension)
                throw new ArgumentOutOfRangeException(nameof(i));
            return i;
        }
    }
}
