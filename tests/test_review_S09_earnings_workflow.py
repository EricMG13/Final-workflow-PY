"""S09 review regressions for the earnings receipt path (`deploy_workflow.earnings_workflow`).

* The financials gate is the financial workflow's own current gate: an IFRS "statement of
  financial position" unit's balance-sheet lines are covered by BS lines, not refused because a
  stale caption copy found no statement for them.
* The composer's `unsupported_pair` refusal is charged to the submission as an issue, like the
  delta core's codes, instead of escaping `_stage_validation` as an exception.
* The composer's missing-prior branch states "Requested FY{y} comparison basis is absent" only
  for an FY current period.
Expected values are literals.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import o2_case
import pytest
from test_line_locators import FIN, _line_spans, _with_spans
from test_owner_cp1b import _producer, _with_opening

from deploy_vii.live.tools import PackTools
from deploy_workflow import earnings_workflow as ew
from deploy_workflow import financial_workflow as fw
from deploy_workflow.earnings import build_earnings_delta
from deploy_workflow.owners import cp1b
from deploy_workflow.workflow import SourceEvidence

UNCOVERED = "Uncovered extracted statement line: "
CASH = "Cash and cash equivalents"


def _quarter(pid: str, quarter: int, start: date, end: date) -> SimpleNamespace:
    return SimpleNamespace(
        period_id=pid,
        period_type="QUARTER",
        fiscal_year="2025",
        fiscal_quarter=quarter,
        start_date=start,
        end_date=end,
    )


def _bs_line(pid: str, amount: Decimal) -> SimpleNamespace:
    cite = SimpleNamespace(source_id=FIN, locator="line:3", quote=f"{CASH}  10  12")
    return SimpleNamespace(
        period_id=pid,
        statement="BS",
        label=CASH,
        value=SimpleNamespace(amount=amount, citations=[cite]),
        quantity=None,
        label_parts=None,
    )


def _financials_issues(monkeypatch: pytest.MonkeyPatch, title: str) -> list[str]:
    """The earnings financials gate over one unit `title` / two quarter columns / one cash row,
    with a submission holding the row's BS line in each quarter."""
    pack = _with_spans(_line_spans([title, "Period  Q1 2025  Q2 2025", f"{CASH}  10  12"]))
    financial = next(s for s in pack.sources if s.source_id == FIN)
    tools = PackTools(pack, sources=(FIN,))
    for locator in fw._statement_units(financial.spans):
        tools.extract_statements({"source_id": FIN, "locators": [locator]})
    evidence = SourceEvidence(
        read=tuple((FIN, span.locator) for span in financial.spans),
        extracted=tuple(sorted(tools.extracted)),
    )
    context = o2_case.payload_for("source_context")
    store = SimpleNamespace(
        read=lambda: SimpleNamespace(
            attempts=[SimpleNamespace(ticket_id="t", steps=[SimpleNamespace(payload_sha256="c")])]
        ),
        payload=lambda _sha: context,
        pack=lambda: pack,
    )
    book = SimpleNamespace(
        periods=[
            _quarter("q1-2025", 1, date(2025, 1, 1), date(2025, 3, 31)),
            _quarter("q2-2025", 2, date(2025, 4, 1), date(2025, 6, 30)),
        ],
        statement_lines=[_bs_line("q1-2025", Decimal(10)), _bs_line("q2-2025", Decimal(12))],
    )
    submission = SimpleNamespace(
        model_validate_json=lambda _s: SimpleNamespace(financial=SimpleNamespace(books=[book]))
    )
    for module in (fw, ew):
        monkeypatch.setattr(module, "FinancialSubmission", submission)
    binding = SimpleNamespace(step_id="financials", ticket_id="t")
    return list(ew._source_issues(cast(Any, store), cast(Any, binding), "x", evidence, ()))


@pytest.mark.parametrize(
    "title",
    ["Consolidated statement of financial position", "Consolidated Balance Sheets"],
)
def test_balance_sheet_lines_are_covered_by_bs_lines(
    monkeypatch: pytest.MonkeyPatch, title: str
) -> None:
    issues = _financials_issues(monkeypatch, title)
    assert not [i for i in issues if i.startswith(UNCOVERED)], issues


def test_a_wrong_statement_is_still_uncovered(monkeypatch: pytest.MonkeyPatch) -> None:
    issues = _financials_issues(monkeypatch, "Consolidated statements of operations")
    assert [i for i in issues if i.startswith(UNCOVERED)] == [
        f"{UNCOVERED}{FIN} line:1-3 line 3; statement: q1-2025 cites this row as BS, expected IS"
    ]


def test_stage_validation_charges_unsupported_pair_as_an_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refused(*_args: object) -> None:
        raise ValueError("unsupported_pair")

    monkeypatch.setattr(ew, "_owner_stage", refused)
    validation = ew._stage_validation(cast(Any, None), cast(Any, None))
    assert validation.issues == ("unsupported_pair",) and validation.output is None


def test_stage_validation_still_raises_its_own_defects(monkeypatch: pytest.MonkeyPatch) -> None:
    def defect(*_args: object) -> None:
        raise ValueError("composer arithmetic defect")

    monkeypatch.setattr(ew, "_owner_stage", defect)
    with pytest.raises(ValueError, match="composer arithmetic defect"):
        ew._stage_validation(cast(Any, None), cast(Any, None))


def test_the_missing_prior_claim_needs_an_fy_current_period() -> None:
    producer = _with_opening(_producer())
    report = build_earnings_delta(cp1b.cp1_view(producer), "fy-2024", "fy-2025")
    assert report.prior_basis_id is None
    ew._require_register_claims(producer, report)  # the pinned gap pair: its claims are true
    quarter = replace(report, current_period_id="q4-2025")
    with pytest.raises(ValueError, match="^unsupported_pair$"):
        ew._require_register_claims(producer, quarter)


def test_an_unknown_owner_read_digest_is_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stored intent naming an owner read the audit no longer holds (deleted or altered) is
    tamper: `identity_mismatch`, never a bare KeyError escaping `_stage_validation`."""
    review = SimpleNamespace(prior_period_id="q3-2025", current_period_id="q4-2025")
    participation = SimpleNamespace(
        session_id="session-1",
        call_ids=("call-1",),
        successful_call_ids=("call-1",),
        content_hash=lambda: "p" * 64,
    )
    envelope = SimpleNamespace(
        binding="binding",
        review=review,
        raw_review_sha256="r" * 64,
        participation=participation,
        content_hash=lambda: "e" * 64,
    )
    intent = SimpleNamespace(
        binding=SimpleNamespace(
            stored_payload_sha256="e" * 64,
            binding="binding",
            owner_session_id="session-1",
            participation_sha256="p" * 64,
            call_ids=("call-1",),
            successful_call_ids=("call-1",),
            input_read_hashes=("0" * 64,),
        )
    )
    records = {
        "owner-sessions": (SimpleNamespace(session_id="session-1"),),
        "owner-calls": (),
        "intents": (intent,),
        "owner-reads": (),
    }
    store = SimpleNamespace(pack=lambda: None)
    monkeypatch.setattr(
        ew, "_historical", lambda *_a: SimpleNamespace(read=lambda: SimpleNamespace(run=None))
    )
    monkeypatch.setattr(ew, "_case_parameters", lambda _run: ("E-QOQ-FLAT", "q3-2025", "q4-2025"))
    monkeypatch.setattr(ew, "_raw", lambda *_a: b"{}")
    monkeypatch.setattr(
        ew, "EarningsDeltaReview", SimpleNamespace(model_validate_json=lambda _raw: review)
    )
    monkeypatch.setattr(ew, "_full_cp1", lambda *_a: (None, None))
    monkeypatch.setattr(ew, "build_earnings_delta_in", lambda *_a, **_k: None)
    monkeypatch.setattr(ew, "_run_currency", lambda *_a: "USD")
    monkeypatch.setattr(ew, "_records", lambda _store, kind, _model: records[kind])
    validation = ew._stage_validation(cast(Any, store), cast(Any, envelope))
    assert validation.issues == ("identity_mismatch",)
