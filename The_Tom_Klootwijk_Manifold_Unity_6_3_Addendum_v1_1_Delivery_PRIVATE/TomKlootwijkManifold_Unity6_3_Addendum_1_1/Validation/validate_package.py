#!/usr/bin/env python3
"""Static delivery validation that does not require a Unity installation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "UnityPackage" / "com.tomklootwijk.manifold"
OUT = Path(__file__).with_name("package_validation_report.json")

REQUIRED = [
    "package.json",
    "Runtime/TomKlootwijk.Manifold.Runtime.asmdef",
    "Runtime/TKAuthorMetadata.cs",
    "Runtime/TKManifoldMath.cs",
    "Runtime/TKPersonalizedParameters.cs",
    "Runtime/TKProjectedSlice.cs",
    "Runtime/TKProjectedAxesGizmo.cs",
    "Runtime/TKManifoldVolume.cs",
    "Runtime/TKSpacetimeSubstrateMath.cs",
    "Runtime/TKSpacetimeProfile.cs",
    "Runtime/TKSpacetimeTorusSdfWitness.cs",
    "Runtime/Shaders/TKProjectedSliceURP.shader",
    "Runtime/Shaders/TKRoundedSDFSurrogateURP.shader",
    "Runtime/Shaders/TKSpatiotemporalTorusSDFURP.shader",
    "Editor/TomKlootwijk.Manifold.Editor.asmdef",
    "Editor/TKManifoldMenu.cs",
    "Tests/Runtime/TomKlootwijk.Manifold.Tests.asmdef",
    "Tests/Runtime/TKManifoldTests.cs",
    "Samples~/SpatiotemporalSDF/README.md",
]

SENSITIVE_TOKENS = [
    "NL200678942",
    "200678942",
    "10-07-1990",
    "1990-07-10",
]

ORIGINAL_FINGERPRINT = "7d85cc5019309659b8279866b0bf6dde69ef18373d25dc71051fe8824ee2e3b4"
ADDENDUM_FINGERPRINT = "ee007f23936d94c39d1f96cd1806b2a4f15177a4ba56debb8eb8a23f85027f18"


def strip_comments_and_literals(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    mode = "code"
    quote = ""
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if mode == "code":
            if c == "/" and nxt == "/":
                out.extend("  ")
                i += 2
                mode = "line"
                continue
            if c == "/" and nxt == "*":
                out.extend("  ")
                i += 2
                mode = "block"
                continue
            if c in ('"', "'"):
                quote = c
                out.append(" ")
                i += 1
                mode = "string"
                continue
            out.append(c)
            i += 1
            continue
        if mode == "line":
            if c == "\n":
                out.append("\n")
                mode = "code"
            else:
                out.append(" ")
            i += 1
            continue
        if mode == "block":
            if c == "*" and nxt == "/":
                out.extend("  ")
                i += 2
                mode = "code"
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
            continue
        if mode == "string":
            if c == "\\":
                out.append(" ")
                if i + 1 < n:
                    out.append(" ")
                    i += 2
                else:
                    i += 1
                continue
            if c == quote:
                out.append(" ")
                i += 1
                mode = "code"
                continue
            out.append("\n" if c == "\n" else " ")
            i += 1
    return "".join(out)


def delimiter_check(path: Path) -> dict[str, object]:
    clean = strip_comments_and_literals(path.read_text(encoding="utf-8"))
    pairs = {"{": "}", "(": ")", "[": "]"}
    reverse = {value: key for key, value in pairs.items()}
    stack: list[tuple[str, int]] = []
    line = 1
    for char in clean:
        if char == "\n":
            line += 1
        elif char in pairs:
            stack.append((char, line))
        elif char in reverse:
            if not stack or stack[-1][0] != reverse[char]:
                return {"status": "FAIL", "message": f"unexpected {char} at line {line}"}
            stack.pop()
    if stack:
        char, where = stack[-1]
        return {"status": "FAIL", "message": f"unclosed {char} from line {where}"}
    return {"status": "PASS"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    missing = [relative for relative in REQUIRED if not (PACKAGE / relative).is_file()]

    json_results: dict[str, str] = {}
    json_objects: dict[str, object] = {}
    for path in sorted(PACKAGE.rglob("*.json")) + sorted(PACKAGE.rglob("*.asmdef")):
        relative = path.relative_to(PACKAGE).as_posix()
        try:
            json_objects[relative] = json.loads(path.read_text(encoding="utf-8"))
            json_results[relative] = "PASS"
        except Exception as exc:
            json_results[relative] = f"FAIL: {exc}"

    delimiter_results = {
        path.relative_to(PACKAGE).as_posix(): delimiter_check(path)
        for path in sorted(list(PACKAGE.rglob("*.cs")) + list(PACKAGE.rglob("*.shader")))
    }

    pii_hits: dict[str, list[str]] = {}
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits = [token for token in SENSITIVE_TOKENS if token in text]
        if hits:
            pii_hits[path.relative_to(PACKAGE).as_posix()] = hits

    package_json = json_objects.get("package.json", {})
    manifest_checks = {
        "name": isinstance(package_json, dict)
        and package_json.get("name") == "com.tomklootwijk.manifold",
        "version": isinstance(package_json, dict) and package_json.get("version") == "1.1.0",
        "unity": isinstance(package_json, dict) and package_json.get("unity") == "6000.3",
        "urp_dependency": isinstance(package_json, dict)
        and package_json.get("dependencies", {}).get("com.unity.render-pipelines.universal") == "17.3.0",
        "spatiotemporal_sample": isinstance(package_json, dict)
        and any(sample.get("path") == "Samples~/SpatiotemporalSDF" for sample in package_json.get("samples", [])),
    }

    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((PACKAGE / "Runtime").rglob("*"))
        if path.is_file()
    )
    test_text = (PACKAGE / "Tests/Runtime/TKManifoldTests.cs").read_text(encoding="utf-8")
    readme_text = (PACKAGE / "README.md").read_text(encoding="utf-8")
    shader_text = (PACKAGE / "Runtime/Shaders/TKSpatiotemporalTorusSDFURP.shader").read_text(encoding="utf-8")

    content_checks = {
        "both_fingerprints_embedded": ORIGINAL_FINGERPRINT in runtime_text and ADDENDUM_FINGERPRINT in runtime_text,
        "original_dimensions_present": "IntrinsicDimension = 7" in runtime_text and "AmbientDimension = 14" in runtime_text,
        "addendum_dimensions_present": "ShellWorldvolumeDimension = 14" in runtime_text and "NormalSphereDimension = 6" in runtime_text,
        "normal_coordinate_formula_present": "Hypot(local[j], local[j + 1]) - radii7[i]" in runtime_text,
        "tubular_sdf_present": "CoreDistance(point14, radii7, center14, orthogonal14x14) - tubeRadius" in runtime_text,
        "regular_tube_guard_present": "tubeRadius < min(radii7)" in runtime_text,
        "eikonal_test_present": "SpacetimeGradientSatisfiesEikonalOnRegularShell" in test_text,
        "little_o_test_present": "FirstOrderTemporalRemainderIsLittleOOfStepForProfile" in test_text,
        "little_o_not_complexity_disclaimer": "not a runtime-complexity claim" in readme_text,
        "exact_torus_sdf_shader_formula": "length(p.xz) - _MajorRadius" in shader_text and "length(q) - _MinorRadius" in shader_text,
        "urp_core_include_count": runtime_text.count(
            "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        ) >= 3,
        "source_hamming_test_retained": "HammingDistanceTwo" in test_text,
    }

    all_json_ok = all(value == "PASS" for value in json_results.values())
    all_delimiters_ok = all(value["status"] == "PASS" for value in delimiter_results.values())
    status = "PASS" if (
        not missing
        and all_json_ok
        and all_delimiters_ok
        and not pii_hits
        and all(manifest_checks.values())
        and all(content_checks.values())
    ) else "FAIL"

    report = {
        "status": status,
        "scope": "Static structure, delimiter, metadata, privacy, and semantic-presence checks; not a Unity compiler, shader compiler, or GPU test.",
        "required_files_missing": missing,
        "json_parse": json_results,
        "delimiter_balance": delimiter_results,
        "runtime_sensitive_token_hits": pii_hits,
        "manifest_checks": manifest_checks,
        "content_checks": content_checks,
        "file_count": sum(1 for path in PACKAGE.rglob("*") if path.is_file()),
        "package_tree_sha256": hashlib.sha256(
            "\n".join(
                f"{path.relative_to(PACKAGE).as_posix()} {sha256(path)}"
                for path in sorted(PACKAGE.rglob("*"))
                if path.is_file()
            ).encode("utf-8")
        ).hexdigest(),
        "unity_editor_compile_shader_gpu": "NOT EXECUTED - Unity Editor unavailable",
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
