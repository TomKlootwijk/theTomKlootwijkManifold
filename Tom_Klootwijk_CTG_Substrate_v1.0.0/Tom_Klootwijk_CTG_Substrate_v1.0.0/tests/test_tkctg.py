from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import jsonschema

from tkctg.canonical import attach_hash, canonical_bytes, content_hash, verify_hash
from tkctg.events import Evaluation, apply_chrono_latch, certify_crossing, evaluate_implicit_guard
from tkctg.geometry import (
    DecodeParameters,
    csg_union,
    decode_klb37,
    encode_klb37,
    pairwise_orthogonal,
    record_has_even_parity,
    sphere_sdf,
    standard_axes,
)
from tkctg.model import DefinitionGraph, HybridState, SubstrateError, load_document
from tkctg.profiles import tk7_axes, validate_checkpoint_path
from tkctg.topology import klein_coordinate, same_geometric_coordinate, same_hybrid_state, xor_swizzle_16x16


class CanonicalTests(unittest.TestCase):
    def test_01_canonical_key_order(self) -> None:
        self.assertEqual(canonical_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}')

    def test_02_hash_attach_and_verify(self) -> None:
        record = attach_hash({"id": "def:x", "value": 3})
        self.assertTrue(verify_hash(record))
        changed = dict(record)
        changed["value"] = 4
        self.assertFalse(verify_hash(changed))


class DefinitionGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = load_document(ROOT / "spec" / "tk_ctg_substrate_definition.json")
        cls.graph = DefinitionGraph.from_document(cls.document)

    def test_03_schema_validation(self) -> None:
        schema = json.loads((ROOT / "spec" / "tk_ctg_substrate.schema.json").read_text())
        jsonschema.Draft202012Validator(schema).validate(self.document)

    def test_04_all_definition_hashes_verify(self) -> None:
        self.graph.validate()
        self.assertTrue(all(verify_hash(item) for item in self.document["definitions"]))

    def test_05_topological_order_is_complete(self) -> None:
        order = self.graph.topological_order()
        self.assertEqual(len(order), len(self.document["definitions"]))
        self.assertEqual(len(order), len(set(order)))

    def test_06_cycle_is_rejected(self) -> None:
        document = copy.deepcopy(self.document)
        first = document["definitions"][0]
        first["dependencies"] = [document["definitions"][-1]["id"]]
        first["evaluation_phase"] = 9
        first["content_hash"] = content_hash(first)
        with self.assertRaises(SubstrateError):
            DefinitionGraph.from_document(document).validate()


class GeometryTests(unittest.TestCase):
    def test_07_klb37_even_parity(self) -> None:
        code = encode_klb37((0.1, 0.2, 0.3), symbol=7)
        self.assertTrue(record_has_even_parity(code))

    def test_08_klb37_roundtrip_is_bounded(self) -> None:
        params = DecodeParameters(center=(1.0, -2.0, 0.5), radius_scale=10.0, log_k=15.0)
        point = (4.0, 1.0, 2.0)
        decoded = decode_klb37(encode_klb37(point, params, symbol=5), params)
        self.assertLess(max(abs(a - b) for a, b in zip(point, decoded)), 0.03)

    def test_09_sphere_zero_level(self) -> None:
        field = sphere_sdf((0.0, 0.0, 0.0), 2.0)
        self.assertAlmostEqual(field((2.0, 0.0, 0.0)), 0.0, places=12)
        self.assertLess(field((0.0, 0.0, 0.0)), 0.0)
        self.assertGreater(field((3.0, 0.0, 0.0)), 0.0)
        self.assertTrue(field.exact_signed_distance)

    def test_10_csg_does_not_silently_claim_exact_distance(self) -> None:
        first = sphere_sdf((0.0, 0.0, 0.0), 1.0)
        second = sphere_sdf((1.0, 0.0, 0.0), 1.0)
        self.assertFalse(csg_union(first, second).exact_signed_distance)

    def test_11_tk7_axes_are_orthogonal(self) -> None:
        axes = tk7_axes()
        self.assertEqual(len(axes), 7)
        self.assertTrue(pairwise_orthogonal(axes))
        self.assertEqual(axes, standard_axes(7))


class TopologyTests(unittest.TestCase):
    def test_12_xor_swizzle_is_involution(self) -> None:
        for index in [0, 1, 15, 16, 37, 255, 256, 4097]:
            self.assertEqual(xor_swizzle_16x16(xor_swizzle_16x16(index)), index)

    def test_13_klein_y_seam_reflects_x(self) -> None:
        base = klein_coordinate(3, 0, 16, 10)
        wrapped = klein_coordinate(3, 10, 16, 10)
        self.assertEqual((base.x, base.y, base.reflected), (3, 0, False))
        self.assertEqual((wrapped.x, wrapped.y, wrapped.reflected), (12, 0, True))

    def test_14_coordinates_are_not_identity(self) -> None:
        first = HybridState("a", 0.0, "sheet-0", (1.0, 2.0, 3.0), lineage=("root",))
        second = HybridState("a", 0.0, "sheet-1", (1.0, 2.0, 3.0), lineage=("root",))
        self.assertTrue(same_geometric_coordinate(first, second))
        self.assertFalse(same_hybrid_state(first, second))


class ChronoEventTests(unittest.TestCase):
    def test_15_verified_crossing_latches_mode(self) -> None:
        crossing = certify_crossing(
            Evaluation(0.2, True, True),
            Evaluation(-0.1, True, True),
            2.0,
            3.0,
            crossing_band=0.25,
        )
        self.assertTrue(crossing.verified)
        state = HybridState("point:0", 2.0, "outside", (1.2, 0.0, 0.0))
        post = apply_chrono_latch(
            state,
            crossing,
            target_mode="inside",
            transition_id="sphere-entry",
        )
        self.assertEqual(post.mode, "inside")
        self.assertEqual(post.auxiliary["latch"], 1)
        self.assertEqual(post.lineage[-1], "sphere-entry")

    def test_16_support_or_compatibility_rejects_crossing(self) -> None:
        crossing = certify_crossing(
            Evaluation(0.1, False, True),
            Evaluation(-0.1, False, True),
            0.0,
            1.0,
            crossing_band=0.2,
        )
        self.assertFalse(crossing.verified)
        self.assertEqual(crossing.reason, "support-or-compatibility-rejected")

    def test_17_implicit_guard_uses_abs_sdf_band(self) -> None:
        field = sphere_sdf((0.0, 0.0, 0.0), 1.0)
        evaluation = evaluate_implicit_guard(field, (1.02, 0.0, 0.0), epsilon=0.05)
        self.assertLessEqual(evaluation.guard, 0.0)


class ProfileTests(unittest.TestCase):
    def test_18_checkpoint_path_is_bounded(self) -> None:
        parents = [-1] + list(range(0, 10))
        checkpoints = [True] + [False] * 10
        path = validate_checkpoint_path(parents, checkpoints, 10, maximum_stride=16)
        self.assertEqual(path[0], 10)
        self.assertEqual(path[-1], 0)
        self.assertEqual(len(path), 11)

    def test_19_checkpoint_cycle_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_checkpoint_path([1, 0], [False, False], 1, maximum_stride=4)


if __name__ == "__main__":
    unittest.main()
