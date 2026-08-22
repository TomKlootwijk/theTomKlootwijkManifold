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

        [Test]
        public void SpacetimeCoreEmbeddingHasZeroNormalCoordinates()
        {
            double[] theta = { 0.1, 0.7, 1.2, 2.0, 2.7, 4.1, 5.3 };
            double[] radii = { 1.0, 1.1, 0.9, 1.2, 0.8, 1.3, 0.95 };
            double[] point = new double[14];
            double[] delta = new double[7];

            TKSpacetimeSubstrateMath.EmbedCore(theta, radii, point);
            TKSpacetimeSubstrateMath.NormalCoordinates(point, radii, delta);

            Assert.That(TKSpacetimeSubstrateMath.Norm(delta), Is.LessThan(2e-12));
        }

        [Test]
        public void SpacetimeShellEmbeddingHasZeroTubularSdf()
        {
            double[] theta = { 0.1, 0.7, 1.2, 2.0, 2.7, 4.1, 5.3 };
            double[] radii = { 1.0, 1.1, 0.9, 1.2, 0.8, 1.3, 0.95 };
            double[] unitNormal = { 1.0, 2.0, -1.0, 0.5, -0.25, 0.75, -1.5 };
            Normalize(unitNormal);
            double tubeRadius = 0.18;
            double[] point = new double[14];

            TKSpacetimeSubstrateMath.EmbedShell(
                theta, unitNormal, radii, tubeRadius, null, null, point);

            double sdf = TKSpacetimeSubstrateMath.TubularSdf(point, radii, tubeRadius);
            Assert.That(Mathf.Abs((float)sdf), Is.LessThan(2e-10f));
        }

        [Test]
        public void SpacetimeGradientSatisfiesEikonalOnRegularShell()
        {
            double[] theta = { 0.2, 0.8, 1.4, 2.2, 2.9, 4.4, 5.7 };
            double[] radii = { 1.0, 1.1, 0.9, 1.2, 0.8, 1.3, 0.95 };
            double[] unitNormal = { 0.2, -0.5, 0.9, 0.1, -0.35, 0.6, -0.2 };
            Normalize(unitNormal);
            double tubeRadius = 0.17;
            double[] point = new double[14];
            double[] gradient = new double[14];

            TKSpacetimeSubstrateMath.EmbedShell(
                theta, unitNormal, radii, tubeRadius, null, null, point);
            TKSpacetimeSubstrateMath.SpatialGradient(point, radii, null, null, gradient);

            Assert.That(TKSpacetimeSubstrateMath.Norm(gradient), Is.EqualTo(1.0).Within(2e-12));
        }

        [Test]
        public void RegularTubeGuardRejectsRadiusAtReach()
        {
            double[] radii = { 1.0, 1.1, 0.9, 1.2, 0.8, 1.3, 0.95 };
            Assert.Throws<System.ArgumentOutOfRangeException>(
                () => TKSpacetimeSubstrateMath.ValidateRegularTube(radii, 0.8));
        }

        [Test]
        public void FirstOrderTemporalRemainderIsLittleOOfStepForProfile()
        {
            const double t0 = 0.83;
            double[] radii = new double[7];
            double[] radiiVelocity = new double[7];
            double[] center = new double[14];
            double[] centerVelocity = new double[14];
            TKSpacetimeProfile.Evaluate(
                t0, radii, radiiVelocity, center, centerVelocity,
                out double tubeRadius, out double tubeVelocity);

            double[] theta = { 0.3, 0.9, 1.5, 2.1, 2.8, 4.0, 5.4 };
            double[] unitNormal = { 0.7, -0.2, 0.45, -0.6, 0.15, 0.3, -0.25 };
            Normalize(unitNormal);
            double[] point = new double[14];
            TKSpacetimeSubstrateMath.EmbedShell(
                theta, unitNormal, radii, tubeRadius, center, null, point);

            double d0 = TKSpacetimeSubstrateMath.TubularSdf(point, radii, tubeRadius, center);
            double derivative = TKSpacetimeSubstrateMath.TemporalDerivativeIdentityFrame(
                point, center, centerVelocity, radii, radiiVelocity, tubeVelocity);

            double ratio1 = RemainderRatio(point, t0, 1e-2, d0, derivative);
            double ratio2 = RemainderRatio(point, t0, 5e-3, d0, derivative);
            double ratio3 = RemainderRatio(point, t0, 2.5e-3, d0, derivative);

            Assert.That(ratio2, Is.LessThan(ratio1 * 0.65));
            Assert.That(ratio3, Is.LessThan(ratio2 * 0.65));
        }

        [Test]
        public void OrthogonalTransformPreservesTubularSdf()
        {
            double[] radii = { 1.0, 1.1, 0.9, 1.2, 0.8, 1.3, 0.95 };
            double[] local = { 1.2, 0.1, 0.7, -0.8, 0.2, 1.1, -1.0, 0.5, 0.6, -0.4, 1.4, 0.2, -0.3, 0.9 };
            double[] rotation = Identity14();
            double angle = 0.37;
            rotation[0] = System.Math.Cos(angle);
            rotation[1] = -System.Math.Sin(angle);
            rotation[14] = System.Math.Sin(angle);
            rotation[15] = System.Math.Cos(angle);
            double[] world = new double[14];
            for (int row = 0; row < 14; row++)
                for (int column = 0; column < 14; column++)
                    world[row] += rotation[row * 14 + column] * local[column];

            TKSpacetimeSubstrateMath.ValidateOrthogonalMatrix(rotation);
            double localSdf = TKSpacetimeSubstrateMath.TubularSdf(local, radii, 0.18);
            double worldSdf = TKSpacetimeSubstrateMath.TubularSdf(world, radii, 0.18, null, rotation);
            Assert.That(worldSdf, Is.EqualTo(localSdf).Within(2e-12));
        }

        [Test]
        public void NonOrthogonalTransformIsRejected()
        {
            double[] transform = Identity14();
            transform[0] = 2.0;
            Assert.Throws<System.ArgumentException>(
                () => TKSpacetimeSubstrateMath.ValidateOrthogonalMatrix(transform));
        }

        [Test]
        public void AddendumDimensionsAreExplicitAndConsistent()
        {
            Assert.That(TKSpacetimeSubstrateMath.CoreWorldvolumeDimension, Is.EqualTo(8));
            Assert.That(TKSpacetimeSubstrateMath.ShellSpatialDimension, Is.EqualTo(13));
            Assert.That(TKSpacetimeSubstrateMath.ShellWorldvolumeDimension, Is.EqualTo(14));
            Assert.That(TKSpacetimeSubstrateMath.NormalSphereDimension, Is.EqualTo(6));
        }

        private static double RemainderRatio(
            double[] fixedPoint,
            double t0,
            double h,
            double d0,
            double derivative)
        {
            double[] radii = new double[7];
            double[] radiiVelocity = new double[7];
            double[] center = new double[14];
            double[] centerVelocity = new double[14];
            TKSpacetimeProfile.Evaluate(
                t0 + h, radii, radiiVelocity, center, centerVelocity,
                out double tubeRadius, out _);
            double d1 = TKSpacetimeSubstrateMath.TubularSdf(fixedPoint, radii, tubeRadius, center);
            return System.Math.Abs(d1 - d0 - h * derivative) / h;
        }

        private static double[] Identity14()
        {
            double[] result = new double[14 * 14];
            for (int i = 0; i < 14; i++) result[i * 14 + i] = 1.0;
            return result;
        }

        private static void Normalize(double[] values)
        {
            double norm = TKSpacetimeSubstrateMath.Norm(values);
            for (int i = 0; i < values.Length; i++) values[i] /= norm;
        }
    }
}
