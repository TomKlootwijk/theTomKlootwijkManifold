"""Tom Klootwijk chrono-topological-geometric reference package."""
from .canonical import attach_hash, canonical_bytes, content_hash, verify_hash
from .events import Crossing, Evaluation, apply_chrono_latch, certify_crossing
from .geometry import DecodeParameters, ImplicitField, decode_klb37, encode_klb37, sphere_sdf
from .model import DefinitionGraph, HybridState, SubstrateError, load_document
from .topology import KleinCoordinate, klein_coordinate, xor_swizzle_16x16

__all__ = [
    "attach_hash",
    "canonical_bytes",
    "content_hash",
    "verify_hash",
    "Crossing",
    "Evaluation",
    "apply_chrono_latch",
    "certify_crossing",
    "DecodeParameters",
    "ImplicitField",
    "decode_klb37",
    "encode_klb37",
    "sphere_sdf",
    "DefinitionGraph",
    "HybridState",
    "SubstrateError",
    "load_document",
    "KleinCoordinate",
    "klein_coordinate",
    "xor_swizzle_16x16",
]
