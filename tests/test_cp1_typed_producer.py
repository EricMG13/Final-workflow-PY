"""Strict source-label and quantity behavior for CP-1 statement composition."""

import json
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

import test_financial_workflow as g1

from deploy_vii.contracts import Citation
from deploy_vii.financial_contracts import StatementQuantity
from deploy_vii.live.schema import exact_json, strict_schema
from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow.statement_compose import (
    SOURCE_LABEL_REFUSED,
    SOURCE_QUANTITY_REFUSED,
    RowJudgment,
    compose_unit,
    resolve_label_parts,
)
from deploy_workflow.unit_maps import (
    FinancialMapSubmission,
    UnitInputs,
    UnitMap,
    _typed_profile_problem,
    expand,
)

SOURCE_ID = "issuer"
SOURCE_HASH = "a" * 64
PAGE = "page:7"
TEXT = """STATEMENT OF OPERATIONS
Amounts in millions, except per share data
2024       2023
Earnings per share                    3          2
Net sales                            10          9
"""


def _quantity(kind: str, scale: str) -> StatementQuantity:
    return StatementQuantity(
        kind=kind,
        scale=scale,
        citations=(
            Citation(
                source_id=SOURCE_ID,
                source_sha256=SOURCE_HASH,
                locator=PAGE,
                quote="Amounts in millions, except per share data",
            ),
        ),
    )


def _compose(quantity: StatementQuantity):
    table = extract_statement_lines(TEXT, PAGE, SOURCE_ID)
    row = table.lines[0]
    return compose_unit(
        table,
        source_id=SOURCE_ID,
        source_sha256=SOURCE_HASH,
        unit_locator=PAGE,
        kind="IS",
        column_periods=("FY2024", "FY2023"),
        row_map={row.line_no: RowJudgment("eps", "other:eps", "detail", "signed")},
        declared_periods=("FY2024", "FY2023"),
        row_label_selections={row.line_no: (row.line_no,)},
        row_dimensions={row.line_no: quantity},
        typed_profile=True,
        book_currency="USD",
        book_unit="MILLIONS",
    )


def test_source_supported_per_share_quantity_composes_with_exact_label_part_citation() -> None:
    result = _compose(_quantity("currency_per_share", "UNITS"))

    assert [line.label for line in result.lines] == ["Earnings per share", "Earnings per share"]
    assert all(
        line.quantity is not None and line.quantity.kind == "currency_per_share"
        for line in result.lines
    )
    assert all(line.label_parts is not None for line in result.lines)
    assert all(line.label_parts[0].locator == PAGE for line in result.lines)
    assert all(line.label_parts[0].text == "Earnings per share" for line in result.lines)


def test_legacy_composition_omits_new_fields_despite_extractor_candidates() -> None:
    table = extract_statement_lines(TEXT, PAGE, SOURCE_ID)
    row = table.lines[1]
    result = compose_unit(
        table,
        source_id=SOURCE_ID,
        source_sha256=SOURCE_HASH,
        unit_locator=PAGE,
        kind="IS",
        column_periods=("FY2024", "FY2023"),
        row_map={row.line_no: RowJudgment("sales", "revenue", "detail", "signed")},
        declared_periods=("FY2024", "FY2023"),
    )

    assert len(result.lines) == 2
    assert all(line.quantity is None and line.label_parts is None for line in result.lines)
    assert all(
        "quantity" not in line.model_dump(mode="json", exclude_none=True)
        and "label_parts" not in line.model_dump(mode="json", exclude_none=True)
        for line in result.lines
    )


def test_per_share_row_cannot_be_mapped_as_monetary_even_with_valid_page_context() -> None:
    result = _compose(_quantity("monetary", "MILLIONS"))

    assert not result.lines
    assert [item.reason for item in result.left_to_model].count(SOURCE_QUANTITY_REFUSED) == 1


def test_unpunctuated_prefix_cannot_be_dropped_from_a_typed_label() -> None:
    root = Path(__file__).parents[1]
    table = extract_statement_lines(
        (root / "cases/cp1-chain/fixtures/allcaps-wrapped-prefix.txt").read_text(),
        "page:1",
        SOURCE_ID,
    )
    row = table.lines[0]
    assert [part.text for part in row.label_candidates] == [
        "SERVICE REVENUE FROM",
        "REPLACEMENT COMPONENTS",
    ]
    result = compose_unit(
        table,
        source_id=SOURCE_ID,
        source_sha256=SOURCE_HASH,
        unit_locator="page:1",
        kind="IS",
        column_periods=("FY2025", "FY2024"),
        row_map={row.line_no: RowJudgment("revenue", "revenue", "detail", "signed")},
        declared_periods=("FY2025", "FY2024"),
        row_label_selections={row.line_no: (row.line_no,)},
        row_dimensions={row.line_no: _quantity("monetary", "MILLIONS")},
        typed_profile=True,
        book_currency="USD",
        book_unit="MILLIONS",
    )

    assert not result.lines
    assert any(item.reason == SOURCE_LABEL_REFUSED for item in result.left_to_model)


def test_tdg_basic_and_diluted_suffix_cannot_claim_money_or_shares() -> None:
    root = Path(__file__).parents[1]
    source_id = "TDG-FY2024-10K"
    source_hash = "dc6a8ea6249e4e919d190a4bbb459d9bf4eded005b7d5680ae911b32d44d44af"
    table = extract_statement_lines(
        (root / "tests/fixtures/pdf_pages/TDG/p106.txt").read_text(),
        "page:106",
        source_id,
    )
    row = next(line for line in table.lines if line.line_no == 33)
    context = Citation(
        source_id=source_id,
        source_sha256=source_hash,
        locator="page:106",
        quote="(Amounts in millions, except per share amounts)",
    )
    base = {
        "table": table,
        "source_id": source_id,
        "source_sha256": source_hash,
        "unit_locator": "page:106",
        "kind": "IS",
        "column_periods": ("FY2024", "FY2023", "FY2022"),
        "row_map": {row.line_no: RowJudgment("shares", "other:shares", "detail", "signed")},
        "declared_periods": ("FY2024", "FY2023", "FY2022"),
        "row_label_selections": {row.line_no: (row.line_no,)},
        "typed_profile": True,
        "book_currency": "USD",
        "book_unit": "MILLIONS",
    }
    money = compose_unit(
        **base,
        row_dimensions={
            row.line_no: StatementQuantity(kind="monetary", scale="MILLIONS", citations=(context,))
        },
    )
    shares = compose_unit(
        **base,
        row_dimensions={
            row.line_no: StatementQuantity(kind="shares", scale="MILLIONS", citations=(context,))
        },
    )
    per_share = compose_unit(
        **base,
        row_dimensions={
            row.line_no: StatementQuantity(
                kind="currency_per_share", scale="UNITS", citations=(context,)
            )
        },
    )

    assert not money.lines
    assert not shares.lines
    assert not per_share.lines
    assert any(item.reason == SOURCE_QUANTITY_REFUSED for item in money.left_to_model)
    assert any(item.reason == SOURCE_QUANTITY_REFUSED for item in shares.left_to_model)
    assert any(item.reason == SOURCE_QUANTITY_REFUSED for item in per_share.left_to_model)


def test_local_per_share_heading_classifies_full_label_and_blocks_suffix_for_all_kinds() -> None:
    from test_statement_quantities import book as quantity_book

    from deploy_vii.financial_contracts import StatementLabelPart
    from deploy_workflow import financial_workflow as fw

    text = """STATEMENT OF OPERATIONS
(Amounts in millions, except per share amounts)
Fiscal Years Ended December 31,
2025       2024
Earnings per share:
Basic                         3          2
Revenue                      10          9
"""
    table = extract_statement_lines(text, "page:7", SOURCE_ID)
    eps = next(row for row in table.lines if row.label == "Basic")
    revenue = next(row for row in table.lines if row.label == "Revenue")
    context = Citation(
        source_id=SOURCE_ID,
        source_sha256=SOURCE_HASH,
        locator="page:7",
        quote="(Amounts in millions, except per share amounts)",
    )
    eps_heading = next(part for part in eps.label_candidates if part.text == "Earnings per share:")
    full_selection = (eps_heading.line_no, eps.line_no)

    def compose(row: Any, selection: tuple[int, ...], kind: str, scale: str):
        quantity = StatementQuantity(kind=kind, scale=scale, citations=(context,))
        return compose_unit(
            table,
            source_id=SOURCE_ID,
            source_sha256=SOURCE_HASH,
            unit_locator="page:7",
            kind="IS",
            column_periods=("FY2025", "FY2024"),
            row_map={row.line_no: RowJudgment(row.label, "other:line", "detail", "signed")},
            declared_periods=("FY2025", "FY2024"),
            row_label_selections={row.line_no: selection},
            row_dimensions={row.line_no: quantity},
            typed_profile=True,
            book_currency="USD",
            book_unit="MILLIONS",
        )

    valid = compose(eps, full_selection, "currency_per_share", "UNITS")
    assert len(valid.lines) == 2
    assert all(line.label == "Earnings per share: Basic" for line in valid.lines)
    assert all(
        line.quantity is not None and line.quantity.kind == "currency_per_share"
        for line in valid.lines
    )

    for kind, scale in (
        ("currency_per_share", "UNITS"),
        ("monetary", "MILLIONS"),
        ("shares", "MILLIONS"),
    ):
        refused = compose(eps, (eps.line_no,), kind, scale)
        assert not refused.lines
        assert any(item.reason == SOURCE_QUANTITY_REFUSED for item in refused.left_to_model)

    money = compose(revenue, (revenue.line_no,), "monetary", "MILLIONS")
    assert len(money.lines) == 2
    for kind, scale in (
        ("currency_per_share", "UNITS"),
        ("shares", "MILLIONS"),
    ):
        refused = compose(revenue, (revenue.line_no,), kind, scale)
        assert not refused.lines
        assert any(item.reason == SOURCE_QUANTITY_REFUSED for item in refused.left_to_model)

    forged_lines = []
    for kind, scale in (
        ("currency_per_share", "UNITS"),
        ("monetary", "MILLIONS"),
        ("shares", "MILLIONS"),
    ):
        forged_lines.append(
            valid.lines[0].model_copy(
                update={
                    "label": "Basic",
                    "label_parts": (
                        StatementLabelPart(locator="page:7", line_no=eps.line_no, text="Basic"),
                    ),
                    "quantity": StatementQuantity(kind=kind, scale=scale, citations=(context,)),
                }
            )
        )
    for forged in forged_lines:
        book = quantity_book().model_copy(update={"statement_lines": (forged,)})
        failure = fw._column_failure(
            book,
            table,
            eps,
            "IS",
            (frozenset({"FY2025"}), Decimal(3)),
            source_sha256=SOURCE_HASH,
            context_tables=(table,),
        )
        assert failure is not None and failure[0] == 2


def _strip_visible_payload(value: Any) -> Any:
    if isinstance(value, dict):
        stripped = {
            key: Decimal(item)
            if key == "amount" and isinstance(item, str)
            else _strip_visible_payload(item)
            for key, item in value.items()
            if key != "source_sha256"
        }
        if "status" in stripped and "amount" in stripped:
            stripped.setdefault("reason", None)
            stripped.setdefault("alternatives", [])
        return stripped
    if isinstance(value, list):
        return [_strip_visible_payload(item) for item in value]
    return value


def _matches_schema(value: Any, node: dict[str, Any], schema: dict[str, Any]) -> bool:
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        return _matches_schema(value, schema["$defs"][name], schema)
    branches = node.get("anyOf", node.get("oneOf"))
    if branches:
        return any(_matches_schema(value, branch, schema) for branch in branches)
    if isinstance(value, dict) and "properties" in node:
        properties = node["properties"]
        return (
            set(value) <= set(properties)
            and set(node.get("required", ())) <= set(value)
            and all(_matches_schema(item, properties[key], schema) for key, item in value.items())
        )
    if isinstance(value, list) and "items" in node:
        return all(_matches_schema(item, node["items"], schema) for item in value)
    expected = node.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        matches_type = any(
            (kind == "null" and value is None)
            or (kind == "object" and isinstance(value, dict))
            or (kind == "array" and isinstance(value, list))
            or (kind == "string" and isinstance(value, str))
            or (kind == "integer" and type(value) is int)
            or (kind == "number" and type(value) in (int, float, Decimal))
            or (kind == "boolean" and type(value) is bool)
            for kind in expected_types
        )
        if not matches_type:
            return False
    if "const" in node and value != node["const"]:
        return False
    return not ("enum" in node and value not in node["enum"])


def _visible_g1_unit_payload(
    pack: Any, *, wrong_currency: bool = False
) -> tuple[dict[str, Any], Any]:
    payload = g1.financials(pack)
    payload["schema_version"] = "cp1-financial-submission/1"
    payload["quarter_ids"] = None
    payload["financial"]["schema_version"] = "financial-review/5"
    payload["financial"]["method_version"] = "deploy-v-r14"
    payload["definition"]["schema_version"] = "definition-review/1"
    payload["definition"]["assessments"] = []
    payload["definition"]["events"] = []
    payload["binding"]["schema_version"] = "financial-context-binding/1"
    book = payload["financial"]["books"][0]
    book.setdefault("audit_basis_explanations", [])
    book.setdefault("facility_fx_conversions", [])
    for facility in book["facilities"]:
        facility.setdefault("issued_on", None)
        facility.setdefault("issuance_citations", [])
    for line in book["statement_lines"]:
        line.setdefault("quantity", None)
        line.setdefault("label_parts", None)
    for bridge in book["cash_movement_bridges"]:
        bridge.setdefault("cash_scope", None)
    for movement in book["balance_movements"]:
        movement.setdefault("sign_citations", [])
    ids_by_label = {
        line["label"]: line
        for line in book["statement_lines"]
        if any(citation.get("locator") == "page:2" for citation in line["value"]["citations"])
    }
    book["statement_lines"] = [
        line
        for line in book["statement_lines"]
        if not any(citation.get("locator") == "page:2" for citation in line["value"]["citations"])
    ]
    for key in ("entity_perimeter", "accounting_basis", "currency", "unit"):
        book.pop(key, None)
    for period in book["periods"]:
        period.setdefault("component_period_ids", [])
        for key in ("entity_perimeter", "accounting_basis", "currency", "unit"):
            period.pop(key, None)

    table = extract_statement_lines(
        g1.MANIFEST["sources"][1]["pages"][1]["text"], "page:2", "financial"
    )
    period_ids = ("q1-2025", "q2-2025", "q3-2025", "q4-2025", "fy-2025")
    context = {
        "source_id": "financial",
        "locator": "page:2",
        "quote": "USD; amounts in millions; unaudited",
    }
    rows = []
    selections = []
    dimensions = []
    for row in table.lines:
        line = ids_by_label[row.label]
        rows.append(
            {
                "row": row.line_no,
                "line_id": line["line_id"],
                "item_id": line["item_id"],
                "line_kind": line["line_kind"],
                "sign_convention": line["sign_convention"],
            }
        )
        selections.append(
            {
                "row": row.line_no,
                "part_line_numbers": [part.line_no for part in row.label_candidates],
            }
        )
        dimensions.append(
            {
                "row": row.line_no,
                "quantity": {"kind": "monetary", "scale": "MILLIONS", "citations": [context]},
            }
        )
    payload["unit_maps"] = [
        {
            "source_id": "financial",
            "locator": "page:2",
            "book_id": book["book_id"],
            "statement": "IS",
            "columns": list(period_ids),
            "rows": rows,
            "profile": "typed-source/1",
            "row_label_selections": selections,
            "row_dimensions": dimensions,
        }
    ]
    if wrong_currency:
        book["currency"] = "EUR"
    return _strip_visible_payload(payload), table


def test_financial_workflow_submit_uses_prefilled_dimensions_for_visible_typed_map(
    tmp_path: Path,
) -> None:
    from deploy_workflow.unit_maps import FinancialMapSubmission

    workflow, pack = g1.before_financials(tmp_path / "positive")
    g1.financial_reads(workflow)
    visible, table = _visible_g1_unit_payload(pack)
    first = table.lines[0]
    assert first.label == "Revenue"
    assert [(part.line_no, part.text) for part in first.label_candidates] == [
        (first.line_no, "Revenue")
    ]
    assert resolve_label_parts(table, first, (1, first.line_no)) is None
    assert visible["unit_maps"][0]["row_label_selections"][0]["part_line_numbers"] == [
        first.line_no
    ]
    schema = strict_schema(FinancialMapSubmission)
    assert _matches_schema(visible, schema, schema)
    outcome = workflow.submit_review(exact_json(visible))
    assert outcome["status"] == "valid", outcome
    record = workflow._submissions[-1]
    from deploy_vii.execution import Execution

    stored = json.loads(
        Execution(tmp_path / "positive" / "store").payload(record.stored_payload_sha256)
    )
    book = stored["financial"]["books"][0]
    typed = [
        line
        for line in book["statement_lines"]
        if line.get("label_parts") and line["label_parts"][-1]["locator"] == "page:2"
    ]
    assert len(typed) == len(table.lines) * len(table.lines[0].values) == 105
    assert all(line["quantity"]["kind"] == "monetary" for line in typed)
    assert all(line["quantity"]["scale"] == "MILLIONS" for line in typed)
    assert book["currency"] == "USD" and book["unit"] == "MILLIONS"
    revenue_id = visible["unit_maps"][0]["rows"][0]["line_id"]
    revenue = [line for line in typed if line["line_id"] == revenue_id]
    assert len(revenue) == 5
    assert {line["label"] for line in revenue} == {"Revenue"}


def test_financial_workflow_refuses_hidden_scope_mismatch_before_map_composition(
    tmp_path: Path,
) -> None:
    root = tmp_path / "wrong-scope"
    workflow, pack = g1.before_financials(root)
    g1.financial_reads(workflow)
    visible, _ = _visible_g1_unit_payload(pack, wrong_currency=True)
    outcome = workflow.submit_review(exact_json(visible))
    assert outcome["status"] != "valid", outcome
    record = workflow._submissions[-1]
    assert record.binding.payload_sha256 == sha256(exact_json(visible).encode()).hexdigest()


def test_typed_balance_rows_require_instant_periods_without_start_dates() -> None:
    text = """BALANCE SHEET
Amounts in millions
As of December 31, 2024 and December 31, 2023
Cash and cash equivalents                10           8
"""
    table = extract_statement_lines(text, "page:8", SOURCE_ID)
    row = table.lines[0]
    quantity = StatementQuantity(
        kind="monetary",
        scale="MILLIONS",
        citations=(
            Citation(
                source_id=SOURCE_ID,
                source_sha256=SOURCE_HASH,
                locator="page:8",
                quote="Amounts in millions",
            ),
        ),
    )
    unit = UnitMap(
        source_id=SOURCE_ID,
        locator="page:8",
        book_id="book",
        statement="BS",
        columns=("BS24", "BS23"),
        rows=(
            {
                "row": row.line_no,
                "line_id": "cash",
                "item_id": "cash_and_equivalents",
                "line_kind": "detail",
                "sign_convention": "signed",
            },
        ),
        profile="typed-source/1",
        row_label_selections=({"row": row.line_no, "part_line_numbers": (row.line_no,)},),
        row_dimensions=({"row": row.line_no, "quantity": quantity},),
    )
    book = {
        "periods": [
            {
                "period_id": "BS24",
                "period_type": "PERIOD_END",
                "start_date": None,
                "end_date": "2024-12-31",
            },
            {
                "period_id": "BS23",
                "period_type": "PERIOD_END",
                "start_date": None,
                "end_date": "2023-12-31",
            },
        ]
    }

    assert _typed_profile_problem(unit, book, table) is None

    dated_as_flow = {
        "periods": [
            {
                "period_id": f"BS{str(year)[-2:]}",
                "period_type": "FY",
                "start_date": f"{year - 1}-01-01",
                "end_date": f"{year}-12-31",
            }
            for year in (2024, 2023)
        ]
    }
    assert "PERIOD_END" in _typed_profile_problem(unit, dated_as_flow, table)


def test_generic_share_count_head_uses_explicit_share_amount_context() -> None:
    text = """STATEMENT OF OPERATIONS
Amounts in millions, except share amounts
2024       2023
Number of shares outstanding             8          7
"""
    table = extract_statement_lines(text, "page:9", SOURCE_ID)
    row = table.lines[0]
    context = Citation(
        source_id=SOURCE_ID,
        source_sha256=SOURCE_HASH,
        locator="page:9",
        quote="Amounts in millions, except share amounts",
    )
    args = {
        "table": table,
        "source_id": SOURCE_ID,
        "source_sha256": SOURCE_HASH,
        "unit_locator": "page:9",
        "kind": "IS",
        "column_periods": ("FY2024", "FY2023"),
        "row_map": {row.line_no: RowJudgment("shares", "other:shares", "detail", "signed")},
        "declared_periods": ("FY2024", "FY2023"),
        "row_label_selections": {row.line_no: (row.line_no,)},
        "book_currency": "USD",
        "book_unit": "MILLIONS",
        "typed_profile": True,
    }

    share_result = compose_unit(
        **args,
        row_dimensions={
            row.line_no: StatementQuantity(kind="shares", scale="UNITS", citations=(context,))
        },
    )
    money_result = compose_unit(
        **args,
        row_dimensions={
            row.line_no: StatementQuantity(kind="monetary", scale="MILLIONS", citations=(context,))
        },
    )

    assert len(share_result.lines) == 2
    assert not share_result.left_to_model
    assert not money_result.lines
    assert any(item.reason == SOURCE_QUANTITY_REFUSED for item in money_result.left_to_model)


def test_common_stock_rows_with_embedded_share_descriptions_remain_monetary() -> None:
    root = Path(__file__).parents[1]
    expected = json.loads((root / "cases/cp1-chain/expected.json").read_text())
    table = extract_statement_lines(
        (root / "tests/fixtures/pdf_pages/TDG/p105.txt").read_text(),
        "page:105",
        "TDG-FY2024-10K",
    )
    by_line = {line.line_no: line for line in table.lines}
    for row_id in ("BS-21", "BS-25"):
        expected_row = next(row for row in expected["financial_rows"] if row["row_id"] == row_id)
        line = by_line[expected_row["amount_position"]["line"]]
        quantity_data = expected_row["row_dimensions"]["quantity"]
        citations = tuple(
            Citation(
                source_id=citation["source_id"],
                source_sha256=citation["source_sha256"],
                locator=citation["locator"],
                quote=citation["quote"],
            )
            for citation in quantity_data["unit_context_citations"]
        )
        result = compose_unit(
            table,
            source_id="TDG-FY2024-10K",
            source_sha256=expected["source"]["source_sha256"],
            unit_locator="page:105",
            kind="BS",
            column_periods=tuple(expected_row["period_ids"]),
            row_map={line.line_no: RowJudgment(row_id, f"other:{row_id}", "detail", "signed")},
            declared_periods=tuple(expected_row["period_ids"]),
            row_label_selections={
                line.line_no: tuple(part["line"] for part in expected_row["label_parts"])
            },
            row_dimensions={
                line.line_no: StatementQuantity(
                    kind="shares", scale="MILLIONS", citations=citations
                )
            },
            typed_profile=True,
            book_currency="USD",
            book_unit="MILLIONS",
        )
        assert not result.lines
        assert any(item.reason == SOURCE_QUANTITY_REFUSED for item in result.left_to_model)


def test_model_visible_hash_omission_binds_only_from_current_seen_context() -> None:
    source_hash = "c" * 64
    row_text = """STATEMENT OF OPERATIONS
Amounts in millions, except share amounts
2024       2023
Number of shares outstanding             8          7
"""
    table = extract_statement_lines(row_text, "page:9", SOURCE_ID)
    context = extract_statement_lines(
        "Amounts in millions, except share amounts", "page:3", SOURCE_ID
    )
    row = table.lines[0]
    raw_map = {
        "source_id": SOURCE_ID,
        "locator": "page:9",
        "book_id": "book",
        "statement": "IS",
        "columns": ["FY2024", "FY2023"],
        "rows": [
            {
                "row": row.line_no,
                "line_id": "shares",
                "item_id": "other:shares",
                "line_kind": "detail",
                "sign_convention": "signed",
            }
        ],
        "profile": "typed-source/1",
        "row_label_selections": [{"row": row.line_no, "part_line_numbers": [row.line_no]}],
        "row_dimensions": [
            {
                "row": row.line_no,
                "quantity": {
                    "kind": "shares",
                    "scale": "UNITS",
                    "citations": [
                        {
                            "source_id": SOURCE_ID,
                            "locator": "page:9",
                            "quote": "Amounts in millions, except share amounts",
                        }
                    ],
                },
            }
        ],
    }
    book = {
        "book_id": "book",
        "currency": "USD",
        "unit": "MILLIONS",
        "periods": [
            {
                "period_id": "FY2024",
                "period_type": "FY",
                "start_date": "2023-10-01",
                "end_date": "2024-09-30",
            },
            {
                "period_id": "FY2023",
                "period_type": "FY",
                "start_date": "2022-10-01",
                "end_date": "2023-09-30",
            },
        ],
        "statement_lines": [],
    }
    payload = json.dumps({"financial": {"books": [book]}, "unit_maps": [raw_map]})
    inputs = UnitInputs(
        tables=(table, context),
        hashes={SOURCE_ID: source_hash},
        located=frozenset({(SOURCE_ID, "page:9")}),
        ocr_header=lambda *_: (frozenset({"FY2024"}), frozenset({"FY2023"})),
        book_dimensions={"book": ("USD", "MILLIONS")},
    )

    assert "source_sha256" not in json.dumps(strict_schema(FinancialMapSubmission))
    result = expand(payload, extracted={(SOURCE_ID, "page:9")}, inputs=lambda: inputs)
    expanded = json.loads(result.payload)
    lines = expanded["financial"]["books"][0]["statement_lines"]
    assert len(lines) == 2, result.notes
    assert all(
        citation["source_sha256"] == source_hash
        for line in lines
        for citation in line["quantity"]["citations"]
    )

    from dataclasses import replace

    unread = UnitInputs(
        tables=(replace(table, source_lines=tuple(
            line for line in table.source_lines if "Amounts in millions" not in line.text
        )),),
        hashes={SOURCE_ID: source_hash},
        located=frozenset({(SOURCE_ID, "page:9")}),
        ocr_header=inputs.ocr_header,
        book_dimensions={"book": ("USD", "MILLIONS")},
    )
    refused = expand(payload, extracted={(SOURCE_ID, "page:9")}, inputs=lambda: unread)
    assert json.loads(refused.payload)["financial"]["books"][0]["statement_lines"] == []
    assert any("source unit evidence" in note for note in refused.notes)

    wrong_hash_map = json.loads(payload)["unit_maps"][0]
    wrong_hash_map["row_dimensions"][0]["quantity"]["citations"][0]["source_sha256"] = "d" * 64
    wrong_payload = json.dumps({"financial": {"books": [book]}, "unit_maps": [wrong_hash_map]})
    wrong = expand(wrong_payload, extracted={(SOURCE_ID, "page:9")}, inputs=lambda: inputs)
    assert json.loads(wrong.payload)["financial"]["books"][0]["statement_lines"] == []


def test_frozen_tdgroup_source_composes_all_103_rows_and_280_cells() -> None:
    root = Path(__file__).parents[1]
    expected = json.loads((root / "cases/cp1-chain/expected.json").read_text())
    by_page: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in expected["financial_rows"]:
        by_page[row["amount_position"]["page"]].append(row)

    composed_rows: dict[str, object] = {}
    composed_cells = 0
    for page, rows in by_page.items():
        locator = f"page:{page}"
        source_id = rows[0]["amount_position"]["source_id"]
        table = extract_statement_lines(
            (root / f"tests/fixtures/pdf_pages/TDG/p{page:03}.txt").read_text(),
            locator,
            source_id,
        )
        extracted = {line.line_no: line for line in table.lines}
        row_map = {}
        selections = {}
        dimensions = {}
        columns = tuple(rows[0]["period_ids"])
        for item in rows:
            position = item["amount_position"]
            row = extracted[position["line"]]
            assert tuple(item["period_ids"]) == columns
            row_map[row.line_no] = RowJudgment(
                item["row_id"],
                f"other:ci_{item['row_id']}"
                if item["statement"] == "CI"
                else f"other:{item['row_id']}",
                "detail",
                "signed",
            )
            selections[row.line_no] = tuple(part["line"] for part in item["label_parts"])
            quantity = item["row_dimensions"]["quantity"]
            contexts = tuple(
                Citation(
                    source_id=citation["source_id"],
                    source_sha256=citation["source_sha256"],
                    locator=citation["locator"],
                    quote=citation["quote"],
                )
                for citation in quantity["unit_context_citations"]
            )
            dimensions[row.line_no] = StatementQuantity(
                kind=quantity["kind"], scale=quantity["scale"], citations=contexts
            )
        transport_kind = "IS" if rows[0]["statement"] == "CI" else rows[0]["statement"]
        result = compose_unit(
            table,
            source_id=source_id,
            source_sha256=expected["source"]["source_sha256"],
            unit_locator=locator,
            kind=transport_kind,
            column_periods=columns,
            row_map=row_map,
            declared_periods=columns,
            row_label_selections=selections,
            row_dimensions=dimensions,
            typed_profile=True,
            book_currency="USD",
            book_unit="MILLIONS",
        )
        assert not result.left_to_model
        assert not result.issues
        assert len(result.lines) == len(rows) * len(columns)
        composed_cells += len(result.lines)
        for item in rows:
            line = next(line for line in result.lines if line.line_id == item["row_id"])
            composed_rows[item["row_id"]] = line
            assert (
                " ".join(line.label.split()).casefold()
                == " ".join(item["label"].split()).casefold()
            )
            assert line.quantity is not None
            assert line.quantity.kind == item["row_dimensions"]["quantity"]["kind"]
            assert line.quantity.scale == item["row_dimensions"]["quantity"]["scale"]
            assert line.label_parts is not None
            assert [part.line_no for part in line.label_parts] == [
                part["line"] for part in item["label_parts"]
            ]
            assert [part.text.casefold() for part in line.label_parts] == [
                part["label_text"].casefold() for part in item["label_parts"]
            ]
            for part in line.label_parts:
                source_line = next(
                    source_line
                    for source_line in table.source_lines
                    if source_line.line_no == part.line_no
                )
                assert part.text in source_line.text
            assert all(part.locator == locator for part in line.label_parts)
            expected_values = [Decimal(value) for value in item["normalized_values"]]
            actual_values = [
                line.value.amount for line in result.lines if line.line_id == item["row_id"]
            ]
            assert actual_values == expected_values

    assert len(composed_rows) == 103
    assert composed_cells == 280
    assert sum(1 for row in composed_rows.values() if row.quantity.kind == "shares") == 1
    assert (
        sum(1 for row in composed_rows.values() if row.quantity.kind == "currency_per_share") == 4
    )


def test_frozen_tdgroup_all_four_pdf_units_expand_from_model_visible_maps() -> None:
    """Exercise extraction, actual PDF location/header binding and typed expansion together."""
    from types import SimpleNamespace

    from deploy_vii.contracts import Source, Span
    from deploy_workflow import financial_workflow as fw

    root = Path(__file__).parents[1]
    expected = json.loads((root / "cases/cp1-chain/expected.json").read_text())
    source_id = expected["financial_rows"][0]["amount_position"]["source_id"]
    source_hash = expected["source"]["source_sha256"]
    page_texts = {
        page: (root / f"tests/fixtures/pdf_pages/TDG/p{page:03}.txt").read_text()
        for page in (105, 106, 107, 109)
    }
    page3 = (root / "work/cp1-typed-producer/fixtures/p3.txt").read_text()
    assert sha256(page3.encode()).hexdigest() == expected["source"]["page_text_sha256"]["3"]
    page_texts[3] = page3
    source = Source(
        source_id=source_id,
        name=expected["source"]["source_name"],
        status="ready",
        sha256=source_hash,
        media_type="application/pdf",
        spans=tuple(Span(locator=f"page:{page}", text=text) for page, text in page_texts.items()),
    )
    pack = SimpleNamespace(sources=(source,))
    financial_ids = (source_id,)
    located = fw._located_units(pack, financial_ids)
    kinds = fw._located_kinds(pack, financial_ids)
    pdf_units = fw._located_pdf_units(pack, financial_ids)
    assert set(located) == {(source_id, f"page:{page}") for page in (105, 106, 107, 109)}
    assert kinds[(source_id, "page:107")] == "IS"  # CI transport alias, retained per-page.
    assert set(pdf_units) == set(located)

    periods = [
        {
            "period_id": period["period_id"],
            "fiscal_year": str(period["fiscal_year"]),
            "fiscal_quarter": None,
            "period_type": "PERIOD_END" if period["kind"] == "instant" else "FY",
            "start_date": period["start_date"],
            "end_date": period["end_date"],
        }
        for period in (
            *expected["fiscal_policy"]["periods"]["BS"],
            *expected["fiscal_policy"]["periods"]["duration"],
        )
    ]
    book_id = "tdg"
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in expected["financial_rows"]:
        by_page[row["amount_position"]["page"]].append(row)
    tables = {
        (source_id, f"page:{page}"): extract_statement_lines(
            page_texts[page], f"page:{page}", source_id
        )
        for page in page_texts
    }
    raw_maps: list[dict[str, Any]] = []
    for page, rows in by_page.items():
        locator = f"page:{page}"
        table = tables[(source_id, locator)]
        extracted = {line.line_no: line for line in table.lines}
        row_entries: list[dict[str, Any]] = []
        label_selections: list[dict[str, Any]] = []
        dimensions: list[dict[str, Any]] = []
        for item in rows:
            position = item["amount_position"]
            line = extracted[position["line"]]
            row_id = item["row_id"]
            item_id = f"other:ci_{row_id}" if item["statement"] == "CI" else f"other:{row_id}"
            row_entries.append(
                {
                    "row": line.line_no,
                    "line_id": row_id,
                    "item_id": item_id,
                    "line_kind": "detail",
                    "sign_convention": "signed",
                }
            )
            label_selections.append(
                {
                    "row": line.line_no,
                    "part_line_numbers": [part["line"] for part in item["label_parts"]],
                }
            )
            quantity = item["row_dimensions"]["quantity"]
            dimensions.append(
                {
                    "row": line.line_no,
                    "quantity": {
                        "kind": quantity["kind"],
                        "scale": quantity["scale"],
                        "citations": [
                            {
                                "source_id": cite["source_id"],
                                "locator": cite["locator"],
                                "quote": cite["quote"],
                            }
                            for cite in quantity["unit_context_citations"]
                        ],
                    },
                }
            )
        statement = "IS" if rows[0]["statement"] == "CI" else rows[0]["statement"]
        raw_maps.append(
            {
                "source_id": source_id,
                "locator": locator,
                "book_id": book_id,
                "statement": statement,
                "columns": rows[0]["period_ids"],
                "rows": row_entries,
                "profile": "typed-source/1",
                "row_label_selections": label_selections,
                "row_dimensions": dimensions,
            }
        )

    def header(table: Any, book: dict[str, Any]) -> Any:
        key = (table.source_id, table.locator)
        return fw._header_columns(
            table,
            book,
            page_text=pdf_units.get(key),
            statement=kinds.get(key),
        )

    inputs = UnitInputs(
        tables=tuple(tables.values()),
        hashes={source_id: source_hash},
        ocr_header=header,
        located=frozenset(located),
        book_dimensions={book_id: ("USD", "MILLIONS")},
    )
    visible_payload = json.dumps(
        {
            "financial": {
                "books": [
                    {
                        "book_id": book_id,
                        "periods": periods,
                        "statement_lines": [],
                    }
                ]
            },
            "unit_maps": raw_maps,
        }
    )
    result = expand(
        visible_payload,
        extracted=set(located),
        inputs=lambda: inputs,
    )
    assert not result.notes, result.notes
    expanded = json.loads(result.payload)
    lines = expanded["financial"]["books"][0]["statement_lines"]
    assert len(lines) == 280
    assert len({line["line_id"] for line in lines}) == 103
    assert sum(len(row["normalized_values"]) for row in expected["financial_rows"]) == 280
    for expected_row in expected["financial_rows"]:
        actual = [line for line in lines if line["line_id"] == expected_row["row_id"]]
        assert len(actual) == len(expected_row["normalized_values"])
        assert [Decimal(str(line["value"]["amount"])) for line in actual] == [
            Decimal(value) for value in expected_row["normalized_values"]
        ]
        assert all(
            line["quantity"]["kind"] == expected_row["row_dimensions"]["quantity"]["kind"]
            for line in actual
        )
        assert all(
            line["quantity"]["scale"] == expected_row["row_dimensions"]["quantity"]["scale"]
            for line in actual
        )
    ci = [line for line in lines if line["item_id"].startswith("other:ci_")]
    assert len(ci) == 24
    assert {line["line_id"] for line in ci} == {
        row["row_id"] for row in expected["financial_rows"] if row["statement"] == "CI"
    }
    assert all(line["quantity"]["citations"][0]["source_sha256"] == source_hash for line in lines)
