using System.IO;
using UnityEditor;
using UnityEngine;

namespace TomKlootwijk.Manifold.Editor
{
    public static class TKManifoldMenu
    {
        private const string GeneratedFolder = "Assets/TomKlootwijkManifoldGenerated";

        [MenuItem("GameObject/Tom Klootwijk Manifold/Create Projected 7-Torus Slice", false, 10)]
        private static void CreateProjectedSlice(MenuCommand command)
        {
            var go = new GameObject("TK Manifold - Projected 7-Torus Slice");
            Undo.RegisterCreatedObjectUndo(go, "Create TK projected slice");
            GameObjectUtility.SetParentAndAlign(go, command.context as GameObject);
            go.AddComponent<MeshFilter>();
            var renderer = go.AddComponent<MeshRenderer>();
            go.AddComponent<TKProjectedSlice>();
            go.AddComponent<TKProjectedAxesGizmo>();
            renderer.sharedMaterial = CreateMaterial(
                "Tom Klootwijk/Projected 7-Torus Slice URP",
                "TKProjectedSliceMaterial.mat");
            Selection.activeObject = go;
        }

        [MenuItem("GameObject/Tom Klootwijk Manifold/Create Rounded SDF Surrogate", false, 11)]
        private static void CreateRoundedSdf(MenuCommand command)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "TK Manifold - Rounded SDF Surrogate";
            Undo.RegisterCreatedObjectUndo(go, "Create TK rounded SDF surrogate");
            GameObjectUtility.SetParentAndAlign(go, command.context as GameObject);
            go.transform.localScale = Vector3.one * 3f;
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = CreateMaterial(
                "Tom Klootwijk/Rounded SDF Surrogate URP",
                "TKRoundedSDFMaterial.mat");
            go.AddComponent<TKManifoldVolume>();
            Selection.activeObject = go;
        }

        [MenuItem("GameObject/Tom Klootwijk Manifold/Create Spatiotemporal Torus SDF Witness", false, 12)]
        private static void CreateSpatiotemporalTorusSdfWitness(MenuCommand command)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "TK Manifold - Spatiotemporal Torus SDF Witness";
            Undo.RegisterCreatedObjectUndo(go, "Create TK spatiotemporal torus SDF witness");
            GameObjectUtility.SetParentAndAlign(go, command.context as GameObject);
            go.transform.localScale = Vector3.one * 3f;
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = CreateMaterial(
                "Tom Klootwijk/Spatiotemporal Torus SDF Witness URP",
                "TKSpatiotemporalTorusSDFWitness.mat");
            go.AddComponent<TKSpacetimeTorusSdfWitness>();
            Selection.activeObject = go;
        }

        private static Material CreateMaterial(string shaderName, string fileName)
        {
            Shader shader = Shader.Find(shaderName);
            if (shader == null)
                throw new System.InvalidOperationException("Required shader not found: " + shaderName);

            Directory.CreateDirectory(GeneratedFolder);
            AssetDatabase.Refresh();
            string path = AssetDatabase.GenerateUniqueAssetPath(GeneratedFolder + "/" + fileName);
            var material = new Material(shader) { name = Path.GetFileNameWithoutExtension(path) };
            AssetDatabase.CreateAsset(material, path);
            AssetDatabase.SaveAssets();
            return material;
        }
    }
}
