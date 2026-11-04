"""Frozen CP-1 quantity dimensions and legacy statement-line compatibility."""

import hashlib
import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_cash_scope import book as cash_scope_book

from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.contracts import Citation, Run, Source, Span
from deploy_vii.financial_contracts import (
    CashMovementBridge,
    Disclosure,
    EffectiveStatementDimensions,
    FinancialBook,
    FinancialPeriod,
    FinancialReview,
    Observation,
    StatementContribution,
    StatementIdentity,
    StatementLabelPart,
    StatementLine,
    StatementQuantity,
    statement_dimensions,
)
from deploy_vii.financial_reconciliation import reconcile_financials
from deploy_vii.financial_validation import book_issues, records, validate_financial_review
from deploy_vii.preparation import PreparedPack
from deploy_vii.statement_validation import statement_issues

SHA = "a" * 64


def cite(quote: str = "source evidence", locator: str = "page:1") -> Citation:
    return Citation(source_id="filing", source_sha256=SHA, locator=locator, quote=quote)


def value(line_id: str, amount: int = 1) -> Observation:
    return Observation(
        observation_id=f"obs-{line_id}",
        status="known",
        amount=Decimal(amount),
        citations=(cite(),),
    )


def period(period_id: str, year: int) -> FinancialPeriod:
    return FinancialPeriod(
        period_id=period_id,
        fiscal_year=f"FY{year}",
        fiscal_quarter=None,
        period_type="FY",
        start_date=date(year - 1, 10, 1),
        end_date=date(year, 9, 30),
        day_count=366 if year % 4 == 0 else 365,
        audit_status="audited",
        currency="USD",
        unit="MILLIONS",
        accounting_basis="US GAAP",
        entity_perimeter="Consolidated",
        citations=(cite("fiscal period"),),
    )


def line(
    line_id: str,
    period_id: str,
    item_id: str,
    *,
    kind: str = "monetary",
    scale: str = "MILLIONS",
    label: str | None = None,
    line_kind: str = "detail",
    statement: str = "CFS",
    priority: int = 1,
) -> StatementLine:
    return StatementLine(
        line_id=line_id,
        statement=statement,
        item_id=item_id,
        label=label or item_id,
        period_id=period_id,
        display_priority=priority,
        line_kind=line_kind,
        value=value(line_id),
        quantity=StatementQuantity(kind=kind, scale=scale, citations=(cite("unit context"),)),
    )


def book(
    lines: tuple[StatementLine, ...] = (),
    identities: tuple[StatementIdentity, ...] = (),
    bridges: tuple[CashMovementBridge, ...] = (),
) -> FinancialBook:
    disclosure = Disclosure(status="not_applicable", explanation="none", citations=(cite(),))
    return FinancialBook(
        book_id="book",
        entity_perimeter="Consolidated",
        accounting_basis="US GAAP",
        currency="USD",
        unit="MILLIONS",
        periods=(period("FY2024", 2024), period("FY2023", 2023)),
        accounts=(),
        addbacks=(),
        segments=(),
        kpis=(),
        facilities=(),
        pro_forma=(),
        statement_lines=lines,
        statement_identities=identities,
        cash_movement_bridges=bridges,
        segment_allocation=(),
        addback_disclosure=disclosure,
        segment_disclosure=disclosure,
    )


def test_effective_dimensions_and_exact_factors_cover_typed_and_legacy_rows() -> None:
    base = book()
    money = line("money", "FY2024", "other:money")
    per_share = line(
        "per-share", "FY2024", "other:per-share", kind="currency_per_share", scale="UNITS"
    )
    shares = line("shares", "FY2024", "other:shares", kind="shares")
    thousands = line("thousands", "FY2024", "other:thousands", kind="shares", scale="THOUSANDS")
    legacy = StatementLine(
        line_id="legacy",
        statement="CFS",
        item_id="other:legacy",
        label="Legacy",
        period_id="FY2024",
        display_priority=1,
        line_kind="detail",
        value=value("legacy"),
    )

    assert statement_dimensions(base, money).model_dump() == {
        "kind": "monetary",
        "currency": "USD",
        "scale": "MILLIONS",
    }
    assert statement_dimensions(base, money).factor == Decimal(1_000_000)
    assert statement_dimensions(base, per_share).kind == "currency_per_share"
    assert statement_dimensions(base, per_share).currency == "USD"
    assert statement_dimensions(base, per_share).scale == "UNITS"
    assert statement_dimensions(base, per_share).factor == Decimal(1)
    assert statement_dimensions(base, shares).currency is None
    assert statement_dimensions(base, shares).scale == "MILLIONS"
    assert statement_dimensions(base, thousands).factor == Decimal(1000)
    assert statement_dimensions(base, legacy) == statement_dimensions(base, money)


def test_effective_dimensions_factor_is_derived_and_not_constructor_input() -> None:
    dimensions = EffectiveStatementDimensions(kind="shares", currency=None, scale="MILLIONS")

    assert dimensions.model_dump() == {"kind": "shares", "currency": None, "scale": "MILLIONS"}
    assert dimensions.factor == Decimal(1_000_000)
    with pytest.raises(ValidationError, match="factor"):
        EffectiveStatementDimensions(
            kind="shares", currency=None, scale="MILLIONS", factor=Decimal(1)
        )


def test_unset_quantity_and_label_parts_are_omitted_from_legacy_wire_and_hash() -> None:
    legacy = StatementLine(
        line_id="legacy",
        statement="CFS",
        item_id="other:legacy",
        label="Legacy",
        period_id="FY2024",
        display_priority=1,
        line_kind="detail",
        value=value("legacy"),
    )

    wire = legacy.model_dump_json()
    assert wire == (
        '{"line_id":"legacy","statement":"CFS","item_id":"other:legacy",'
        '"label":"Legacy","period_id":"FY2024","display_priority":1,'
        '"line_kind":"detail","value":{"observation_id":"obs-legacy",'
        '"status":"known","amount":"1","citations":[{"source_id":"filing",'
        f'"source_sha256":"{SHA}","locator":"page:1","quote":"source evidence"' +
        '}],"reason":null,"alternatives":[]},"sign_convention":"signed",'
        '"sign_citations":[]}'
    )
    assert '"quantity"' not in wire
    assert '"label_parts"' not in wire
    assert legacy.content_hash() == hashlib.sha256(wire.encode()).hexdigest()
    assert json.loads(wire)["sign_convention"] == "signed"


@pytest.mark.parametrize(
    ("kind", "scale", "reason"),
    [
        ("currency_per_share", "MILLIONS", "per-share scale"),
        ("shares", "MILLIONS", "nonmonetary outflow"),
    ],
)
def test_invalid_quantity_dimensions_or_sign_conventions_refuse(
    kind: str, scale: str, reason: str
) -> None:
    if reason == "per-share scale":
        with pytest.raises(ValidationError, match="currency-per-share quantities require UNITS"):
            StatementQuantity(kind=kind, scale=scale, citations=(cite(),))
        return
    with pytest.raises(ValidationError, match="nonmonetary statement quantities require signed"):
        StatementLine(
            line_id="bad",
            statement="CFS",
            item_id="other:bad",
            label="bad",
            period_id="FY2024",
            display_priority=1,
            line_kind="detail",
            value=value("bad"),
            sign_convention="outflow_magnitude",
            sign_citations=(cite("outflows shown as magnitudes"),),
            quantity=StatementQuantity(kind=kind, scale=scale, citations=(cite(),)),
        )


def test_typed_quantity_requires_unit_context_citation() -> None:
    with pytest.raises(ValidationError):
        StatementQuantity(kind="monetary", scale="MILLIONS", citations=())


def test_label_part_requires_a_positive_physical_line_number() -> None:
    with pytest.raises(ValidationError):
        StatementLabelPart(locator="page:106", line_no=0, text="Basic and diluted")

    with pytest.raises(ValidationError):
        StatementLine(
            line_id="empty-parts",
            statement="CFS",
            item_id="other:empty-parts",
            label="No source fragments",
            period_id="FY2024",
            display_priority=1,
            line_kind="detail",
            value=value("empty-parts"),
            label_parts=(),
        )


def test_statement_quantity_does_not_change_zero_or_gap_observations() -> None:
    zero = Observation(
        observation_id="zero",
        status="known",
        amount=Decimal(0),
        citations=(cite("reported zero"),),
    )
    gap = Observation(
        observation_id="gap",
        status="missing",
        amount=None,
        citations=(),
        reason="not reported",
    )
    zero_line = line("zero", "FY2024", "other:zero").model_copy(update={"value": zero})
    gap_line = line("gap", "FY2024", "other:gap").model_copy(update={"value": gap})

    assert (zero_line.value.status, zero_line.value.amount) == ("known", Decimal(0))
    assert (gap_line.value.status, gap_line.value.amount, gap_line.value.reason) == (
        "missing",
        None,
        "not reported",
    )


def test_monetary_scale_and_logical_row_dimensions_are_guarded() -> None:
    wrong_scale = line("cash", "FY2024", "other:cash", scale="THOUSANDS")
    changed_period = line("cash", "FY2023", "other:cash", kind="shares")
    issues = statement_issues(book((wrong_scale, changed_period)))

    assert any("Monetary statement quantity scale differs from book" in issue for issue in issues)
    assert any("Changed statement definition requires a distinct line ID" in issue for issue in issues)


def test_canonical_account_link_rejects_nonmonetary_quantity() -> None:
    linked = line("revenue", "FY2024", "revenue", kind="shares", statement="IS")

    assert any("Canonical account link requires monetary quantity" in issue for issue in
               statement_issues(book((linked,)))
    )


def test_identity_equation_rejects_mixed_nonmonetary_and_monetary_dimensions() -> None:
    target = line("total", "FY2024", "other:total", line_kind="total")
    component = line("component", "FY2024", "other:component", kind="shares")
    identity = StatementIdentity(
        identity_id="mixed",
        period_id="FY2024",
        target_line_id="total",
        components=(StatementContribution(line_id="component", coefficient=1),),
        explanation="source equation",
        citations=(cite("source equation"),),
    )

    assert any(
        "Statement identity requires monetary quantities" in issue
        for issue in statement_issues(book((target, component), (identity,)))
    )


def test_identity_equation_rejects_same_unit_nonmonetary_terms_and_result() -> None:
    target = line("shares-total", "FY2024", "other:shares-total", kind="shares", line_kind="total")
    component = line("shares-part", "FY2024", "other:shares-part", kind="shares")
    identity = StatementIdentity(
        identity_id="share-identity",
        period_id="FY2024",
        target_line_id="shares-total",
        components=(StatementContribution(line_id="shares-part", coefficient=1),),
        explanation="source equation",
        citations=(cite("source equation"),),
    )

    assert any(
        "Statement identity requires monetary quantities" in issue
        for issue in statement_issues(book((target, component), (identity,)))
    )


def test_identity_equation_accepts_matching_monetary_dimensions() -> None:
    target = line("money-total", "FY2024", "other:money-total", line_kind="total", priority=1)
    component = line("money-part", "FY2024", "other:money-part", priority=2)
    identity = StatementIdentity(
        identity_id="money-identity",
        period_id="FY2024",
        target_line_id="money-total",
        components=(StatementContribution(line_id="money-part", coefficient=1),),
        explanation="source equation",
        citations=(cite("source equation"),),
    )

    assert statement_issues(book((target, component), (identity,))) == ()


def test_cash_adjustments_reject_nonmonetary_or_wrong_scale_quantities() -> None:
    bridge = CashMovementBridge(
        bridge_id="bridge",
        period_id="FY2024",
        components=(StatementContribution(line_id="fx", coefficient=1),),
        explanation="source FX detail",
        citations=(cite(),),
    )

    nonmonetary = line("fx", "FY2024", "fx_cash_effect", kind="shares")
    wrong_scale = line("fx-small", "FY2024", "fx_cash_effect", scale="THOUSANDS")
    nonmonetary_bridge = bridge.model_copy(
        update={"components": (StatementContribution(line_id="fx", coefficient=1),)}
    )
    wrong_scale_bridge = bridge.model_copy(
        update={"bridge_id": "bridge-small", "components": (
            StatementContribution(line_id="fx-small", coefficient=1),
        )}
    )

    assert any(
        "Cash adjustment requires monetary quantity" in issue
        for issue in cash_bridge_issues(book((nonmonetary,), bridges=(nonmonetary_bridge,)))
    )
    assert any(
        "Cash adjustment quantity scale differs from book" in issue
        for issue in cash_bridge_issues(book((wrong_scale,), bridges=(wrong_scale_bridge,)))
    )


def cash_scope_case(
    book_value: FinancialBook,
) -> tuple[PreparedPack, FinancialReview]:
    run = Run(
        run_id="cash-quantity-check",
        issuer_id="issuer",
        issuer_name="Cash Scope Fixture",
        as_of=date(2026, 6, 30),
        case_kind="synthetic",
    )
    review = FinancialReview(
        pack_sha256=SHA,
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        books=(book_value,),
        analysis=(),
    )
    spans: dict[str, set[str]] = {}
    for citation in records(review, Citation):
        spans.setdefault(citation.locator, set()).add(citation.quote)
    source = Source(
        source_id="k",
        name="Cash scope fixture",
        status="ready",
        sha256=SHA,
        spans=tuple(
            Span(locator=locator, text="\n".join(sorted(quotes)))
            for locator, quotes in sorted(spans.items())
        ),
        extraction_status="complete",
    )
    pack = PreparedPack(run=run, sources=(source,))
    review = review.model_copy(update={"pack_sha256": pack.content_hash()})
    return pack, review


def typed_cash_scope_book(kind: str, scale: str) -> FinancialBook:
    original = cash_scope_book(flows=("fy-2025",))
    typed_lines = []
    for row in original.statement_lines:
        if row.statement == "BS" and row.item_id in {
            "restricted_cash",
            "restricted_cash_noncurrent",
        }:
            data = row.model_dump()
            data["quantity"] = StatementQuantity(
                kind=kind, scale=scale, citations=row.value.citations
            ).model_dump()
            typed_lines.append(StatementLine.model_validate(data))
        else:
            typed_lines.append(row)
    return original.model_copy(update={"statement_lines": tuple(typed_lines)})


@pytest.mark.parametrize(
    ("kind", "scale"),
    [("shares", "MILLIONS"), ("currency_per_share", "UNITS")],
)
def test_cash_scope_raw_balances_require_monetary_dimensions_end_to_end(
    kind: str, scale: str
) -> None:
    forged = typed_cash_scope_book(kind, scale)
    pack, review = cash_scope_case(forged)

    assert any("Declared cash scope balance requires book monetary dimensions" in issue
               for issue in book_issues(forged))
    issues = validate_financial_review(pack, review)
    assert any("Declared cash scope balance requires book monetary dimensions" in issue
               for issue in issues)
    with pytest.raises(ValueError, match="Declared cash scope balance requires book monetary dimensions"):
        reconcile_financials(pack, review, forged.book_id)


def test_typed_monetary_cash_scope_balances_pass_full_validation_and_reconciliation() -> None:
    valid = typed_cash_scope_book("monetary", "MILLIONS")
    pack, review = cash_scope_case(valid)

    assert book_issues(valid) == ()
    assert validate_financial_review(pack, review) == ()
    report = reconcile_financials(pack, review, valid.book_id)
    check = next(item for item in report.checks if item.check_type == "NCF_CASH_MOVEMENT")
    assert (report.unit, check.status, check.calculated_value) == (
        "MILLIONS",
        "PASS",
        Decimal(-32),
    )
