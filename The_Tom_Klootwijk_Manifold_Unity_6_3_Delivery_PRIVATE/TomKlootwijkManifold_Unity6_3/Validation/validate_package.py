#!/usr/bin/env python3
"""Static delivery validation that does not require a Unity installation."""
from __future__ import annotations

import hashlib
import json
import re
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
    "Runtime/Shaders/TKProjectedSliceURP.shader",
    "Runtime/Shaders/TKRoundedSDFSurrogateURP.shader",
    "Editor/TomKlootwijk.Manifold.Editor.asmdef",
    "Editor/TKManifoldMenu.cs",
    "Tests/Runtime/TomKlootwijk.Manifold.Tests.asmdef",
    "Tests/Runtime/TKManifoldTests.cs",
]

SENSITIVE_TOKENS = [
    "NL200678942",
    "200678942",
    "10-07-1990",
    "1990-07-10",
]

EXPECTED_FINGERPRINT = "7d85cc5019309659b8279866b0bf6dde69ef18373d25dc71051fe8824ee2e3b4"


def strip_comments_and_literals(text: str) -> str:
    """Replace comments and literals with spaces while preserving delimiters outside them."""
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
    reverse = {v: k for k, v in pairs.items()}
    stack: list[tuple[str, int]] = []
    line = 1
    for ch in clean:
        if ch == "\n":
            line += 1
        elif ch in pairs:
            stack.append((ch, line))
        elif ch in reverse:
            if not stack or stack[-1][0] != reverse[ch]:
                return {"status": "FAIL", "message": f"unexpected {ch} at line {line}"}
            stack.pop()
    if stack:
        ch, where = stack[-1]
        return {"status": "FAIL", "message": f"unclosed {ch} from line {where}"}
    return {"status": "PASS"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    missing = [p for p in REQUIRED if not (PACKAGE / p).is_file()]

    json_results: dict[str, str] = {}
    json_objects: dict[str, object] = {}
    for path in sorted(PACKAGE.rglob("*.json")) + sorted(PACKAGE.rglob("*.asmdef")):
        rel = path.relative_to(PACKAGE).as_posix()
        try:
            json_objects[rel] = json.loads(path.read_text(encoding="utf-8"))
            json_results[rel] = "PASS"
        except Exception as exc:  # pragma: no cover - diagnostic path
            json_results[rel] = f"FAIL: {exc}"

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
        "name": isinstance(package_json, dict) and package_json.get("name") == "com.tomklootwijk.manifold",
        "version": isinstance(package_json, dict) and package_json.get("version") == "1.0.0",
        "unity": isinstance(package_json, dict) and package_json.get("unity") == "6000.3",
        "urp_dependency": isinstance(package_json, dict)
        and package_json.get("dependencies", {}).get("com.unity.render-pipelines.universal") == "17.3.0",
    }

    runtime_text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((PACKAGE / "Runtime").rglob("*"))
        if p.is_file()
    )
    content_checks = {
        "fingerprint_embedded": EXPECTED_FINGERPRINT in runtime_text,
        "exact_dimensions_present": "IntrinsicDimension = 7" in runtime_text and "AmbientDimension = 14" in runtime_text,
        "projected_slice_disclaimer_present": "cannot preserve seven-way orthogonality" in runtime_text,
        "sdf_surrogate_disclaimer_present": "rounded 3D surrogate" in runtime_text,
        "urp_core_include_present": runtime_text.count(
            'Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl'
        ) >= 2,
        "tests_include_hamming_distance_two": "HammingDistanceTwo" in (PACKAGE / "Tests/Runtime/TKManifoldTests.cs").read_text(encoding="utf-8"),
    }

    all_json_ok = all(v == "PASS" for v in json_results.values())
    all_delimiters_ok = all(v["status"] == "PASS" for v in delimiter_results.values())
    all_manifest_ok = all(manifest_checks.values())
    all_content_ok = all(content_checks.values())
    status = "PASS" if not missing and all_json_ok and all_delimiters_ok and not pii_hits and all_manifest_ok and all_content_ok else "FAIL"

    report = {
        "status": status,
        "scope": "Static structure, syntax-delimiter, metadata, privacy, and content checks; not a Unity compiler or GPU test.",
        "required_files_missing": missing,
        "json_parse": json_results,
        "delimiter_balance": delimiter_results,
        "runtime_sensitive_token_hits": pii_hits,
        "manifest_checks": manifest_checks,
        "content_checks": content_checks,
        "file_count": sum(1 for p in PACKAGE.rglob("*") if p.is_file()),
        "package_tree_sha256": hashlib.sha256(
            "\n".join(
                f"{p.relative_to(PACKAGE).as_posix()} {sha256(p)}"
                for p in sorted(PACKAGE.rglob("*"))
                if p.is_file()
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
