"""CP-1 candidate registers -> Financials and credit metrics, capital structure, chart strip.

FP 01 has no separate metric strip: the Model chart strip holds S.1 to S.4 and the KPI
dashboard register (T4.10) feeds it. FP 02 places the same two registers again, in its own
``metric-strip`` and ``ebitda-adjustments`` blocks: a second placement per Pathway
composition, never a second binding inside one (``validate_bindings``). Capital structure is
a tabbed block: the debt facility register, the adjusted EBITDA bridge (T4.17) and the pro
forma adjustments.

Registers without a Front Page block go to Evidence or Limitations; module register detail
belongs on the module's Full analysis page. ``unit_class`` is the table's default; the
cell-level class follows each fact's unit (``report_view.fact_spelling``).
"""

from deploy_vii.bindings import Binder, BindingMap

_bind = Binder("CP-1").bind


_FINANCIALS = "financials-credit-metrics"

CP1 = BindingMap(
    module_id="CP-1",
    entries=(
        # Financial statements, calculations and the model's schedules.
        _bind("T4.4", _FINANCIALS, unit="amount", slot="income-statement"),
        _bind("T4.5", _FINANCIALS, unit="amount", slot="cash-flow-statement"),
        _bind("T4.6", _FINANCIALS, unit="amount", slot="balance-sheet"),
        _bind("T4.8", _FINANCIALS, unit="amount", slot="constructed-periods"),
        _bind("T4.9", _FINANCIALS, unit="amount", slot="calculations"),
        _bind("T4.15", _FINANCIALS, unit="amount", slot="account-register"),
        _bind("T4.16", _FINANCIALS, unit="amount", slot="segment-revenue"),
        _bind("segment-allocation", _FINANCIALS, unit="amount"),
        _bind("operating-kpis", _FINANCIALS, unit="amount"),
        # Model chart strip (FP 01 S.1 to S.4).
        _bind("T4.10", "model-chart-strip", "KPI dashboard", slot="kpi-dashboard"),
        # Capital structure tabs, in tab order.
        _bind(
            "T4.18", "capital-structure", "Capital structure", unit="amount", slot="debt-facilities"
        ),
        _bind(
            "T4.17",
            "capital-structure",
            "EBITDA adjustments",
            unit="amount",
            slot="adjusted-ebitda-bridge",
        ),
        _bind("pro-forma", "capital-structure", "Transaction and new debt", unit="amount"),
        # Maturity wall (FP 04 S.4): the facility register is the Model's primary tab; CP-2D's
        # T2E.4 follows as a further tab (a second placement of T4.18, never a second binding in
        # one block).
        _bind("T4.18", "maturity-wall", "Capital structure", unit="amount", slot="debt-facilities"),
        # Earnings Update (FP 02): the same registers placed in that Pathway's own blocks.
        _bind(
            "T4.17",
            "ebitda-adjustments",
            "House view",
            unit="amount",
            slot="adjusted-ebitda-bridge",
        ),
        _bind("T4.10", "metric-strip", "KPI dashboard", slot="kpi-dashboard"),
        # Evidence.
        _bind("T4.1", "evidence", slot="source-register"),
        _bind("T4.2", "evidence", slot="entity-periods"),
        _bind("T4.3", "evidence", slot="normalizations"),
        _bind("T4.11", "evidence", slot="definition-conflicts"),
        _bind("T4.14", "evidence", slot="period-register"),
        _bind("T4.19", "evidence", slot="model-reconciliation"),
        _bind("evidence-trace", "evidence"),
        # Limitations.
        _bind("T4.12", "limitations", slot="gaps-and-warnings"),
        _bind("T4.13", "limitations", slot="downstream-readiness"),
        _bind("model-readiness", "limitations"),
        _bind("analysis-coverage", "limitations"),
        _bind("funding-assessment", "limitations"),
        _bind("statement-coverage", "limitations"),
        _bind("required-stories", "limitations"),
    ),
)
