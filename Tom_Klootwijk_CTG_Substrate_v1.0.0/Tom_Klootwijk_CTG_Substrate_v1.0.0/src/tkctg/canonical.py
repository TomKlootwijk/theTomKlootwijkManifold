"""Canonical JSON and SHA-256 content-address helpers."""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

HASH_FIELD = "content_hash"


def canonical_bytes(record: Mapping[str, Any], *, omit_hash: bool = True) -> bytes:
    """Return deterministic UTF-8 JSON bytes.

    The formal registry excludes ``content_hash`` from its own digest, matching
    the content-address rule used in the specification.
    """
    value = copy.deepcopy(dict(record))
    if omit_hash:
        value.pop(HASH_FIELD, None)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_hash(record: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(record)).hexdigest()


def attach_hash(record: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(record))
    value[HASH_FIELD] = content_hash(value)
    return value


def verify_hash(record: Mapping[str, Any]) -> bool:
    supplied = record.get(HASH_FIELD)
    return isinstance(supplied, str) and supplied == content_hash(record)
