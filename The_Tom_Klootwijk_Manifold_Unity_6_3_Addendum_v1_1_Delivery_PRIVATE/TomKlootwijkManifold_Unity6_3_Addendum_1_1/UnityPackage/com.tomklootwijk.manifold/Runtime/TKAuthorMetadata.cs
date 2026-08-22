namespace TomKlootwijk.Manifold
{
    /// <summary>
    /// Public, non-secret metadata. The national identifier and birth date are deliberately
    /// absent from runtime code; only cryptographic fingerprints of private records appear.
    /// </summary>
    public static class TKAuthorMetadata
    {
        public const string DefinitionName = "The Tom Klootwijk Manifold";
        public const string AddendumName = "Spatiotemporal SDF o(1) Geometrical Topological Substrate";
        public const string AuthorName = "Tom Klootwijk";

        public const string OriginalAuthorRecordSha256 = "7d85cc5019309659b8279866b0bf6dde69ef18373d25dc71051fe8824ee2e3b4";
        public const string AddendumAuthorRecordSha256 = "ee007f23936d94c39d1f96cd1806b2a4f15177a4ba56debb8eb8a23f85027f18";

        public const string OriginalEditionCode = "U6.3-A36";
        public const string AddendumEditionCode = "ST-SDF-o1-U6.3-A36";

        public const string OriginalOccasionLocalIso8601 = "2026-08-22T06:34:39+02:00";
        public const string OriginalOccasionUtcIso8601 = "2026-08-22T04:34:39Z";
        public const string OriginalDocumentId = "TKM-U63-A36-20260822-063439";

        public const string AddendumOccasionLocalIso8601 = "2026-08-22T07:25:11+02:00";
        public const string AddendumOccasionUtcIso8601 = "2026-08-22T05:25:11Z";
        public const string AddendumDocumentId = "TKM-STSDF-U63-A36-20260822-072511";
    }
}
