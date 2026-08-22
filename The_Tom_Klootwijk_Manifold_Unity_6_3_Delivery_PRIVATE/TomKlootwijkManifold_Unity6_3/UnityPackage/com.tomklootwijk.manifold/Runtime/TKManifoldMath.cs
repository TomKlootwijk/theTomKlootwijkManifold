using System;
using UnityEngine;

namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// Exact mathematics for K_TK(r) = Product_{i=0}^6 S^1(r_i) embedded in R^14.
    /// Arrays use literal 0-indexed implementation notation.
    /// </summary>
    public static class TKManifoldMath
    {
        public const int IntrinsicDimension = 7;
        public const int AmbientDimension = 14;

        public static void Embed(float[] theta, float[] radii, float[] phase, float[] destination14)
        {
            RequireLength(theta, IntrinsicDimension, nameof(theta));
            RequireLength(radii, IntrinsicDimension, nameof(radii));
            RequireLength(phase, IntrinsicDimension, nameof(phase));
            RequireLength(destination14, AmbientDimension, nameof(destination14));
            ValidateRadii(radii);

            for (int i = 0; i < IntrinsicDimension; i++)
            {
                float a = theta[i] + phase[i];
                int j = 2 * i;
                destination14[j] = radii[i] * Mathf.Cos(a);
                destination14[j + 1] = radii[i] * Mathf.Sin(a);
            }
        }

        public static void ConstraintResiduals(float[] point14, float[] radii, float[] destination7)
        {
            RequireLength(point14, AmbientDimension, nameof(point14));
            RequireLength(radii, IntrinsicDimension, nameof(radii));
            RequireLength(destination7, IntrinsicDimension, nameof(destination7));
            ValidateRadii(radii);

            for (int i = 0; i < IntrinsicDimension; i++)
            {
                int j = 2 * i;
                destination7[i] = point14[j] * point14[j]
                                + point14[j + 1] * point14[j + 1]
                                - radii[i] * radii[i];
            }
        }

        public static void Tangent(int axis, float[] theta, float[] radii, float[] phase, float[] destination14)
        {
            if (axis < 0 || axis >= IntrinsicDimension)
                throw new ArgumentOutOfRangeException(nameof(axis));

            RequireLength(theta, IntrinsicDimension, nameof(theta));
            RequireLength(radii, IntrinsicDimension, nameof(radii));
            RequireLength(phase, IntrinsicDimension, nameof(phase));
            RequireLength(destination14, AmbientDimension, nameof(destination14));
            ValidateRadii(radii);

            Array.Clear(destination14, 0, destination14.Length);
            float a = theta[axis] + phase[axis];
            int j = 2 * axis;
            destination14[j] = -radii[axis] * Mathf.Sin(a);
            destination14[j + 1] = radii[axis] * Mathf.Cos(a);
        }

        public static float Dot(float[] a, float[] b)
        {
            if (a == null) throw new ArgumentNullException(nameof(a));
            if (b == null) throw new ArgumentNullException(nameof(b));
            if (a.Length != b.Length) throw new ArgumentException("Vector lengths must match.");

            float sum = 0f;
            for (int i = 0; i < a.Length; i++) sum += a[i] * b[i];
            return sum;
        }

        public static float MaxAbs(float[] values)
        {
            if (values == null) throw new ArgumentNullException(nameof(values));
            float result = 0f;
            for (int i = 0; i < values.Length; i++) result = Mathf.Max(result, Mathf.Abs(values[i]));
            return result;
        }

        public static float[] UnitRadii()
        {
            var result = new float[IntrinsicDimension];
            for (int i = 0; i < result.Length; i++) result[i] = 1f;
            return result;
        }

        public static void ValidateRadii(float[] radii)
        {
            RequireLength(radii, IntrinsicDimension, nameof(radii));
            for (int i = 0; i < radii.Length; i++)
            {
                float r = radii[i];
                if (float.IsNaN(r) || float.IsInfinity(r) || r <= 0f)
                    throw new ArgumentOutOfRangeException(nameof(radii), "Every radius must be finite and strictly positive.");
            }
        }

        private static void RequireLength(Array value, int required, string name)
        {
            if (value == null) throw new ArgumentNullException(name);
            if (value.Length != required)
                throw new ArgumentException(name + " must have length " + required + ".", name);
        }
    }
}
