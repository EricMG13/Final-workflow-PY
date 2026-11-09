"""S13-C09: the T4.12 projection-gap rows register source gaps, not the gap table's own blanks."""

import test_statement_quantity_outputs as fixtures

from deploy_vii.canonical_tables import COLUMNS, _join, _keys, _projection_gap_rows, _row
from deploy_vii.model_interface import InterfaceGap, _Tables


def test_a_gap_row_without_periods_adds_no_row_about_itself() -> None:
    # By hand: the narrative gap "gap-funding" names no period, so its T4.12 row leaves field_2
    # empty and the ledger records that blank as a gap of table T4.12. One real gap, of table
    # T4.10, is registered; the blank of the T4.12 row itself is not: two T4.12 rows in all.
    tables = _Tables(
        fixtures._book(),
        schemas={k: (title, None, _keys(k)) for k, (title, _) in COLUMNS.items()},
    )
    _row(
        tables,
        "T4.12",
        "gap-funding",
        _join(()) or "Unspecified gap scope",
        ("gap-funding: Funding not assessed", "funding", _join(()), "impact", "WARN", "action"),
    )
    assert [(g.table_id, g.field) for g in tables.gaps] == [("T4.12", "field_2")]
    tables.gaps.append(
        InterfaceGap(table_id="T4.10", row_id="r1", field="field_3", reason="Missing")
    )
    _projection_gap_rows(tables)
    assert len(tables.rows["T4.12"]) == 2
    texts = [f.text for f in tables.facts if f.table_id == "T4.12" and f.field == "field_0"]
    assert texts[0] == "gap-funding: Funding not assessed"
    assert texts[1] == "T4.10/r1/field_3: Missing"
