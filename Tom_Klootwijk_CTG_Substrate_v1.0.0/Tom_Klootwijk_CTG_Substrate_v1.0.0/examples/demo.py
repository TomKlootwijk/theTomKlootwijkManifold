#!/usr/bin/env python3
"""Deterministic demonstration of the TK-CTG reference model."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tkctg.events import Evaluation, apply_chrono_latch, certify_crossing
from tkctg.geometry import DecodeParameters, decode_klb37, encode_klb37, record_has_even_parity, sphere_sdf
from tkctg.model import DefinitionGraph, HybridState, load_document, trace_definition_ids
from tkctg.topology import klein_coordinate, xor_swizzle_16x16


def main() -> int:
    document = load_document(ROOT / "spec" / "tk_ctg_substrate_definition.json")
    graph = DefinitionGraph.from_document(document)
    graph.validate()

    parameters = DecodeParameters(center=(1.0, -2.0, 0.5), radius_scale=10.0, log_k=15.0)
    source_point = (4.0, 1.0, 2.0)
    code = encode_klb37(source_point, parameters, symbol=5)
    decoded_point = decode_klb37(code, parameters)

    topology = klein_coordinate(x=17, y=10, width=16, height=10)
    logical = 37
    physical = xor_swizzle_16x16(logical)

    field = sphere_sdf((0.0, 0.0, 0.0), 1.0)
    previous = Evaluation(guard=0.20, supported=True, compatible=True)
    current = Evaluation(guard=-0.10, supported=True, compatible=True)
    crossing = certify_crossing(previous, current, 2.0, 3.0, crossing_band=0.25)
    state = HybridState(
        address="point:demo:0",
        time=2.0,
        mode="outside",
        position=(1.2, 0.0, 0.0),
        lineage=("seed:demo",),
    )
    latched = apply_chrono_latch(
        state,
        crossing,
        target_mode="inside",
        transition_id="transition:sphere-entry",
        auxiliary_patch={"field_value_after": field((0.9, 0.0, 0.0))},
    )

    trace = trace_definition_ids(
        graph,
        ["substrate:tom-klootwijk-ctg-v1"],
    )
    output = {
        "schema_version": document["schema_version"],
        "definition_count": len(document["definitions"]),
        "definition_order": graph.topological_order(),
        "substrate_trace": trace,
        "klb37": {
            "source_point": source_point,
            "code_hex": hex(code),
            "even_parity": record_has_even_parity(code),
            "decoded_point": decoded_point,
            "maximum_abs_component_error": max(abs(a - b) for a, b in zip(source_point, decoded_point)),
        },
        "topology": {
            "logical_index": logical,
            "xor_swizzled_index": physical,
            "xor_unswizzled_index": xor_swizzle_16x16(physical),
            "klein_coordinate": {
                "x": topology.x,
                "y": topology.y,
                "reflected": topology.reflected,
            },
        },
        "chrono_latch": {
            "verified": crossing.verified,
            "crossing_time": crossing.crossing_time,
            "pre_mode": state.mode,
            "post_mode": latched.mode,
            "lineage": latched.lineage,
            "latch": latched.auxiliary.get("latch", 0),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
