using System;

namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// Exact high-dimensional mathematics for the spatiotemporal tubular SDF addendum.
    ///
    /// At a fixed time, the core is a product of seven circles in R^14. For a point x,
    /// Delta_i(x) is the signed radial offset from circle factor i. The Euclidean norm
    /// of Delta is the exact distance to the product manifold. Subtracting a tube radius
    /// gives a scalar signed-distance function for the boundary of a regular tube.
    ///
    /// Arrays use literal 0-indexed notation. An optional row-major 14x14 orthogonal
    /// matrix Q applies the rigid embedding x = center + Q*y. Pass null for Q = identity.
    /// </summary>
    public static class TKSpacetimeSubstrateMath
    {
        public const int FactorCount = 7;
        public const int AmbientDimension = 14;
        public const int OrthogonalMatrixLength = AmbientDimension * AmbientDimension;

        public const int CoreSpatialDimension = 7;
        public const int CoreWorldvolumeDimension = 8;
        public const int ShellSpatialDimension = 13;
        public const int ShellWorldvolumeDimension = 14;
        public const int NormalSphereDimension = 6;
        public const double DefaultOrthogonalityTolerance = 1e-10;

        public static void EmbedCore(
            double[] theta7,
            double[] radii7,
            double[] destination14)
        {
            EmbedCore(theta7, radii7, null, null, destination14);
        }

        public static void EmbedCore(
            double[] theta7,
            double[] radii7,
            double[] center14,
            double[] orthogonal14x14,
            double[] destination14)
        {
            RequireLength(theta7, FactorCount, nameof(theta7));
            ValidateRadii(radii7);
            ValidateCenter(center14);
            ValidateOptionalOrthogonalMatrix(orthogonal14x14);
            RequireLength(destination14, AmbientDimension, nameof(destination14));

            var local = new double[AmbientDimension];
            for (int i = 0; i < FactorCount; i++)
            {
                int j = 2 * i;
                local[j] = radii7[i] * Math.Cos(theta7[i]);
                local[j + 1] = radii7[i] * Math.Sin(theta7[i]);
            }

            ApplyRigidEmbedding(local, center14, orthogonal14x14, destination14);
        }

        public static void EmbedShell(
            double[] theta7,
            double[] unitNormal7,
            double[] radii7,
            double tubeRadius,
            double[] center14,
            double[] orthogonal14x14,
            double[] destination14)
        {
            RequireLength(theta7, FactorCount, nameof(theta7));
            RequireLength(unitNormal7, FactorCount, nameof(unitNormal7));
            ValidateRegularTube(radii7, tubeRadius);
            ValidateCenter(center14);
            ValidateOptionalOrthogonalMatrix(orthogonal14x14);
            RequireLength(destination14, AmbientDimension, nameof(destination14));

            double normalNorm = Norm(unitNormal7);
            if (Math.Abs(normalNorm - 1.0) > 1e-9)
                throw new ArgumentException("unitNormal7 must have Euclidean norm 1.", nameof(unitNormal7));

            var local = new double[AmbientDimension];
            for (int i = 0; i < FactorCount; i++)
            {
                double factorRadius = radii7[i] + tubeRadius * unitNormal7[i];
                if (!(factorRadius > 0.0))
                    throw new InvalidOperationException("Regular-tube guard failed: a shell factor radius is not positive.");

                int j = 2 * i;
                local[j] = factorRadius * Math.Cos(theta7[i]);
                local[j + 1] = factorRadius * Math.Sin(theta7[i]);
            }

            ApplyRigidEmbedding(local, center14, orthogonal14x14, destination14);
        }

        public static void NormalCoordinates(
            double[] point14,
            double[] radii7,
            double[] destination7)
        {
            NormalCoordinates(point14, radii7, null, null, destination7);
        }

        public static void NormalCoordinates(
            double[] point14,
            double[] radii7,
            double[] center14,
            double[] orthogonal14x14,
            double[] destination7)
        {
            RequireLength(point14, AmbientDimension, nameof(point14));
            ValidateRadii(radii7);
            ValidateCenter(center14);
            ValidateOptionalOrthogonalMatrix(orthogonal14x14);
            RequireLength(destination7, FactorCount, nameof(destination7));

            var local = new double[AmbientDimension];
            ToLocalFrame(point14, center14, orthogonal14x14, local);

            for (int i = 0; i < FactorCount; i++)
            {
                int j = 2 * i;
                destination7[i] = Hypot(local[j], local[j + 1]) - radii7[i];
            }
        }

        public static double CoreDistance(
            double[] point14,
            double[] radii7,
            double[] center14 = null,
            double[] orthogonal14x14 = null)
        {
            var delta = new double[FactorCount];
            NormalCoordinates(point14, radii7, center14, orthogonal14x14, delta);
            return Norm(delta);
        }

        public static double TubularSdf(
            double[] point14,
            double[] radii7,
            double tubeRadius,
            double[] center14 = null,
            double[] orthogonal14x14 = null)
        {
            ValidateRegularTube(radii7, tubeRadius);
            return CoreDistance(point14, radii7, center14, orthogonal14x14) - tubeRadius;
        }

        /// <summary>
        /// Computes the spatial gradient of D_tau = ||Delta||_2 - tau in the regular band.
        /// The result has norm one wherever Delta != 0 and no coordinate pair is at its origin.
        /// On the shell with tubeRadius less than every factor radius, these conditions hold.
        /// </summary>
        public static void SpatialGradient(
            double[] point14,
            double[] radii7,
            double[] center14,
            double[] orthogonal14x14,
            double[] destination14)
        {
            RequireLength(point14, AmbientDimension, nameof(point14));
            ValidateRadii(radii7);
            ValidateCenter(center14);
            ValidateOptionalOrthogonalMatrix(orthogonal14x14);
            RequireLength(destination14, AmbientDimension, nameof(destination14));

            var local = new double[AmbientDimension];
            ToLocalFrame(point14, center14, orthogonal14x14, local);

            var delta = new double[FactorCount];
            double distanceSquared = 0.0;
            for (int i = 0; i < FactorCount; i++)
            {
                int j = 2 * i;
                double rho = Hypot(local[j], local[j + 1]);
                if (!(rho > 0.0))
                    throw new InvalidOperationException("The field gradient is undefined when a coordinate pair is at the origin.");

                delta[i] = rho - radii7[i];
                distanceSquared += delta[i] * delta[i];
            }

            double distance = Math.Sqrt(distanceSquared);
            if (!(distance > 0.0))
                throw new InvalidOperationException("The scalar distance is nondifferentiable on the core manifold Delta = 0.");

            var localGradient = new double[AmbientDimension];
            for (int i = 0; i < FactorCount; i++)
            {
                int j = 2 * i;
                double rho = Hypot(local[j], local[j + 1]);
                double coefficient = delta[i] / distance;
                localGradient[j] = coefficient * local[j] / rho;
                localGradient[j + 1] = coefficient * local[j + 1] / rho;
            }

            FromLocalVector(localGradient, orthogonal14x14, destination14);
        }

        /// <summary>
        /// Partial derivative dD/dt at a fixed ambient point for the implemented identity-frame
        /// motion model: time-varying center, radii, and tube radius, with Q(t) = identity.
        /// On D=0, the outward normal velocity is V_n = -dD/dt because ||grad_x D|| = 1.
        /// </summary>
        public static double TemporalDerivativeIdentityFrame(
            double[] point14,
            double[] center14,
            double[] centerVelocity14,
            double[] radii7,
            double[] radiiVelocity7,
            double tubeRadiusVelocity)
        {
            RequireLength(point14, AmbientDimension, nameof(point14));
            RequireLength(center14, AmbientDimension, nameof(center14));
            RequireLength(centerVelocity14, AmbientDimension, nameof(centerVelocity14));
            ValidateRadii(radii7);
            RequireLength(radiiVelocity7, FactorCount, nameof(radiiVelocity7));

            var delta = new double[FactorCount];
            var deltaVelocity = new double[FactorCount];
            double distanceSquared = 0.0;

            for (int i = 0; i < FactorCount; i++)
            {
                int j = 2 * i;
                double px = point14[j] - center14[j];
                double py = point14[j + 1] - center14[j + 1];
                double rho = Hypot(px, py);
                if (!(rho > 0.0))
                    throw new InvalidOperationException("Temporal derivative is undefined when a coordinate pair is at the moving center.");

                delta[i] = rho - radii7[i];
                double radialCenterVelocity = (px * centerVelocity14[j] + py * centerVelocity14[j + 1]) / rho;
                deltaVelocity[i] = -radialCenterVelocity - radiiVelocity7[i];
                distanceSquared += delta[i] * delta[i];
            }

            double distance = Math.Sqrt(distanceSquared);
            if (!(distance > 0.0))
                throw new InvalidOperationException("Temporal derivative of the scalar norm is undefined on the core manifold.");

            double result = -tubeRadiusVelocity;
            for (int i = 0; i < FactorCount; i++)
                result += (delta[i] / distance) * deltaVelocity[i];
            return result;
        }

        public static double NormalVelocityFromTemporalDerivative(double temporalDerivative)
        {
            if (double.IsNaN(temporalDerivative) || double.IsInfinity(temporalDerivative))
                throw new ArgumentOutOfRangeException(nameof(temporalDerivative));
            return -temporalDerivative;
        }

        public static void ValidateRegularTube(double[] radii7, double tubeRadius)
        {
            ValidateRadii(radii7);
            if (double.IsNaN(tubeRadius) || double.IsInfinity(tubeRadius) || !(tubeRadius > 0.0))
                throw new ArgumentOutOfRangeException(nameof(tubeRadius), "Tube radius must be finite and strictly positive.");

            double minimum = radii7[0];
            for (int i = 1; i < FactorCount; i++) minimum = Math.Min(minimum, radii7[i]);
            if (!(tubeRadius < minimum))
                throw new ArgumentOutOfRangeException(nameof(tubeRadius), "Regular tube requires tubeRadius < min(radii7).");
        }

        public static void ValidateRadii(double[] radii7)
        {
            RequireLength(radii7, FactorCount, nameof(radii7));
            for (int i = 0; i < radii7.Length; i++)
            {
                double radius = radii7[i];
                if (double.IsNaN(radius) || double.IsInfinity(radius) || !(radius > 0.0))
                    throw new ArgumentOutOfRangeException(nameof(radii7), "Every radius must be finite and strictly positive.");
            }
        }

        public static double OrthogonalityError(double[] orthogonal14x14)
        {
            RequireLength(orthogonal14x14, OrthogonalMatrixLength, nameof(orthogonal14x14));
            double maximum = 0.0;
            for (int columnA = 0; columnA < AmbientDimension; columnA++)
            {
                for (int columnB = 0; columnB < AmbientDimension; columnB++)
                {
                    double dot = 0.0;
                    for (int row = 0; row < AmbientDimension; row++)
                        dot += orthogonal14x14[row * AmbientDimension + columnA]
                             * orthogonal14x14[row * AmbientDimension + columnB];
                    double target = columnA == columnB ? 1.0 : 0.0;
                    maximum = Math.Max(maximum, Math.Abs(dot - target));
                }
            }
            return maximum;
        }

        public static double Norm(double[] values)
        {
            if (values == null) throw new ArgumentNullException(nameof(values));
            double sum = 0.0;
            for (int i = 0; i < values.Length; i++) sum += values[i] * values[i];
            return Math.Sqrt(sum);
        }

        public static double Dot(double[] a, double[] b)
        {
            if (a == null) throw new ArgumentNullException(nameof(a));
            if (b == null) throw new ArgumentNullException(nameof(b));
            if (a.Length != b.Length) throw new ArgumentException("Vector lengths must match.");
            double sum = 0.0;
            for (int i = 0; i < a.Length; i++) sum += a[i] * b[i];
            return sum;
        }

        private static void ApplyRigidEmbedding(
            double[] local14,
            double[] center14,
            double[] orthogonal14x14,
            double[] destination14)
        {
            if (orthogonal14x14 == null)
            {
                for (int i = 0; i < AmbientDimension; i++)
                    destination14[i] = local14[i] + (center14 == null ? 0.0 : center14[i]);
                return;
            }

            for (int row = 0; row < AmbientDimension; row++)
            {
                double value = center14 == null ? 0.0 : center14[row];
                for (int column = 0; column < AmbientDimension; column++)
                    value += orthogonal14x14[row * AmbientDimension + column] * local14[column];
                destination14[row] = value;
            }
        }

        private static void ToLocalFrame(
            double[] point14,
            double[] center14,
            double[] orthogonal14x14,
            double[] destination14)
        {
            if (orthogonal14x14 == null)
            {
                for (int i = 0; i < AmbientDimension; i++)
                    destination14[i] = point14[i] - (center14 == null ? 0.0 : center14[i]);
                return;
            }

            // y = Q^T (x - center)
            for (int column = 0; column < AmbientDimension; column++)
            {
                double value = 0.0;
                for (int row = 0; row < AmbientDimension; row++)
                {
                    double centered = point14[row] - (center14 == null ? 0.0 : center14[row]);
                    value += orthogonal14x14[row * AmbientDimension + column] * centered;
                }
                destination14[column] = value;
            }
        }

        private static void FromLocalVector(
            double[] local14,
            double[] orthogonal14x14,
            double[] destination14)
        {
            if (orthogonal14x14 == null)
            {
                Array.Copy(local14, destination14, AmbientDimension);
                return;
            }

            // grad_x = Q grad_y
            for (int row = 0; row < AmbientDimension; row++)
            {
                double value = 0.0;
                for (int column = 0; column < AmbientDimension; column++)
                    value += orthogonal14x14[row * AmbientDimension + column] * local14[column];
                destination14[row] = value;
            }
        }

        private static double Hypot(double x, double y)
        {
            // Stable enough for ordinary geometry values and available on all Unity profiles.
            return Math.Sqrt(x * x + y * y);
        }

        private static void ValidateCenter(double[] center14)
        {
            if (center14 != null) RequireLength(center14, AmbientDimension, nameof(center14));
        }

        public static void ValidateOrthogonalMatrix(
            double[] orthogonal14x14,
            double tolerance = DefaultOrthogonalityTolerance)
        {
            RequireLength(orthogonal14x14, OrthogonalMatrixLength, nameof(orthogonal14x14));
            if (double.IsNaN(tolerance) || double.IsInfinity(tolerance) || !(tolerance > 0.0))
                throw new ArgumentOutOfRangeException(nameof(tolerance));

            for (int i = 0; i < orthogonal14x14.Length; i++)
            {
                double value = orthogonal14x14[i];
                if (double.IsNaN(value) || double.IsInfinity(value))
                    throw new ArgumentOutOfRangeException(nameof(orthogonal14x14),
                        "Every transform entry must be finite.");
            }

            double error = OrthogonalityError(orthogonal14x14);
            if (error > tolerance)
                throw new ArgumentException(
                    "The supplied 14x14 transform is not orthogonal within tolerance. Error: " + error,
                    nameof(orthogonal14x14));
        }

        private static void ValidateOptionalOrthogonalMatrix(double[] orthogonal14x14)
        {
            if (orthogonal14x14 != null)
                ValidateOrthogonalMatrix(orthogonal14x14);
        }

        private static void RequireLength(Array value, int required, string name)
        {
            if (value == null) throw new ArgumentNullException(name);
            if (value.Length != required)
                throw new ArgumentException(name + " must have length " + required + ".", name);
        }
    }
}
