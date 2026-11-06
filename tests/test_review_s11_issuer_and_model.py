"""S11 review: issuer identity on word boundaries; the Model reads each anchor's own table.

Synthetic handoffs plus one retained TDG CP-1 handoff (runs/cpos-tdg-model-001, FY2022-FY2024,
USD millions, historical); expected values are literal source spellings.
"""

import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii.contracts import Run
from deploy_workflow.handoff_delivery import (
    HandoffInput,
    ModelDelivery,
    ModelPeriod,
    ModelRow,
    names_issuer,
)
from deploy_workflow.markdown_delivery import require_issuer
from deploy_workflow.model_handoff_delivery import _AnnualReader, build_model

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "runs/cpos-tdg-model-001"
GE = Run(
    run_id="r",
    issuer_id="ge-aerospace",
    issuer_name="GE Aerospace",
    as_of=date(2025, 12, 31),
    case_kind="public",
    pathway="credit_snapshot",
    requested_modules=("CP-2",),
)


def test_short_alias_inside_another_word_does_not_identify_the_issuer():
    lines = [
        "# CP-2 Rolls-Royce Holdings plc",
        "## Request",
        "Rolls-Royce Holdings plc, large-cap engine maker, as of 2025-12-31.",
        "## Sources",
    ]
    with pytest.raises(ValueError, match="markdown_issuer"):
        require_issuer(GE, ("GE",), "CP-2", lines)


def test_whole_word_alias_name_or_id_identifies_the_issuer():
    for title in ("# CP-2 GE", "# CP-2 for ge  aerospace", "# CP-2 ge-aerospace (Q4)"):
        require_issuer(GE, ("GE",), "CP-2", [title, "## Request", "As of 2025-12-31.", "## X"])


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Acme Corp. FY2024", True),
        ("Acme's 2024 results", True),
        ("Acmeco is a peer", False),
        ("NotAcme Holdings", False),
        ("ACME\nCORP", True),
    ],
)
def test_names_issuer_is_case_and_space_insensitive_on_word_boundaries(text, expected):
    assert names_issuer(text, ("Acme Corp", "Acme")) is expected


ANNUAL = b"""# CP-1 Acme
## Request
Acme.
## Sources
x
## Findings
### T4.6 - Balance sheet
Balance sheet not supplied in this revision.
### T4.7 - Pro forma debt schedule after the 2025 add-on
| Line | FY2024 |
|---|---|
| Long-term debt | 9,999 |
**Bridge (PDF 53):**
Not reproduced.
**Other bridge:**
| Reported row | FY2024 |
|---|---|
| EBITDA | 512 |
## Calculations
None.
## Gaps
Balance sheet missing.
## Next module
x
"""


def reader(raw: bytes = ANNUAL) -> _AnnualReader:
    layout = ModelDelivery(
        periods={
            "FY2024": ModelPeriod(
                start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), balance_column="FY2024"
            )
        },
        anchors={"balance": "### T4.6 - Balance sheet", "issuer_bridge": "**Bridge (PDF 53):**"},
        rows={
            "debt_long_term": ModelRow(table="balance", label="Long-term debt"),
            "issuer_ordinary_ebitda": ModelRow(table="issuer_bridge", label="EBITDA"),
        },
    )
    spec = HandoffInput(path="a.md", sha256=hashlib.sha256(raw).hexdigest())
    return _AnnualReader(raw, spec, layout)


def test_missing_anchored_table_is_an_explicit_gap_not_the_next_sections_table():
    cell = reader().read("debt_long_term", "FY2024")
    assert (cell.value, cell.reason, cell.sources) == (None, "NOT_SOURCED", ())
    assert cell.note == "No table under ### T4.6 - Balance sheet in this source"


def test_bold_label_anchor_stops_at_the_next_label():
    cell = reader().read("issuer_ordinary_ebitda", "FY2024")
    assert (cell.value, cell.reason) == (None, "NOT_SOURCED")


def tdg_inputs(old: bytes | None = None, new: bytes | None = None):
    from deploy_workflow.owners.cpos import HandoffPlan

    request = HandoffPlan.model_validate_json((CASE / "workflow.json").read_bytes())
    specs = {
        "annual": request.retained_handoffs["CP-1"],
        "current_synthesis": request.retained_handoffs["CP-2"],
    }
    raw = {k: (CASE / spec.path).read_bytes() for k, spec in specs.items()}
    if old is not None and new is not None:
        assert raw["annual"].count(old) >= 1
        raw["annual"] = raw["annual"].replace(old, new)
        specs["annual"] = HandoffInput(
            path="changed.md", sha256=hashlib.sha256(raw["annual"]).hexdigest()
        )
    layout = request.model.model_copy(update={"extra_handoffs": {}, "forecast_exact": None})
    return request.run, specs, raw, layout


def test_period_column_spelled_differently_is_refused_not_published_as_absent():
    old = b"| Row as reported | FY2024 | FY2023 | FY2022 |"
    run, specs, raw, layout = tdg_inputs(old, b"| Row as reported | FY2024A | FY2023 | FY2022 |")
    with pytest.raises(ValueError, match="model_period_column"):
        build_model(run, specs, raw, layout)


def test_model_history_shows_the_places_its_source_spells():
    run, specs, raw, layout = tdg_inputs()
    published = build_model(run, specs, raw, layout)
    facts = {f.fact_id: f for f in published.module.facts}
    assert (facts["history.revenue.FY2024"].amount, facts["history.revenue.FY2024"].decimals) == (
        Decimal(7940),
        0,
    )
    lexeme = facts["history.revenue.FY2024"].citations[0].quote
    assert "7,940" in lexeme
    old = lexeme.encode()
    new = old.replace(b"7,940", b"7,940.5", 1)
    run, specs, raw, layout = tdg_inputs(old, new)
    facts = {f.fact_id: f for f in build_model(run, specs, raw, layout).module.facts}
    assert (facts["history.revenue.FY2024"].amount, facts["history.revenue.FY2024"].decimals) == (
        Decimal("7940.5"),
        1,
    )
    assert facts["ratios.gross_carrying_multiple.FY2024"].decimals == 2  # declared ratio places


def test_a_sum_shows_its_most_precise_input_spelling():
    from deploy_vii.model.frame import Cell, SourceRef
    from deploy_workflow.model_handoff_delivery import _history_decimals

    parts = (SourceRef("annual", "line 1", "(1,234.25)"), SourceRef("annual", "line 2", "17.5"))
    assert _history_decimals(Cell(Decimal("-1216.75"), basis="CALCULATED", sources=parts)) == 2
    assert _history_decimals(Cell(None, "COMPONENT_MISSING")) == 0
