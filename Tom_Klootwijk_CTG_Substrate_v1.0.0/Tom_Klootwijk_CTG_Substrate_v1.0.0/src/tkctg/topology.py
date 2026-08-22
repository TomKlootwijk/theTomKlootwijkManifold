"""Explicit topology maps used by the reference profiles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .model import HybridState

TILE_SIDE = 16
TILE_RECORDS = TILE_SIDE * TILE_SIDE


@dataclass(frozen=True)
class KleinCoordinate:
    x: int
    y: int
    reflected: bool


def xor_swizzle_16x16(logical_index: int) -> int:
    if logical_index < 0:
        raise ValueError("index must be non-negative")
    tile, local = divmod(logical_index, TILE_RECORDS)
    row, column = divmod(local, TILE_SIDE)
    return tile * TILE_RECORDS + row * TILE_SIDE + (column ^ row)


def klein_coordinate(x: int, y: int, width: int, height: int) -> KleinCoordinate:
    if width <= 0 or height <= 0:
        raise ValueError("Klein grid dimensions must be positive")
    y_wrap, yy = divmod(y, height)
    reflected = bool(y_wrap & 1)
    xx = width - 1 - x if reflected else x
    xx %= width
    return KleinCoordinate(xx, yy, reflected)


def same_geometric_coordinate(first: HybridState, second: HybridState, *, tolerance: float = 0.0) -> bool:
    if len(first.position) != len(second.position):
        return False
    return all(abs(a - b) <= tolerance for a, b in zip(first.position, second.position))


def same_hybrid_state(first: HybridState, second: HybridState, *, tolerance: float = 0.0) -> bool:
    return first.identity_key == second.identity_key and same_geometric_coordinate(
        first, second, tolerance=tolerance
    )
