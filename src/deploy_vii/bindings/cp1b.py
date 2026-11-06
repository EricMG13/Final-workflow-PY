"""CP1B paired earnings and analytical gaps -> FP02 and existing evidence rails.

Layout metadata contains identities and labels, never financial answers. Whole
paired tables preserve their columns; the assessment table is partitioned by row
so no fact is bound twice in one pathway. Rail bindings provide coverage; actual
source inventory and module limitations keep their existing rendering behavior.
"""

from dataclasses import dataclass, replace

from deploy_vii.bindings import Binder, BindingMap


@dataclass(frozen=True)
class _Layout:
    table_id: str
    title: str
    row_header: str
    fields: tuple[str, ...]
    rows: tuple[tuple[str, str], ...]


_LAYOUT_TEMPLATES = (
    _Layout(
        "T1B.1",
        "Paired earnings results",
        "Measure",
        ("prior", "current", "delta", "growth"),
        (
            ("revenue", "Revenue ({unit})"),
            ("ebitda", "Reported EBITDA ({unit})"),
            ("adjusted_ebitda", "Adjusted EBITDA ({unit})"),
            ("ebitda_margin", "EBITDA margin (%; change pp)"),
            ("cfo_reported", "Reported CFO ({unit})"),
            ("capex", "Signed capex ({unit})"),
            ("fcf", "Levered FCF ({unit})"),
        ),
    ),
    _Layout(
        "T1B.2",
        "Balance changes",
        "Measure",
        ("prior", "current", "delta"),
        (
            ("cash_closing", "Closing cash ({unit})"),
            ("total_debt", "Total debt ({unit})"),
            ("net_debt", "Net debt ({unit})"),
        ),
    ),
    _Layout(
        "T1B.3",
        "Evidence and analytical gaps",
        "Assessment",
        ("assessment",),
        (
            ("variance.summary", "Numerical comparison"),
            ("drivers", "Driver evidence"),
            ("guidance", "Guidance evidence"),
            ("comparative.prior-year", "Prior-year comparison"),
            ("comparative.trailing-leverage", "Leverage comparison"),
            ("evidence.inputs", "Selected input evidence"),
            ("scope.limitations", "Scope limitations"),
        ),
    ),
)


def cp1b_layouts(unit: str = "US$ m") -> tuple[_Layout, ...]:
    """The three layouts with the nine money labels stated in ``unit`` (e.g. ``EUR m``)."""
    return tuple(
        replace(layout, rows=tuple((row, label.format(unit=unit)) for row, label in layout.rows))
        for layout in _LAYOUT_TEMPLATES
    )


_CP1B_LAYOUTS = cp1b_layouts()


_bind = Binder("CP-1B").bind


CP1B = BindingMap(
    module_id="CP-1B",
    entries=(
        _bind("T1B.1", "headline-results", "Paired earnings results", slot="cp1b-paired-earnings"),
        _bind(
            "T1B.2", "kpi-changes", "Balance changes", unit="amount", slot="cp1b-balance-changes"
        ),
        _bind(
            "T1B.3",
            "variance-drivers",
            "Numerical comparison",
            slot="cp1b-variance-summary",
            row="variance.summary",
        ),
        _bind("T1B.3", "variance-drivers", "Driver evidence", slot="cp1b-drivers", row="drivers"),
        _bind(
            "T1B.3", "guidance-signals", "Guidance evidence", slot="cp1b-guidance", row="guidance"
        ),
        _bind(
            "T1B.3",
            "limitations",
            "Prior-year comparison",
            slot="cp1b-prior-year-gap",
            row="comparative.prior-year",
        ),
        _bind(
            "T1B.3",
            "limitations",
            "Leverage comparison",
            slot="cp1b-trailing-leverage-gap",
            row="comparative.trailing-leverage",
        ),
        _bind(
            "T1B.3",
            "evidence",
            "Selected input evidence",
            slot="cp1b-input-evidence",
            row="evidence.inputs",
        ),
        _bind(
            "T1B.3",
            "limitations",
            "Scope limitations",
            slot="cp1b-scope-limitations",
            row="scope.limitations",
        ),
    ),
)
