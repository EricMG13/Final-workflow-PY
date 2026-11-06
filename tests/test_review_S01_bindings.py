"""S01 review: the shipped binding maps after the per-module `_bind` helpers became one
`Binder.bind`.

The digest below is of the maps as the copied helpers produced them (recorded before the
change, from `"\\n".join(m.model_dump_json() for m in SHIPPED_MAPS)`), so the test pins the old
output byte for byte, not whatever the new code writes."""

import hashlib

import pytest

from deploy_vii.bindings import Binder
from deploy_vii.bindings.shipped import SHIPPED_MAPS

BEFORE_SHA256 = "0761269c49141a91e89e30fc8f176e39fd82608fc118fb4cc005bed39d90708e"


def test_shipped_maps_are_byte_identical_to_the_copied_helpers() -> None:
    text = "\n".join(m.model_dump_json() for m in SHIPPED_MAPS)
    assert sum(len(m.entries) for m in SHIPPED_MAPS) == 273
    assert hashlib.sha256(text.encode()).hexdigest() == BEFORE_SHA256


@pytest.mark.parametrize(
    ("module_id", "table_id", "row_id", "block_id", "slot"),
    [
        # cp1d keeps "_" in its slots; cp1a turns it into "-".
        ("CP-1D", "cp1_references", None, "evidence", "cp1d-cp1_references"),
        ("CP-1A", "company_description", "company", "company-operating-model", None),
        ("CP-1", "T4.10", None, "model-chart-strip", "kpi-dashboard"),
        ("CP-1", "pro-forma", None, "capital-structure", "pro-forma"),
        ("CP-0", "T1", None, "header", "run-identity"),
        ("CP-1B", "T1B.3", "drivers", "variance-drivers", "cp1b-drivers"),
        ("CP-2", "T2.10", None, "evidence", "cp2-t2-10"),
    ],
)
def test_named_slots_keep_their_names(
    module_id: str, table_id: str, row_id: str | None, block_id: str, slot: str | None
) -> None:
    entries = [
        e
        for m in SHIPPED_MAPS
        for e in m.entries
        if e.fact_coord.module_id == module_id
        and e.fact_coord.table_id == table_id
        and e.block_id == block_id
        and e.fact_coord.row_id in {None, row_id}
    ]
    assert len(entries) == 1
    if slot is None:  # cp1a's company row: the slot comes from the hyphenated table id
        assert entries[0].cell_slot == "cp1a-company-description"
        assert entries[0].fact_coord.row_id is not None
    else:
        assert entries[0].cell_slot == slot
        assert entries[0].fact_coord.row_id == row_id


def test_binder_slot_rules() -> None:
    assert Binder("CP-1").slot("T4.18") == "t4-18"
    assert Binder("CP-1D", "cp1d-").slot("cp1_references") == "cp1d-cp1_references"
    assert Binder("CP-2A", "cp2a-", hyphenate=True).slot("gaps_ledger.T2") == "cp2a-gaps-ledger-t2"
    bound = Binder("CP-2", "cp2-").bind("T2.7", "strengths-weaknesses", "Thesis", section="thesis")
    assert (bound.cell_slot, bound.section, bound.unit_class) == ("cp2-t2-7", "thesis", "text")
    explicit = Binder("CP-0").bind("T1", "header", slot="run-identity")
    assert (explicit.cell_slot, explicit.label, explicit.title) == (
        "run-identity",
        None,
        "Run identity",
    )
