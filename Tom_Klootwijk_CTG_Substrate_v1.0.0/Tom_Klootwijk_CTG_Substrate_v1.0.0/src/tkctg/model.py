"""Typed referential model and hybrid-state identity."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .canonical import verify_hash


class SubstrateError(ValueError):
    """Raised when a substrate violates referential or phase constraints."""


@dataclass(frozen=True)
class HybridState:
    """One addressed chrono-topological-geometric state.

    Coordinates are deliberately not identity.  ``address``, ``mode`` and the
    ordered ``lineage`` remain part of state even when two positions coincide.
    """

    address: str
    time: float
    mode: str
    position: tuple[float, ...]
    velocity: tuple[float, ...] = ()
    auxiliary: Mapping[str, Any] = field(default_factory=dict)
    lineage: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "auxiliary", MappingProxyType(dict(self.auxiliary)))
        if not self.address:
            raise SubstrateError("state address must be non-empty")
        if not self.mode:
            raise SubstrateError("state mode must be non-empty")
        if not self.position:
            raise SubstrateError("state position must contain at least one coordinate")

    @property
    def identity_key(self) -> tuple[str, str, tuple[str, ...]]:
        return self.address, self.mode, self.lineage

    def transitioned(
        self,
        *,
        time: float,
        target_mode: str,
        transition_id: str,
        auxiliary_patch: Mapping[str, Any] | None = None,
    ) -> "HybridState":
        auxiliary = dict(self.auxiliary)
        if auxiliary_patch:
            auxiliary.update(auxiliary_patch)
        return replace(
            self,
            time=time,
            mode=target_mode,
            auxiliary=auxiliary,
            lineage=self.lineage + (transition_id,),
        )


@dataclass(frozen=True)
class DefinitionGraph:
    definitions: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "DefinitionGraph":
        raw = document.get("definitions")
        if not isinstance(raw, list) or not raw:
            raise SubstrateError("document must contain a non-empty definitions list")
        return cls(tuple(MappingProxyType(dict(item)) for item in raw))

    @property
    def by_id(self) -> dict[str, Mapping[str, Any]]:
        result: dict[str, Mapping[str, Any]] = {}
        for definition in self.definitions:
            identifier = definition.get("id")
            if not isinstance(identifier, str) or not identifier:
                raise SubstrateError("definition id must be a non-empty string")
            if identifier in result:
                raise SubstrateError(f"duplicate definition id: {identifier}")
            result[identifier] = definition
        return result

    def validate(self, *, verify_hashes: bool = True) -> None:
        by_id = self.by_id
        for identifier, definition in by_id.items():
            phase = definition.get("evaluation_phase")
            if not isinstance(phase, int) or not 0 <= phase <= 9:
                raise SubstrateError(f"definition {identifier} has invalid phase")
            dependencies = definition.get("dependencies")
            if not isinstance(dependencies, list):
                raise SubstrateError(f"definition {identifier} dependencies must be a list")
            for dependency in dependencies:
                if dependency not in by_id:
                    raise SubstrateError(
                        f"definition {identifier} references unknown dependency {dependency}"
                    )
                dependency_phase = by_id[dependency].get("evaluation_phase")
                if isinstance(dependency_phase, int) and dependency_phase > phase:
                    raise SubstrateError(
                        f"definition {identifier} phase {phase} depends on later phase "
                        f"{dependency_phase}: {dependency}"
                    )
            if verify_hashes and not verify_hash(definition):
                raise SubstrateError(f"definition {identifier} has an invalid content hash")
        self.topological_order()

    def topological_order(self) -> list[str]:
        by_id = self.by_id
        indegree = {identifier: 0 for identifier in by_id}
        children: dict[str, list[str]] = {identifier: [] for identifier in by_id}
        for identifier, definition in by_id.items():
            for dependency in definition["dependencies"]:
                indegree[identifier] += 1
                children[dependency].append(identifier)

        ready = sorted(
            (identifier for identifier, degree in indegree.items() if degree == 0),
            key=lambda identifier: (by_id[identifier]["evaluation_phase"], identifier),
        )
        order: list[str] = []
        while ready:
            identifier = ready.pop(0)
            order.append(identifier)
            for child in sorted(children[identifier]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
            ready.sort(key=lambda item: (by_id[item]["evaluation_phase"], item))

        if len(order) != len(by_id):
            cyclic = sorted(identifier for identifier, degree in indegree.items() if degree > 0)
            raise SubstrateError(f"definition dependency cycle: {cyclic}")
        return order

    def instances_of(self, document: Mapping[str, Any], definition_id: str) -> list[Mapping[str, Any]]:
        instances = document.get("instances", [])
        return [item for item in instances if item.get("definition_ref") == definition_id]


def load_document(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise SubstrateError("substrate JSON root must be an object")
    return value


def trace_definition_ids(graph: DefinitionGraph, selected: Iterable[str]) -> list[str]:
    """Return the dependency-closed order restricted to selected definitions."""
    by_id = graph.by_id
    requested = set(selected)
    closure = set()

    def visit(identifier: str) -> None:
        if identifier not in by_id:
            raise SubstrateError(f"unknown definition id: {identifier}")
        if identifier in closure:
            return
        for dependency in by_id[identifier]["dependencies"]:
            visit(dependency)
        closure.add(identifier)

    for identifier in requested:
        visit(identifier)
    return [identifier for identifier in graph.topological_order() if identifier in closure]
