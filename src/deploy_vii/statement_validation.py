"""Full source-statement keys, completeness and independent equation structure."""

import re
import unicodedata
from datetime import date
from decimal import Decimal
from typing import NamedTuple

from deploy_vii.financial_contracts import (
    AccountObservation,
    FinancialBook,
    statement_dimensions,
)
from deploy_vii.model.history import OUTFLOW_METRICS

# r14 CP-1 steps 4-6: missing required entries must remain visible, including
# maintenance/growth capex, interest income and minority interests.
REQUIRED_ITEMS: dict[str, tuple[str, ...]] = {
    "IS": (
        "revenue",
        "cogs",
        "gross_profit",
        "sga",
        "other_operating",
        "ebitda_reported",
        "ebitda_adjusted",
        "depreciation_amortization",
        "ebit",
        "interest_expense_total",
        "interest_expense_cash",
        "interest_income",
        "other_non_operating",
        "pretax_income",
        "income_tax_total",
        "income_tax_cash",
        "net_income",
        "exceptionals",
        "sbc",
    ),
    "CFS": (
        "ocf_before_wc",
        "cfo_ncfo",
        "working_capital_change",
        "capex_maintenance",
        "capex_growth",
        "capex_total",
        "fcf_levered",
        "fcf_unlevered",
        "dividends_paid",
        "acquisitions",
        "disposals",
        "debt_issuance",
        "debt_repayment",
        "equity_issuance",
        "equity_buybacks",
        "net_cash_change",
        "cash_taxes_paid",
        "cash_interest_paid",
    ),
    "BS": (
        "cash_and_equivalents",
        "restricted_cash",
        "short_term_investments",
        "trade_receivables",
        "inventory",
        "other_current_assets",
        "total_current_assets",
        "ppe_net",
        "goodwill",
        "other_intangibles",
        "other_noncurrent_assets",
        "total_assets",
        "short_term_debt",
        "current_portion_long_term_debt",
        "trade_payables",
        "other_current_liabilities",
        "total_current_liabilities",
        "senior_secured_debt",
        "senior_unsecured_debt",
        "subordinated_debt",
        "total_debt",
        "pension_obligations",
        "lease_obligations",
        "other_noncurrent_liabilities",
        "total_liabilities",
        "shareholders_equity",
        "minority_interests",
        "total_equity",
    ),
}
OPTIONAL_ITEMS: dict[str, tuple[str, ...]] = {
    "IS": ("opex_including_da", "operating_lease_cost"),
    "CFS": (
        "investing_cash_flow",
        "financing_cash_flow",
        "fx_cash_effect",
        "opening_cash",
        "closing_cash",
        "net_income",
        "lease_payments_in_financing",
        "interest_paid_in_financing",
    ),
    "BS": (
        "rcf_drawn",
        "rcf_commitment",
        "net_accounts_receivable",
        "accounts_payable",
        "restricted_cash_noncurrent",
    ),
}
# Only identities with the same meaning are linked. IS cash interest/tax are
# deliberately not aliases of the CFS cash-paid observations.
ACCOUNT_LINKS: dict[tuple[str, str], str] = {
    **{
        ("IS", key): key
        for key in (
            "revenue",
            "cogs",
            "gross_profit",
            "depreciation_amortization",
            "ebit",
            "pretax_income",
            "net_income",
            "opex_including_da",
            "operating_lease_cost",
        )
    },
    ("IS", "ebitda_reported"): "ebitda",
    ("IS", "ebitda_adjusted"): "adjusted_ebitda",
    ("IS", "income_tax_total"): "income_tax_expense",
    **{
        ("CFS", key): key
        for key in (
            "cfo_ncfo",
            "working_capital_change",
            "dividends_paid",
            "net_cash_change",
            "cash_taxes_paid",
            "cash_interest_paid",
            "lease_payments_in_financing",
            "interest_paid_in_financing",
        )
    },
    ("CFS", "capex_total"): "capex_and_intangible_investment",
    **{
        ("BS", key): key
        for key in (
            "cash_and_equivalents",
            "inventory",
            "senior_secured_debt",
            "total_debt",
            "rcf_drawn",
            "rcf_commitment",
            "net_accounts_receivable",
            "accounts_payable",
        )
    },
}


def _identity_issues(book: FinancialBook) -> list[str]:
    """Reject circular, duplicate and overlapping arithmetic within one statement."""
    lines = {(r.period_id, r.line_id): r for r in book.statement_lines}
    identities = {(r.period_id, r.target_line_id): r for r in book.statement_identities}
    issues: list[str] = []
    if len(identities) != len(book.statement_identities):
        issues.append("Duplicate statement identity target")
    if len({r.identity_id for r in book.statement_identities}) != len(book.statement_identities):
        issues.append("Duplicate statement identity ID")
    references = 0
    for row in book.statement_identities:
        references += len(row.components)
        target = lines.get((row.period_id, row.target_line_id))
        keys = [(row.period_id, c.line_id) for c in row.components]
        if target is None or any(k not in lines for k in keys):
            issues.append(f"Unknown statement identity line: {row.identity_id}")
            continue
        if target.line_kind == "detail":
            issues.append(
                f"Statement identity target must be a subtotal or total: {row.identity_id}"
            )
        if any(lines[k].statement != target.statement for k in keys):
            issues.append(f"Statement identity mixes statements: {row.identity_id}")
        target_dimensions = statement_dimensions(book, target)
        requires_monetary = target_dimensions.kind != "monetary"
        dimensions_mismatch = False
        for key in keys:
            dimensions = statement_dimensions(book, lines[key])
            requires_monetary |= dimensions.kind != "monetary"
            dimensions_mismatch |= dimensions != target_dimensions
        if requires_monetary:
            issues.append(f"Statement identity requires monetary quantities: {row.identity_id}")
        elif dimensions_mismatch:
            issues.append(f"Statement identity mixes quantity dimensions: {row.identity_id}")
        if len(set(keys)) != len(keys):
            issues.append(f"Duplicate statement identity component: {row.identity_id}")
    if issues:
        return issues
    if references > 20000:
        return ["Statement identities exceed 20000 component references"]
    active: set[tuple[str, str]] = set()
    memo: dict[tuple[str, str], tuple[dict[tuple[str, str], int], int, int]] = {}
    expanded = 0

    def descend(key: tuple[str, str], depth: int) -> tuple[dict[tuple[str, str], int], int, int]:
        nonlocal expanded
        if key in active:
            raise ValueError(f"Cyclic statement identity: {key[0]} {key[1]}")
        cached = memo.get(key)
        if depth > 12 or (cached is not None and depth + cached[1] - 1 > 12):
            raise ValueError("Statement identity nesting exceeds twelve levels")
        if cached is not None:
            return cached
        active.add(key)
        equation = identities.get(key)
        covered: dict[tuple[str, str], int] = {key: 1} if equation is None else {}
        height = 1
        size = 1 if equation is None else 0
        if equation is not None:
            for term in equation.components:
                part, child_height, child_size = descend((key[0], term.line_id), depth + 1)
                height = max(height, 1 + child_height)
                size += child_size
                for leaf, weight in part.items():
                    contribution = weight * term.coefficient
                    prior = covered.get(leaf, 0)
                    if prior * contribution > 0:
                        raise ValueError(
                            f"Overlapping statement identity components: {key[0]} {key[1]}"
                        )
                    covered[leaf] = prior + contribution
        covered = {leaf: weight for leaf, weight in covered.items() if weight}
        if not covered:
            raise ValueError(f"Statement identity has no independent components: {key[0]} {key[1]}")
        expanded += size
        if expanded > 20000:
            raise ValueError("Expanded statement identities exceed 20000 terms")
        active.remove(key)
        result = covered, height, size
        memo[key] = result
        return result

    try:
        for key in identities:
            descend(key, 1)
    except ValueError as error:
        issues.append(str(error))
    return issues


def _signed_outflow_issues(book: FinancialBook) -> list[str]:
    """S12-A02 (user ruling: fail closed): every reader of an `OUTFLOW_METRICS` account takes
    -abs(amount), so a positive `signed` amount on a line linked to one (a printed net refund, say)
    would turn into an outflow unseen. It is refused for the model to repair instead."""
    return [
        f"Positive signed amount on an outflow account: {line.line_id} {line.period_id} "
        f"({line.statement} {line.item_id}, account {metric}) is never flipped; a source that "
        "prints the outflow as a positive magnitude needs `sign_convention: outflow_magnitude` "
        "with `sign_citations`, and a source that prints a net inflow (a refund) needs the value "
        "recorded as status `missing` with a null `amount` and a `reason` saying so"
        for line in book.statement_lines
        if line.sign_convention == "signed"
        and line.value.amount is not None
        and line.value.amount > 0
        and (metric := ACCOUNT_LINKS.get((line.statement, line.item_id))) in OUTFLOW_METRICS
    ]


# User ruling (S12-A02, fail closed): the words by which a label states an inflow, and the "net of"
# clause they may sit in without stating one ("Cash taxes paid, net of refunds received"). The
# clause runs from "net of" (or "net-of") to the bracket that encloses it, a semicolon or the end
# of the label; a bracketed part inside it stays in it.
INFLOW_WORDS = (
    "refund",
    "refunds",
    "refunded",
    "received",
    "receipt",
    "receipts",
    "proceeds",
    "inflow",
    "inflows",
    "reimbursement",
    "reimbursements",
)
_INFLOW = re.compile(rf"\b(?:{'|'.join(INFLOW_WORDS)})\b")
_NET_OF = re.compile(r"\bnet[\s\-\u2010]+of\b(?:[^()\[\];]|\([^()]*\)|\[[^\[\]]*\])*")


def _inflow_word(label: str) -> str | None:
    """The first inflow word a label states outside a "net of" clause, compared case-blind after
    NFKC (full-width brackets and no-break spaces read as their plain forms), or None."""
    text = _NET_OF.sub(" ", unicodedata.normalize("NFKC", label).casefold())
    found = _INFLOW.search(text)
    return None if found is None else found.group()


def _inflow_label_issues(book: FinancialBook) -> list[str]:
    """User ruling (S12-A02, fail closed): `outflow_magnitude` reads -abs(amount), so on a line of
    an `OUTFLOW_METRICS` account whose label states an inflow (a refund, say) it would turn the
    inflow into an outflow unseen. It is refused for the model to repair instead."""
    return [
        f"Outflow magnitude on a label that states an inflow: {line.line_id} {line.period_id} "
        f'({line.statement} {line.item_id}, account {metric}, label word "{word}") is never read '
        "as an outflow; a source that prints the figure negative needs `sign_convention: signed` "
        "with the negative amount, and a source that prints a net inflow (a refund) needs the "
        "value recorded as status `missing` with a null `amount` and a `reason` saying so"
        for line in book.statement_lines
        if line.sign_convention == "outflow_magnitude"
        and (metric := ACCOUNT_LINKS.get((line.statement, line.item_id))) in OUTFLOW_METRICS
        and (word := _inflow_word(line.label)) is not None
    ]


def _withheld_account_issues(book: FinancialBook) -> list[str]:
    """User ruling (S12-A02, fail closed): a `book.accounts` row of an `OUTFLOW_METRICS` account
    is read -abs(amount) and takes precedence over the statement, so an amount beside that
    account's statement line withheld as `missing` (a net inflow such as a refund) would give the
    period the outflow the statement withholds. It is a conflict for the model to repair."""
    withheld = {
        (line.period_id, metric): line
        for line in book.statement_lines
        if line.value.status == "missing"
        and (metric := ACCOUNT_LINKS.get((line.statement, line.item_id))) in OUTFLOW_METRICS
    }
    return [
        f"Account contradicts a withheld statement line: account {account.metric_id} "
        f"{account.period_id} carries an amount while {line.line_id} ({line.statement} "
        f"{line.item_id}) is withheld as `missing` for that period (a net inflow such as a "
        "refund); leave that account row out or give it a null `amount` (status `missing` with a "
        "`reason`), never a figure the statement withholds"
        for account in book.accounts
        if account.value.amount is not None
        and (line := withheld.get((account.period_id, account.metric_id))) is not None
    ]


def statement_issues(  # noqa: C901, PLR0912, PLR0915 - pre-existing (C901 27, 26 branches, 70 statements at base, unchanged)
    book: FinancialBook,
) -> tuple[str, ...]:
    periods = {p.period_id for p in book.periods}
    instant_periods = {p.period_id for p in book.periods if p.period_type == "PERIOD_END"}
    issues: list[str] = []
    seen: set[tuple[str, str]] = set()
    canonical: set[tuple[str, str, str]] = set()
    metadata: dict[str, tuple[object, ...]] = {}
    priorities: dict[tuple[str, int], str] = {}
    end_dates = {p.period_id: p.end_date for p in book.periods}
    balances: dict[tuple[str, date], set[Decimal]] = {}
    for row in book.statement_lines:
        key = row.period_id, row.line_id
        if key in seen or row.period_id not in periods:
            issues.append(
                f"Duplicate statement line or unknown period: {row.line_id} {row.period_id}"
            )
        seen.add(key)
        if row.statement != "BS" and row.period_id in instant_periods:
            issues.append(f"Flow statement cannot use a period-end-only date: {row.line_id}")
        item_key = row.period_id, row.statement, row.item_id
        if item_key in canonical:
            issues.append(f"Duplicate canonical statement item: {row.item_id} {row.period_id}")
        canonical.add(item_key)
        if row.item_id not in (
            *REQUIRED_ITEMS[row.statement],
            *OPTIONAL_ITEMS[row.statement],
        ) and not row.item_id.startswith("other:"):
            issues.append(
                f"Unknown statement item; issuer detail requires other: prefix: {row.item_id}"
            )
        dimensions = statement_dimensions(book, row)
        values = (
            row.statement,
            row.item_id,
            row.label,
            row.display_priority,
            row.line_kind,
            dimensions.kind,
            dimensions.currency,
            dimensions.scale,
        )
        if row.quantity is not None and (
            row.quantity.kind == "monetary" and row.quantity.scale != book.unit
        ):
            issues.append(f"Monetary statement quantity scale differs from book: {row.line_id}")
        if row.line_id in metadata and metadata[row.line_id] != values:
            issues.append(
                f"Changed statement definition requires a distinct line ID: {row.line_id}"
            )
        metadata[row.line_id] = values
        priority_key = row.statement, row.display_priority
        if priority_key in priorities and priorities[priority_key] != row.line_id:
            issues.append(
                f"Duplicate statement display priority: {row.statement} {row.display_priority}"
            )
        priorities[priority_key] = row.line_id
        day = end_dates.get(row.period_id)
        if row.statement == "BS" and day is not None and row.value.amount is not None:
            balances.setdefault((row.item_id, day), set()).add(row.value.amount)
    for (item, day), amounts in balances.items():
        if len(amounts) > 1:
            issues.append(f"Unresolved same-date statement balances: {item} {day}")
    if len(metadata) * len(periods) > 20000:
        issues.append("Expanded statement register exceeds 20000 rows")
    disclosures: set[tuple[str, str]] = set()
    for disclosure_row in book.statement_disclosures:
        key = disclosure_row.period_id, disclosure_row.statement
        if key in disclosures or disclosure_row.period_id not in periods:
            issues.append(f"Duplicate statement disclosure or unknown period: {key}")
        disclosures.add(key)
        populated = any(
            r.period_id == disclosure_row.period_id and r.statement == disclosure_row.statement
            for r in book.statement_lines
        )
        if populated and disclosure_row.disclosure.status in {"not_disclosed", "not_applicable"}:
            issues.append(f"Statement disclosure contradicts populated statement: {key}")
    linked: dict[tuple[str, str], set[object]] = {}
    for account in book.accounts:
        amount = account.value.amount
        if amount is not None:
            normalized = (
                amount.copy_abs().copy_negate()
                if account_outflow(book, account.period_id, account.metric_id)
                else amount
            )
            linked.setdefault((account.period_id, account.metric_id), set()).add(normalized)
    for line in book.statement_lines:
        metric = ACCOUNT_LINKS.get((line.statement, line.item_id))
        amount = line.value.amount
        if metric is not None and line.quantity is not None and line.quantity.kind != "monetary":
            issues.append(
                "Canonical account link requires monetary quantity: "
                f"{line.item_id} {line.period_id}"
            )
        if metric is not None and amount is not None:
            normalized = (
                amount.copy_abs().copy_negate()
                if account_outflow(book, line.period_id, metric)
                else amount
            )
            linked.setdefault((line.period_id, metric), set()).add(normalized)
    for (period_id, metric), linked_values in linked.items():
        if len(linked_values) > 1:
            issues.append(
                f"Statement/account disagreement requires explicit conflict: {metric} {period_id}"
            )
    canonical_accounts = {(r.period_id, r.metric_id): r.value for r in book.accounts}
    for source in statement_accounts(book):
        canonical_value = canonical_accounts.get((source.period_id, source.metric_id))
        if (
            source.value.status == "conflicting"
            and canonical_value is not None
            and canonical_value.amount is not None
        ):
            issues.append(
                f"Unresolved source statement conflict: {source.metric_id} {source.period_id}"
            )
    issues.extend(_identity_issues(book))
    # The source bridge is a calculation, never a renamed SG&A observation.
    from deploy_vii.expense_composition import opex_composition

    for period_id in periods:
        composition = opex_composition(book, period_id)
        if composition is not None and any(
            amount != composition.value
            for amount in linked.get((period_id, "opex_including_da"), ())
        ):
            issues.append(f"OPEX must include SG&A and intangible amortization: {period_id}")
    return (
        *issues,
        *_signed_outflow_issues(book),
        *_inflow_label_issues(book),
        *_withheld_account_issues(book),
    )


class _AccountIndex(NamedTuple):
    effective: tuple[AccountObservation, ...]
    by_metric: dict[str, tuple[AccountObservation, ...]]
    outflow_magnitude: frozenset[tuple[str, str]]


_last_index: tuple[FinancialBook, _AccountIndex] | None = None


def _account_index(book: FinancialBook) -> _AccountIndex:
    """The book's effective accounts, by metric, and its cited outflow-magnitude statement lines
    as `(period_id, metric)`. A book is frozen, so the index of the last book asked about is kept:
    the reconciliation asks per period and metric. The kept pair is read once, so a thread that
    stores another book's index meanwhile cannot hand that index to this book."""
    global _last_index
    last = _last_index
    if last is not None and last[0] is book:
        return last[1]
    result = list(book.accounts)
    present = {(r.period_id, r.metric_id) for r in result}
    for row in statement_accounts(book):
        if (row.period_id, row.metric_id) not in present:
            result.append(row)
            present.add((row.period_id, row.metric_id))
    by_metric: dict[str, list[AccountObservation]] = {}
    for account in result:
        by_metric.setdefault(account.metric_id, []).append(account)
    outflow = frozenset(
        (row.period_id, metric)
        for row in book.statement_lines
        if row.sign_convention == "outflow_magnitude"
        and (metric := ACCOUNT_LINKS.get((row.statement, row.item_id))) is not None
    )
    index = _AccountIndex(tuple(result), {m: tuple(rows) for m, rows in by_metric.items()}, outflow)
    _last_index = (book, index)
    return index


def effective_accounts(book: FinancialBook) -> tuple[AccountObservation, ...]:
    """Fill only absent canonical accounts from exactly equivalent statement items.

    Explicit accounts, including explicit gaps/conflicts, take precedence. The
    original source Observation stays intact; the Model owns sign normalization.
    """
    return _account_index(book).effective


def metric_accounts(book: FinancialBook, metric: str) -> tuple[AccountObservation, ...]:
    """The effective accounts of one metric, in `effective_accounts` order."""
    return _account_index(book).by_metric.get(metric, ())


def statement_accounts(book: FinancialBook) -> tuple[AccountObservation, ...]:
    return tuple(
        AccountObservation(metric_id=metric, period_id=row.period_id, value=row.value)
        for row in book.statement_lines
        if (metric := ACCOUNT_LINKS.get((row.statement, row.item_id))) is not None
    )


def account_outflow(book: FinancialBook, period_id: str, metric: str) -> bool:
    """Canonical outflow semantics or an explicitly cited source presentation."""
    return (
        metric in OUTFLOW_METRICS or (period_id, metric) in _account_index(book).outflow_magnitude
    )
