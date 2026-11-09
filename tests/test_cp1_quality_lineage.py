"""CP-1 QA lineage ceilings and module status, from the module's own registers only.

Expected values are hand-derived from the docstring rule of `cp1_quality._lineage_basis` (an
absent calculated amount, or a check that could not be computed or blocks, is missing evidence)
and the QA ceiling table in METHODOLOGY (missing -> Insufficient Information, weight 0;
calculation -> Calculated, weight 9), not from the code under test.
"""

import hashlib
from decimal import Decimal

import pytest

from deploy_vii.cp1_quality import _lineage_basis, _module_status
from deploy_vii.financial_reconciliation import Reconciliation, ReconciliationTerm
from deploy_vii.narrative import EvidenceRecord, NarrativeReport
from deploy_vii.period_reconciliation import PeriodCheck, PeriodTerm

H = hashlib.sha256(b"x").hexdigest()


def _term(amount: str | None) -> ReconciliationTerm:
    return ReconciliationTerm(
        label="Reported EBITDA",
        observation_id=None,
        original_amount=None,
        amount=None if amount is None else Decimal(amount),
        reason="Not reported in the source" if amount is None else None,
        citations=(),
    )


def _check(status: str, calculated: str | None) -> EvidenceRecord:
    check = Reconciliation(
        check_id="chk-ebitda-bridge-fy2025",
        period_id="fy-2025",
        check_type="EBITDA_BRIDGE",
        metric_id="ebitda",
        reported=_term(None),
        components=(_term(calculated),),
        reported_value=None,
        calculated_value=None if calculated is None else Decimal(calculated),
        difference=None,
        tolerance=None,
        status=status,
        formula="EBITDA = operating profit + D&A",
        explanation="Reported value or independent components are unavailable",
        context_citations=(),
    )
    return EvidenceRecord(
        evidence_id="narrative-evidence-source-check-x",
        kind="source_check",
        reference=check.check_id,
        artifact_sha256=H,
        record_sha256=check.content_hash(),
        record_json=check.model_dump_json(),
        citations=(),
    )


@pytest.mark.parametrize(
    ("status", "calculated", "expected"),
    [
        # No calculated amount: nothing was calculated, so the lineage is missing evidence.
        ("BLOCK", None, "missing"),
        ("WARN", None, "missing"),
        # A computed check that blocks disagrees with its reported value: conflicting evidence.
        ("BLOCK", "120", "missing"),
        # A computed check that passes (or warns within its own rule) is a Python calculation.
        ("PASS", "120", "calculation"),
        ("WARN", "120", "calculation"),
    ],
)
def test_a_check_caps_at_calculated_only_when_it_computed_and_does_not_block(
    status: str, calculated: str | None, expected: str
) -> None:
    assert _lineage_basis(_check(status, calculated)) == expected


def _period_check(status: str, calculated: str | None) -> EvidenceRecord:
    term = PeriodTerm(
        label="FY from quarters",
        value_id=None,
        amount=None,
        observation_ids=(),
        citations=(),
        reason="Not reported",
    )
    check = PeriodCheck(
        check_id="chk-fy-quarters-fy2025",
        construction_id="con-fy-2025",
        check_type="FY_QUARTERS",
        metric_id="revenue",
        reported=term,
        components=(term,),
        calculated_value=None if calculated is None else Decimal(calculated),
        difference=None,
        tolerance=None,
        independent=True,
        shared_observation_ids=(),
        status=status,
        formula="FY = Q1 + Q2 + Q3 + Q4",
        explanation="Quarters are unavailable",
        context_citations=(),
    )
    return EvidenceRecord(
        evidence_id="narrative-evidence-period-check-x",
        kind="period_check",
        reference=check.check_id,
        artifact_sha256=H,
        record_sha256=check.content_hash(),
        record_json=check.model_dump_json(),
        citations=(),
    )


@pytest.mark.parametrize(
    ("status", "calculated", "expected"),
    [
        ("BLOCK", None, "missing"),
        ("BLOCK", "400", "missing"),
        ("WARN", None, "missing"),
        ("PASS", "400", "calculation"),
        ("WARN", "400", "calculation"),
        # A calculated amount of zero is a computed zero, not a missing amount.
        ("PASS", "0", "calculation"),
    ],
)
def test_a_period_check_follows_the_same_rule_as_a_source_check(
    status: str, calculated: str | None, expected: str
) -> None:
    assert _lineage_basis(_period_check(status, calculated)) == expected


def test_a_source_check_with_a_calculated_zero_is_a_calculation() -> None:
    assert _lineage_basis(_check("PASS", "0")) == "calculation"


# The four scope disclaimers canonical_narrative writes on every report (narrative.py), copied
# by hand: they describe what structural binding cannot prove, not a finding of this module.
DISCLAIMERS = (
    (
        "Structural evidence binding cannot prove issuer-specific meaning, materiality or "
        "reasoning quality"
    ),
    "All numeric evidence is supplied by prior registers; prose still requires semantic review",
    (
        "Funding classification is an analyst synthesis over prior balance-sheet rows, "
        "not new extraction"
    ),
    "No consumer readiness, analytical qualification or completed Module acceptance is inferred",
)


@pytest.mark.parametrize(
    ("status", "gaps", "expected"),
    [
        # A clean narrative (no gaps of its own) with only the disclaimers is complete: QA may
        # then pass on its score (decision 0007: only own findings restrict).
        ("candidate", 0, "complete"),
        # One own gap (e.g. a stated review limitation) restricts; a BLOCK gap blocks.
        ("restricted", 1, "restricted"),
        ("blocked", 1, "blocked"),
        # Fail closed: a "candidate" status that still carries a gap is not complete.
        ("candidate", 1, "restricted"),
    ],
)
def test_module_status_follows_own_gaps_not_the_fixed_disclaimers(
    status: str, gaps: int, expected: str
) -> None:
    report = NarrativeReport.model_construct(
        status=status, gaps=(object(),) * gaps, limitations=DISCLAIMERS
    )
    assert _module_status(report) == expected
