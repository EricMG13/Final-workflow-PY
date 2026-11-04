"""CZR with the filing's printed cash scope declared: both NCF_CASH_MOVEMENT checks agree.

The recorded partial submission is loaded and extended in memory (the "restricted and escrow cash
included in other long-term assets" balance, one scope declaration per flow period, the two pages
that print the balance, and the unit maps of the four statement units it predates, CP1H-R23.11);
nothing under `cases/**` is edited. The run still stops at the calculation gate for the other open
checks, so the reconciliation is captured as the audit builds it.
"""

import copy
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from czr_runs import CASE, czr_closed

from deploy_vii import canonical_audit
from deploy_vii.financial_reconciliation import (
    Reconciliation,
    ReconciliationReport,
    reconcile_financials,
)
from deploy_workflow import owner_workflow as ow

NONCURRENT = "bs-restricted-and-escrow-cash-included-in-other-long-term-assets-net"
BOTH = ["restricted_cash", "restricted_cash_noncurrent"]
K_QUOTE = "Restricted and escrow cash included in other long-term assets, net | 12 | 55 | 16"
Q_QUOTE = "Restricted and escrow cash included in other long-term assets, net | 16 | 19"
# period -> (amount, source id, locator, quote)
BALANCES = {
    "bs-2025-12-31": ("12", "czr-fy2025-10k", "page:61", K_QUOTE),
    "bs-2024-12-31": ("55", "czr-fy2025-10k", "page:61", K_QUOTE),
    "bs-2026-06-30": ("16", "czr-q2-2026-10q", "page:10", Q_QUOTE),
}


TENK, TENQ = "czr-fy2025-10k", "czr-q2-2026-10q"
FY = ["fy-2025", "fy-2024", "fy-2023"]
H1 = ["h1-2026", "h1-2025"]
Q_IS = ["q2-2026", "q2-2025", "h1-2026", "h1-2025"]
# The four statement units the recorded submission predates (CP1H-R23.11), as the extractor reads
# them: (source, unit tag, locator, statement, one period id per printed column, row numbers).
# Every row maps to an `other:` item, so none repeats a canonical (period, statement, item).
NEW_UNITS = [
    (TENK, "k57", "page:57", "IS", FY, (5, 6, 7, 8, 10, 11, 12)),
    (TENK, "k61", "page:61", "CFS", FY, (4, 5, 6, 7, 9, 10, 11, 13, 14, 15)),
    (TENQ, "q5", "page:5", "IS", Q_IS, (6, 7, 8, 9, 10, 11)),
    (TENQ, "q10", "page:10", "CFS", H1, (4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16)),
]


def _unit_map(source: str, tag: str, locator: str, kind: str, columns: list[str], rows: Any) -> Any:
    return {
        "source_id": source,
        "locator": locator,
        "book_id": "consolidated",
        "statement": kind,
        "columns": columns,
        "rows": [
            {
                "row": row,
                "line_id": f"t21c-{tag}-{row}",
                "item_id": f"other:t21c-{tag}-{row}",
                "line_kind": "detail",
                "sign_convention": "signed",
            }
            for row in rows
        ],
    }


def _declared(data: dict[str, Any]) -> dict[str, Any]:
    stage = next(s for s in data["stages"] if s["step"] == "financials")
    book = stage["submission"]["financial"]["books"][0]
    shas = {
        c["source_id"]: c["source_sha256"]
        for row in book["statement_lines"]
        for c in row["value"]["citations"]
    }
    top = max(row["display_priority"] for row in book["statement_lines"])
    for period, (amount, source, locator, quote) in BALANCES.items():
        citation = {
            "source_id": source,
            "source_sha256": shas[source],
            "locator": locator,
            "quote": quote,
        }
        book["statement_lines"].append(
            {
                "line_id": NONCURRENT,
                "statement": "BS",
                "item_id": "restricted_cash_noncurrent",
                "label": "Restricted and escrow cash included in other long-term assets, net",
                "period_id": period,
                "display_priority": top + 1,
                "line_kind": "detail",
                "value": {
                    "observation_id": f"{NONCURRENT}--{period}",
                    "status": "known",
                    "amount": amount,
                    "citations": [citation],
                },
            }
        )
    for period in ("fy-2025", "h1-2026"):
        line = next(
            r
            for r in book["statement_lines"]
            if r["item_id"] == "net_cash_change" and r["period_id"] == period
        )
        citation = line["value"]["citations"][0]
        book["cash_movement_bridges"].append(
            {
                "bridge_id": f"bridge-{period}",
                "period_id": period,
                "components": [],
                "explanation": "No FX or perimeter adjustment is printed in the cash flow statement.",
                "citations": [citation],
                "cash_scope": {"items": BOTH, "citations": [citation]},
            }
        )
    stage["submission"]["unit_maps"] = [_unit_map(*unit) for unit in NEW_UNITS]
    stage["calls"] += [
        {
            "tool": "extract_statements",
            "arguments": {"source_id": TENK, "locators": ["page:57", "page:61"]},
        },
        {
            "tool": "extract_statements",
            "arguments": {"source_id": TENQ, "locators": ["page:5", "page:10"]},
        },
        {
            "tool": "read_pages",
            "arguments": {"source_id": "czr-fy2025-10k", "first_page": 61, "last_page": 61},
        },
        {
            "tool": "read_pages",
            "arguments": {"source_id": "czr-q2-2026-10q", "first_page": 10, "last_page": 10},
        },
    ]
    return data


def test_czr_cash_movement_agrees_with_the_declared_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _declared(copy.deepcopy(json.loads((CASE / "submissions-partial.json").read_text())))
    path = tmp_path / "submissions.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    captured: list[ReconciliationReport] = []

    def spy(*args: Any, **kwargs: Any) -> ReconciliationReport:
        report = reconcile_financials(*args, **kwargs)
        captured.append(report)
        return report

    monkeypatch.setattr(canonical_audit, "reconcile_financials", spy)
    with pytest.raises(RuntimeError):
        czr_closed(tmp_path / "run", path)
    assert captured, "the audit never reconciled the financials"
    checks: dict[str, Reconciliation] = {
        c.period_id: c for c in captured[-1].checks if c.check_type == "NCF_CASH_MOVEMENT"
    }
    for period, calculated in (("fy-2025", Decimal(-32)), ("h1-2026", Decimal(93))):
        check = checks[period]
        assert (check.status, check.calculated_value, check.difference) == (
            "PASS",
            calculated,
            Decimal(0),
        )


def test_the_expansion_leaves_the_reconciliation_rows_to_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # R23.22: k61 and q10 rows 4-7 sit under the cash reconciliation caption that names the
    # balance sheet. The expansion, like the gate, leaves them with `other_statement` and
    # composes no line for them.
    data = _declared(copy.deepcopy(json.loads((CASE / "submissions-partial.json").read_text())))
    path = tmp_path / "submissions.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    seen: list[Any] = []
    real = ow.expand_unit_maps

    def spy(*args: Any, **kwargs: Any) -> Any:
        expansion = real(*args, **kwargs)
        seen.append(expansion)
        return expansion

    monkeypatch.setattr(ow, "expand_unit_maps", spy)
    with pytest.raises(RuntimeError):
        czr_closed(tmp_path / "run", path)
    expansions = [e for e in seen if e.notes]
    assert expansions, "the expansion never ran on a payload with unit maps"
    notes = expansions[-1].notes
    line_ids = {
        line["line_id"]
        for book in json.loads(expansions[-1].payload)["financial"]["books"]
        for line in book["statement_lines"]
    }
    for source, tag, locator in ((TENK, "k61", "page:61"), (TENQ, "q10", "page:10")):
        for row in (4, 5, 6, 7):
            pattern = rf"{source} {locator}: row {row} .* is left to you \(other_statement\)"
            assert any(re.search(pattern, note) for note in notes), (tag, row)
            assert f"t21c-{tag}-{row}" not in line_ids, (tag, row)
