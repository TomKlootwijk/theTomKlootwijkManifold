using NUnit.Framework;
using UnityEngine;

namespace TomKlootwijk.Manifold.Tests
{
    public sealed class TKManifoldTests
    {
        [Test]
        public void EmbeddedPointSatisfiesSevenCircleConstraints()
        {
            float[] theta = { 0.1f, 0.7f, 1.2f, 2.0f, 2.7f, 4.1f, 5.3f };
            float[] radii = { 1f, 1.1f, 0.9f, 1.2f, 0.8f, 1.3f, 0.95f };
            float[] phase = new float[7];
            float[] point = new float[14];
            float[] residuals = new float[7];
            TKPersonalizedParameters.CopyPhases(phase);

            TKManifoldMath.Embed(theta, radii, phase, point);
            TKManifoldMath.ConstraintResiduals(point, radii, residuals);

            Assert.That(TKManifoldMath.MaxAbs(residuals), Is.LessThan(2e-5f));
        }

        [Test]
        public void CoordinateTangentsArePairwiseOrthogonal()
        {
            float[] theta = { 0.1f, 0.7f, 1.2f, 2.0f, 2.7f, 4.1f, 5.3f };
            float[] radii = { 1f, 1.1f, 0.9f, 1.2f, 0.8f, 1.3f, 0.95f };
            float[] phase = new float[7];
            TKPersonalizedParameters.CopyPhases(phase);

            var a = new float[14];
            var b = new float[14];
            for (int i = 0; i < 7; i++)
            {
                TKManifoldMath.Tangent(i, theta, radii, phase, a);
                Assert.That(TKManifoldMath.Dot(a, a), Is.EqualTo(radii[i] * radii[i]).Within(2e-5f));
                for (int j = i + 1; j < 7; j++)
                {
                    TKManifoldMath.Tangent(j, theta, radii, phase, b);
                    Assert.That(Mathf.Abs(TKManifoldMath.Dot(a, b)), Is.LessThan(2e-5f));
                }
            }
        }

        [Test]
        public void SourceTransition943To937HasBinaryHammingDistanceTwo()
        {
            int x = 943 ^ 937;
            int count = 0;
            while (x != 0) { count += x & 1; x >>= 1; }
            Assert.That(count, Is.EqualTo(2));
        }

        [Test]
        public void PersonalizedProjectionPairsAreOrthonormalWithinEachPlane()
        {
            for (int i = 0; i < 7; i++)
            {
                Vector3 u = TKPersonalizedParameters.CosineBasis(i);
                Vector3 v = TKPersonalizedParameters.SineBasis(i);
                Assert.That(u.magnitude, Is.EqualTo(1f).Within(2e-5f));
                Assert.That(v.magnitude, Is.EqualTo(1f).Within(2e-5f));
                Assert.That(Mathf.Abs(Vector3.Dot(u, v)), Is.LessThan(2e-5f));
            }
        }
    }
}
