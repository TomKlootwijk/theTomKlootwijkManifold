using System;

namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// A deterministic smooth C-infinity motion profile used by the tests and examples.
    /// It changes center, seven radii, and tube radius while preserving the regular-tube guard.
    /// No private identifier is stored here.
    /// </summary>
    public static class TKSpacetimeProfile
    {
        private static readonly double[] BaseRadii =
        {
            1.00, 1.07, 0.93, 1.12, 0.88, 1.18, 0.97
        };

        private static readonly double[] RelativeAmplitudes =
        {
            0.045, 0.038, 0.041, 0.032, 0.036, 0.029, 0.043
        };

        private static readonly double[] RadiusSpeeds =
        {
            0.31, -0.27, 0.23, -0.19, 0.17, 0.29, -0.21
        };

        private static readonly double[] RadiusPhases =
        {
            3.080712791, 5.014583196, 0.618194258, 3.690086659,
            4.519778518, 3.740420404, 4.338001794
        };

        private const double BaseTubeRadius = 0.19;
        private const double TubeAmplitude = 0.018;
        private const double TubeSpeed = 0.37;
        private const double TubePhase = 0.43;

        public static void Evaluate(
            double time,
            double[] radii7,
            double[] radiiVelocity7,
            double[] center14,
            double[] centerVelocity14,
            out double tubeRadius,
            out double tubeRadiusVelocity)
        {
            RequireFinite(time, nameof(time));
            RequireLength(radii7, TKSpacetimeSubstrateMath.FactorCount, nameof(radii7));
            RequireLength(radiiVelocity7, TKSpacetimeSubstrateMath.FactorCount, nameof(radiiVelocity7));
            RequireLength(center14, TKSpacetimeSubstrateMath.AmbientDimension, nameof(center14));
            RequireLength(centerVelocity14, TKSpacetimeSubstrateMath.AmbientDimension, nameof(centerVelocity14));

            for (int i = 0; i < TKSpacetimeSubstrateMath.FactorCount; i++)
            {
                double argument = RadiusSpeeds[i] * time + RadiusPhases[i];
                double scale = 1.0 + RelativeAmplitudes[i] * Math.Sin(argument);
                radii7[i] = BaseRadii[i] * scale;
                radiiVelocity7[i] = BaseRadii[i] * RelativeAmplitudes[i]
                                  * RadiusSpeeds[i] * Math.Cos(argument);
            }

            for (int j = 0; j < TKSpacetimeSubstrateMath.AmbientDimension; j++)
            {
                int factor = j / 2;
                double amplitude = 0.018 + 0.002 * (j % 3);
                double speed = 0.11 + 0.013 * (j + 1);
                double phase = RadiusPhases[factor] + 0.37 * (j % 2);
                double argument = speed * time + phase;
                center14[j] = amplitude * Math.Sin(argument);
                centerVelocity14[j] = amplitude * speed * Math.Cos(argument);
            }

            double tubeArgument = TubeSpeed * time + TubePhase;
            tubeRadius = BaseTubeRadius + TubeAmplitude * Math.Sin(tubeArgument);
            tubeRadiusVelocity = TubeAmplitude * TubeSpeed * Math.Cos(tubeArgument);

            TKSpacetimeSubstrateMath.ValidateRegularTube(radii7, tubeRadius);
        }

        public static double ConservativeMinimumFactorRadius()
        {
            double minimum = double.PositiveInfinity;
            for (int i = 0; i < BaseRadii.Length; i++)
                minimum = Math.Min(minimum, BaseRadii[i] * (1.0 - RelativeAmplitudes[i]));
            return minimum;
        }

        public static double MaximumTubeRadius()
        {
            return BaseTubeRadius + Math.Abs(TubeAmplitude);
        }

        private static void RequireFinite(double value, string name)
        {
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new ArgumentOutOfRangeException(name);
        }

        private static void RequireLength(Array value, int required, string name)
        {
            if (value == null) throw new ArgumentNullException(name);
            if (value.Length != required)
                throw new ArgumentException(name + " must have length " + required + ".", name);
        }
    }
}
