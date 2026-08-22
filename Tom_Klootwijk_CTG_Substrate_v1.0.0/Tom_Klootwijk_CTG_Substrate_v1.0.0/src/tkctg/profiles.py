"""Bounded profile helpers for KLSC1-like chains and optional TK7 geometry."""
from __future__ import annotations

from typing import Mapping, Sequence

from .geometry import pairwise_orthogonal, standard_axes

MAX_CHECKPOINT_STRIDE = 64


def validate_checkpoint_path(
    parent_indices: Sequence[int],
    checkpoint_flags: Sequence[bool],
    target: int,
    *,
    maximum_stride: int = MAX_CHECKPOINT_STRIDE,
) -> list[int]:
    if len(parent_indices) != len(checkpoint_flags):
        raise ValueError("parent and checkpoint arrays differ in length")
    if not 0 <= target < len(parent_indices):
        raise ValueError("target node is out of range")
    if not 1 <= maximum_stride <= MAX_CHECKPOINT_STRIDE:
        raise ValueError("maximum_stride must be in 1..64")
    path: list[int] = []
    current = target
    for _ in range(maximum_stride + 1):
        if current in path:
            raise ValueError("cycle in parent chain")
        path.append(current)
        if checkpoint_flags[current] or parent_indices[current] < 0:
            return path
        current = parent_indices[current]
        if not 0 <= current < len(parent_indices):
            raise ValueError("parent index is out of range")
    raise ValueError("checkpoint path exceeds bounded stride")


def tk7_axes() -> tuple[tuple[float, ...], ...]:
    axes = standard_axes(7)
    assert pairwise_orthogonal(axes)
    return axes
