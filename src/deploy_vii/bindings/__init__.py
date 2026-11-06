"""Binding maps: module + table/row/fact coordinates -> report block and cell slot.

Maps are data (``cp0.py``, ``cp1.py``). A ``None`` table, row or fact id in a coordinate is
a wildcard, so a map names a table once instead of listing thousands of facts. Each
binding owns a distinct ``(block_id, cell_slot)``; no catch-all binding exists, so a fact
from a table the map does not name is reported, never silently placed.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self, TypedDict, Unpack

from pydantic import model_validator

from deploy_vii.contracts import Contract, Fact, Identifier, Text, View
from deploy_vii.display import UnitClass
from deploy_vii.report_view import FactCoord, Section, pathways

# Modules whose facts reach the Front Page or module pages; the other statuses show none.
SHOWN_STATUSES = frozenset({"accepted", "restricted", "candidate"})
# Binding targets that are rail destinations, not Front Page blocks: the Evidence and
# Limitations pages and the issuer header. A map may name these without any Pathway block.
RAIL_DESTINATIONS = frozenset({"evidence", "limitations", "header"})


class Binding(Contract):
    fact_coord: FactCoord
    block_id: Identifier
    cell_slot: Identifier
    unit_class: UnitClass
    # Tab or section label when the block shows several registers; defaults to the slot words.
    label: Text | None = None
    # Prose column of a strengths-and-weaknesses block: the thesis, a strength or a weakness.
    section: Section | None = None

    @model_validator(mode="after")
    def names_more_than_a_module(self) -> Self:
        coord = self.fact_coord
        if coord.table_id is None and coord.row_id is None and coord.fact_id is None:
            raise ValueError(
                "An all-wildcard coordinate would bind every fact of the module: "
                "name a table, row or fact"
            )
        return self

    @property
    def title(self) -> str:
        return self.label or self.cell_slot.replace("-", " ").capitalize()

    @property
    def slot(self) -> tuple[str, str]:
        return (self.block_id, self.cell_slot)

    def matches(self, module_id: str, fact: Fact) -> bool:
        coord = self.fact_coord
        return (
            coord.module_id == module_id
            and coord.table_id in {None, fact.table_id}
            and coord.row_id in {None, fact.row_id}
            and coord.fact_id in {None, fact.fact_id}
        )


class Placement(TypedDict, total=False):
    """A binding's optional coordinates: the row it narrows to, the prose column of a
    strengths-and-weaknesses block, and an explicit cell slot (else the binder derives one)."""

    row: str | None
    section: Section | None
    slot: str | None


@dataclass(frozen=True)
class Binder:
    """How one module's map makes its bindings: the module id and how a table id becomes a cell
    slot (``prefix``, then the id lower-cased with "." as "-" and, where ``hyphenate``, "_" as
    "-" too). The per-module rules differ and are kept, so every shipped slot keeps its name."""

    module_id: str
    prefix: str = ""
    hyphenate: bool = False

    def slot(self, table: str) -> str:
        slug = table.lower().replace(".", "-")
        return self.prefix + (slug.replace("_", "-") if self.hyphenate else slug)

    def bind(
        self,
        table: str,
        block: str,
        label: str | None = None,
        unit: UnitClass = "text",
        **placement: Unpack[Placement],
    ) -> Binding:
        """One binding of ``table`` (narrowed to ``row`` when given) to ``block``."""
        return Binding(
            fact_coord=FactCoord(
                module_id=self.module_id, table_id=table, row_id=placement.get("row")
            ),
            block_id=block,
            cell_slot=placement.get("slot") or self.slot(table),
            unit_class=unit,
            label=label,
            section=placement.get("section"),
        )


class BindingMap(Contract):
    module_id: Identifier
    entries: tuple[Binding, ...]

    @model_validator(mode="after")
    def stays_in_module(self) -> Self:
        if any(entry.fact_coord.module_id != self.module_id for entry in self.entries):
            raise ValueError("A binding map holds bindings for its own module only")
        return self


def _name(module_id: str, fact: Fact) -> str:
    return f"{module_id}/{fact.table_id}/{fact.row_id}/{fact.fact_id!r}"


def _map_issues(maps: tuple[BindingMap, ...], entries: list[Binding]) -> list[str]:
    """A module with more than one map, and a slot bound more than once."""
    issues = [
        f"{module_id} has more than one binding map"
        for module_id, count in Counter(m.module_id for m in maps).items()
        if count > 1
    ]
    issues.extend(
        f"slot {block_id}/{cell_slot} is bound {count} times"
        for (block_id, cell_slot), count in Counter(e.slot for e in entries).items()
        if count > 1
    )
    return issues


def validate_bindings(view: View, maps: Iterable[BindingMap]) -> tuple[str, ...]:
    """One message per unbound or doubly bound fact, per shared slot and per repeated map.

    A fact in an accepted, restricted or candidate module must match at least one binding; one
    that matches none is unbound. A register may be placed in several blocks when no Pathway
    composes more than one of them (T4.17 feeds FP 01's capital structure and FP 02's EBITDA
    adjustments), so a fact is doubly bound when two of its bindings name one block, or name two
    blocks the run's Pathway composes (a rail destination is composed everywhere). A fact whose
    every binding names a block the run's Pathway does not compose is bound, not placed: the
    report lists that block as unplaced (``report_view._unplaced``) instead of failing the run.
    Empty when valid.
    """
    maps = tuple(maps)
    composed = RAIL_DESTINATIONS | set(
        next(item for item in pathways() if item.id == view.run.pathway).blocks
    )
    entries = [entry for m in maps for entry in m.entries]
    issues = _map_issues(maps, entries)
    by_module: dict[str, list[Binding]] = {}
    for entry in entries:
        by_module.setdefault(entry.fact_coord.module_id, []).append(entry)
    for module in view.modules:
        if module.status not in SHOWN_STATUSES:
            continue
        candidates = by_module.get(module.module_id, [])
        for fact in module.facts:
            hits = [e for e in candidates if e.matches(module.module_id, fact)]
            blocks = Counter(e.block_id for e in hits)
            placed = {block for block in blocks if block in composed}
            if not hits:
                issues.append(f"unbound fact {_name(module.module_id, fact)}")
            elif max(blocks.values()) > 1 or len(placed) > 1:
                slots = ", ".join(f"{e.block_id}/{e.cell_slot}" for e in hits)
                issues.append(f"doubly bound fact {_name(module.module_id, fact)}: {slots}")
    return tuple(issues)
