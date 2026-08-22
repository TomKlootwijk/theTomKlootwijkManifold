#!/usr/bin/env python3
"""Small structural audit for the bounded hot-query loops.

This is not a theorem prover. It verifies that the delivered source still contains
compile-time MaxSegments/MaxPatches loop bounds and no while-loop in the query
header.
"""
from pathlib import Path
import sys

path = Path(__file__).resolve().parents[1] / "include" / "tkm" / "tkm.hpp"
text = path.read_text(encoding="utf-8")
required = [
    "index < MaxSegments",
    "slot < MaxPatches",
    "fixed_query_bound",
    "normalized_storage_ratio",
]
missing = [item for item in required if item not in text]
if "while (" in text or "while(" in text:
    missing.append("unexpected while-loop in tkm.hpp")
if missing:
    print("FAIL")
    for item in missing:
        print(" -", item)
    sys.exit(1)
print("PASS: fixed MaxSegments/MaxPatches hot-query structure present")
