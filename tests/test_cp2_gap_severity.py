"""S06-A06: a Critical CP-1A row is restated only by a CP-2 gaps row of severity Critical.

Before the fix a gaps row of severity Minor citing the Critical CP-1A gap counted as its
restatement, so CP-2's own limitation read "Gap (Minor): ..." for a Critical upstream gap.
"""

from datetime import date

import pytest
import test_engine_blank_text as tb

from deploy_vii import cp2_synthesis as c2
from deploy_vii.contracts import Fact, Input, Module, ReportTable, TableColumn, TableRow

PLAIN = "Leverage is tight."


def _fact(table: str, row: str, field: str, text: str) -> Fact:
    return Fact(
        fact_id=f"{table}.{row}.{field}",
        label=field,
        table_id=table,
        row_id=row,
        field=field,
        text=text,
    )


def _table(table_id: str, row_id: str, label: str, fields: tuple[str, str]) -> ReportTable:
    return ReportTable(
        table_id=table_id,
        title=table_id,
        row_header="Item",
        columns=tuple(TableColumn(field=f, label=f) for f in fields),
        rows=(
            TableRow(
                row_id=row_id,
                label=label,
                fact_ids=tuple(f"{table_id}.{row_id}.{f}" for f in fields),
            ),
        ),
    )


def _upstream(readiness: str = "READY") -> c2.Upstream:
    """CP-1A with one Critical gaps_ledger row g01 and CP-1A's readiness judgment of CP-2."""
    facts = (
        _fact("gaps_ledger", "g01", "gap", "No debt maturity schedule"),
        _fact("gaps_ledger", "g01", "severity", "Critical"),
        _fact("downstream_readiness", "r01", "status", readiness),
        _fact("downstream_readiness", "r01", "gap", "none"),
    )
    cp1a = Module(
        run_id="run-1",
        issuer_id="acme",
        as_of=date(2026, 1, 1),
        module_id="CP-1A",
        facts=facts,
        tables=(
            _table("gaps_ledger", "g01", "Gap 1", ("gap", "severity")),
            _table("downstream_readiness", "r01", "CP-2", ("status", "gap")),
        ),
    )
    cp1 = tb._module("CP-1")
    bound = (
        Input(input_id="CP-1", sha256=cp1.content_hash()),
        Input(input_id="CP-1A", sha256=cp1a.content_hash()),
    )
    return c2.Upstream(bound=bound, current=bound, cp1=cp1, cp1a=cp1a, inherited=())


def _submission(*gaps: tuple[str, tuple[str, ...]]) -> c2.CreditSynthesisSubmission:
    refs = ("gaps_ledger.g01",)
    return c2.CreditSynthesisSubmission(
        assessment=c2.Assessment(
            rationale=PLAIN,
            category="Analyst Interpretation",
            confidence="Medium",
            cp1a_refs=refs,
            limitation=None,
        ),
        thesis=c2.Thesis(
            text=PLAIN, category="Analyst Interpretation", cp1a_refs=refs, limitation=None
        ),
        strengths=(),
        weaknesses=(),
        key_findings=(c2.Finding(text=PLAIN, cp1a_refs=refs),),
        risks=(),
        gaps=tuple(
            c2.SynthesisGap(
                gap="No maturity schedule in the pack",
                why_it_matters=PLAIN,
                affected_analysis=PLAIN,
                severity=severity,  # type: ignore[arg-type]
                action=PLAIN,
                cp1a_refs=cited,
            )
            for severity, cited in gaps
        ),
    )


ISSUE = (
    "gaps: restate the Critical CP-1A gap gaps_ledger.g01 in a gaps row of severity Critical "
    "that cites it"
)


@pytest.mark.parametrize("severity", ["Minor", "Material"])
def test_a_downgraded_restatement_of_a_critical_gap_is_refused(severity: str) -> None:
    up = _upstream()
    sub = _submission((severity, ("gaps_ledger.g01",)))
    assert c2.validate_credit_synthesis(tb._pack(), sub, up) == (ISSUE,)


def test_a_critical_restatement_composes_with_its_severity() -> None:
    """Hand-derived: one Critical gaps row citing g01; the own limitation is
    'Gap (Critical): No maturity schedule in the pack'."""
    up = _upstream()
    sub = _submission(("Minor", ("gaps_ledger.g01",)), ("Critical", ("gaps_ledger.g01",)))
    assert c2.validate_credit_synthesis(tb._pack(), sub, up) == ()
    report = c2.credit_synthesis(tb._pack(), sub, up)
    assert "Gap (Critical): No maturity schedule in the pack" in report.limitations


def test_a_readiness_signal_is_restated_by_a_row_of_any_severity() -> None:
    """A non-READY readiness judgment carries no severity, so a Minor row restates it; the
    Critical gap g01 still needs its Critical row."""
    up = _upstream("READY WITH LIMITATIONS")
    refs = ("gaps_ledger.g01",)
    sub = _submission(("Critical", refs), ("Minor", ("downstream_readiness.r01",)))
    assert c2.validate_credit_synthesis(tb._pack(), sub, up) == ()
