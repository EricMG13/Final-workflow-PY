"""S12-C07 / S13-C11: one Model or KPI build validates the review once and reuses its registers."""

import json
from typing import Any

import pytest
import test_financial_workflow as fw

import deploy_vii.financial_adapter as adapter
from deploy_vii.canonical_kpis import canonical_kpis
from deploy_vii.financial_adapter import kernel_registers
from deploy_vii.financial_contracts import FinancialReview
from deploy_vii.financial_model import model_report
from deploy_vii.financial_periods import historical_report
from deploy_vii.period_reconciliation import reconcile_periods

SCOPE = {
    "currency": "USD",
    "unit": "MILLIONS",
    "accounting_basis": "IFRS",
    "entity_perimeter": "consolidated group",
}


@pytest.fixture(scope="module")
def case() -> tuple[Any, FinancialReview, str]:
    pack = fw.make_pack()
    doc = fw.financials(pack)["financial"]
    doc.pop("limitations", None)
    for book in doc["books"]:
        book.update(SCOPE)
        for period in book["periods"]:
            period.update(SCOPE)
    review = FinancialReview.model_validate_json(
        json.dumps({**doc, "pack_sha256": pack.content_hash()})
    )
    return pack, review, review.books[0].book_id


def test_model_report_and_kpis_validate_the_review_once(case, monkeypatch) -> None:
    # By hand: each build needs the registers once (the review is validated inside
    # kernel_registers); before the change model_report and canonical_kpis built them twice.
    pack, review, book_id = case
    calls: list[int] = []
    real = adapter.validate_financial_review
    monkeypatch.setattr(
        adapter, "validate_financial_review", lambda *a: calls.append(1) or real(*a)
    )
    model_report(pack, review, book_id)
    assert len(calls) == 1
    canonical_kpis(pack, review, book_id)
    assert len(calls) == 2


def test_passed_registers_and_history_equal_the_ones_built_inside(case) -> None:
    pack, review, book_id = case
    regs = kernel_registers(pack, review, book_id)
    history = historical_report(pack, review, book_id)
    assert historical_report(pack, review, book_id, regs=regs) == history
    assert canonical_kpis(pack, review, book_id, regs=regs) == canonical_kpis(pack, review, book_id)
    assert reconcile_periods(pack, review, book_id, historical=history) == reconcile_periods(
        pack, review, book_id
    )
