"""Review S02 (statement validation): the OPEX-composition issues follow the book's period
order in every process (they iterated a set of period ids, so their order followed the hash
seed), and the precomputed outflow lookups agree with `account_outflow`."""

import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_statement_quantity_outputs as fx

from deploy_vii import expense_composition
from deploy_vii.financial_contracts import AccountObservation, FinancialBook, Observation
from deploy_vii.statement_validation import account_outflow, statement_issues

ROOT = Path(__file__).resolve().parent.parent


def _book() -> FinancialBook:
    book = fx._book()
    accounts = tuple(
        AccountObservation(
            metric_id="opex_including_da",
            period_id=period.period_id,
            value=Observation(
                observation_id=f"obs:opex:{period.period_id}",
                status="known",
                amount=Decimal(-100),
                citations=book.periods[0].citations,
            ),
        )
        for period in book.periods
    )
    return book.model_copy(update={"accounts": accounts})


def _opex_issues(book: FinancialBook) -> list[str]:
    return [issue for issue in statement_issues(book) if issue.startswith("OPEX must include")]


def test_opex_issues_follow_the_book_period_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        expense_composition, "opex_composition", lambda _book, _pid: SimpleNamespace(value=1)
    )
    book = _book()
    assert len(book.periods) >= 2
    assert _opex_issues(book) == [
        f"OPEX must include SG&A and intangible amortization: {period.period_id}"
        for period in book.periods
    ]


SCRIPT = """
import sys
from types import SimpleNamespace
sys.path[:0] = [{tests!r}]
import test_review_S02_statement_validation as t
from deploy_vii import expense_composition
expense_composition.opex_composition = lambda _b, _p: SimpleNamespace(value=1)
print("|".join(t._opex_issues(t._book())))
"""


def test_opex_issue_order_does_not_follow_the_hash_seed() -> None:
    script = SCRIPT.format(tests=str(ROOT / "tests"))
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT)])}
    outputs = {
        subprocess.run(
            [sys.executable, "-c", script],
            env={**env, "PYTHONHASHSEED": str(seed)},
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        ).stdout
        for seed in range(6)
    }
    assert len(outputs) == 1


def test_account_outflow_is_canonical_or_an_explicit_line() -> None:
    book = _book()
    period_id = book.periods[0].period_id
    assert account_outflow(book, period_id, "opex_including_da")
    assert not account_outflow(book, period_id, "revenue")
