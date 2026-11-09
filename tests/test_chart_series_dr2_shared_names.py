"""S12-A06: two CP-4C classes with one name keep their own DR.2 and waterfall points."""

import chart_dr_support as support

from deploy_workflow.restructuring_series import cp4c_chart_series


def test_two_classes_with_one_name_are_two_rows_of_one_cell_per_scenario() -> None:
    # By hand: the positive case has creditor classes c01, c02 and c03, and three scenarios, so
    # DR.2 is three rows of three cells. Naming c02 like c01 must not merge them into one row of
    # six cells (the block's own columns check refuses that) nor drop a row.
    module = support.composer_module("positive")
    first = next(
        f for f in module.facts if (f.table_id, f.row_id, f.field) == ("T4E.2", "c01", "name")
    )
    renamed = tuple(
        f.model_copy(update={"text": first.text})
        if (f.table_id, f.row_id, f.field) == ("T4E.2", "c02", "name")
        else f
        for f in module.facts
    )
    module = module.model_copy(update={"facts": renamed})
    figure = cp4c_chart_series(module)[0]
    assert [p.category for p in figure.points[::3]] == [
        "Senior secured term loan (c01)",
        "Senior secured term loan (c02)",
        "Other current liabilities",
    ]
    block = {b.block_id: b for b in support.report_of(support.view_with(module)).blocks}[
        "recovery-by-class"
    ]
    twin = block.figures[0].chart.table_twin
    assert [len(r.cells) for r in twin.rows] == [len(figure.series)] * 3
    assert [r.label for r in twin.rows][:2] == [
        "Senior secured term loan (c01)",
        "Senior secured term loan (c02)",
    ]
