"""S09 review regressions: chart categories keep facility and class identities apart, and a
CP-4C register with no creditor class is an n/a DR.2 frame, not an exception that takes the
DR.3-DR.5 waterfalls down with it. Expected categories and texts are literals."""

import chart_dr_support as support
import chart_wiring_c as w

from deploy_vii.contracts import ModuleView
from deploy_workflow.liquidity_series import cp3c_chart_series
from deploy_workflow.restructuring_series import cp4c_chart_series


def _relabel_t3d1(module: ModuleView, label: str) -> ModuleView:
    tables = tuple(
        table.model_copy(
            update={"rows": tuple(row.model_copy(update={"label": label}) for row in table.rows)}
        )
        if table.table_id == "T3D.1"
        else table
        for table in module.tables
    )
    return module.model_copy(update={"tables": tables})


def test_cr3_facilities_sharing_a_label_stay_two_categories() -> None:
    module = _relabel_t3d1(w.fixture_register("fixture_two_facilities").module, "Term Loan B")
    (record,) = cp3c_chart_series(module)
    assert [p.category for p in record.points] == [
        "Term Loan B (r01)",
        "Term Loan B (r01)",
        "Term Loan B (r02)",
        "Term Loan B (r02)",
    ]
    # The consumer's ChartSpec identity: a point is its series and category, never repeated.
    assert len({(p.series, p.category) for p in record.points}) == len(record.points) == 4


def test_cr3_distinct_labels_are_unchanged() -> None:
    (record,) = cp3c_chart_series(w.fixture_register("fixture_two_facilities").module)
    assert [p.category for p in record.points[::2]] == ["notes", "term-loan"]


def _without_creditors(module: ModuleView) -> ModuleView:
    facts = {f.fact_id: f for f in module.facts}
    creditors = {
        f.row_id
        for f in module.facts
        if f.table_id == "T4E.2"
        and f.field == "name"
        and facts[f"T4E.2.{f.row_id}.kind"].text != "equity"
    }
    assert creditors == {"c01", "c02", "c03"}
    kept = tuple(f for f in module.facts if not (f.table_id == "T4E.2" and f.row_id in creditors))
    return module.model_copy(update={"facts": kept})


def test_dr2_without_a_creditor_class_is_an_na_frame_and_the_waterfalls_stay() -> None:
    module = _without_creditors(support.composer_module(support.CASES[0]))
    figures = cp4c_chart_series(module)
    assert [f.fig_id for f in figures] == ["DR.2", "DR.3", "DR.4", "DR.5"]
    dr2 = figures[0]
    assert (dr2.kind, dr2.points) == ("na", ())
    assert dr2.reason == (
        "The CP-4C claims register (T4E.2) lists no creditor class; no recovery is charted."
    )
    assert dr2.series == ("Base 4.00x", "Downside 3.00x", "Stress 2.00x")
    for waterfall in figures[1:]:
        assert waterfall.kind == "waterfall"
        assert [p.category for p in waterfall.points] == ["Residual to equity", "Enterprise value"]


def test_dr_classes_sharing_a_name_stay_apart() -> None:
    module = support.composer_module(support.CASES[0])
    renamed = tuple(
        f.model_copy(update={"text": "Trade payables"}) if f.fact_id == "T4E.2.c03.name" else f
        for f in module.facts
    )
    figures = cp4c_chart_series(module.model_copy(update={"facts": renamed}))
    categories = ["Senior secured term loan", "Trade payables (c02)", "Trade payables (c03)"]
    assert list(dict.fromkeys(p.category for p in figures[0].points)) == categories
    for waterfall in figures[1:]:
        assert [p.category for p in waterfall.points][:3] == categories
        assert len({(p.series, p.category) for p in waterfall.points}) == len(waterfall.points)
