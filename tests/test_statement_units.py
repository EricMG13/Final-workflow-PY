"""Statement units located in line sources (CP1H-R18, T12).

`cases/statement-units/*.json` is the frozen answer key: per source the BS, IS and CFS units as
`line:S`/`line:E` of the repo's `convert_html` output, or `none` entries. The key is read, never
written, here.
"""

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import o2_case
import pytest
from test_line_locators import FIN, H_BS, H_IS, HEADER, ROWS, _issues, _line_spans, _with_spans

from deploy_workflow import earnings_workflow as ew
from deploy_workflow import financial_workflow as fw
from deploy_workflow.html_text import convert_html
from deploy_workflow.workflow import SourceEvidence

REPO = Path(__file__).resolve().parents[1]
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")
KEYS = sorted((REPO / "cases" / "statement-units").glob("*.json"))
SOURCES = 22
NOT_EXTRACTED = "Financials must extract every located statement unit: "
NO_UNIT = "No statement unit is located in the financial sources"


def _key_sources() -> Iterator[Any]:
    for key in KEYS:
        data = json.loads(key.read_text(encoding="utf-8"))
        for source in data["sources"]:
            yield pytest.param(source, id=f"{data['case']}/{source['source_id']}")


def _locator(key: dict[str, str]) -> str:
    return f"line:{key['start'].split(':')[1]}-{key['end'].split(':')[1]}"


def test_the_key_holds_every_source() -> None:
    assert len(list(_key_sources())) == SOURCES


@pytest.mark.parametrize("source", _key_sources())
def test_the_units_of_a_converted_filing_are_the_key_units(source: dict[str, Any]) -> None:
    if not CORPUS.is_dir():
        pytest.skip("public corpus directory absent (artifacts/public-corpus/v1)")
    path = CORPUS / source["file"]
    if path.suffix.lower() not in {".htm", ".html"} or not path.is_file():
        pytest.skip(f"{source['file']} is not a converted corpus file")
    text = convert_html(path.read_bytes()).text
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == source["converted_sha256"]
    spans = _line_spans(text.splitlines())
    assert set(fw._statement_units(spans)) == {_locator(unit) for unit in source["units"]}


TWO_UNITS = [H_IS, HEADER, ROWS[0], H_BS, HEADER, ROWS[1]]  # line:1-3 and line:4-6


def test_the_refusal_names_the_one_missing_unit(monkeypatch: pytest.MonkeyPatch) -> None:  # (d)
    pack = _with_spans(_line_spans(TWO_UNITS))
    units, issues = _issues(monkeypatch, pack, leave=("line:4-6",))
    assert list(units) == ["line:1-3", "line:4-6"]
    assert f"{NOT_EXTRACTED}{FIN} line:4-6" in issues


def test_the_refusal_lists_every_missing_unit_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    pack = _with_spans(_line_spans(TWO_UNITS))
    _, issues = _issues(monkeypatch, pack, extract_all=False)
    assert f"{NOT_EXTRACTED}{FIN} line:1-3, {FIN} line:4-6" in issues


def test_nothing_is_refused_when_every_unit_is_extracted(monkeypatch: pytest.MonkeyPatch) -> None:
    pack = _with_spans(_line_spans(TWO_UNITS))
    _, issues = _issues(monkeypatch, pack)
    assert not [i for i in issues if i.startswith(NOT_EXTRACTED) or i == NO_UNIT]


def test_a_ready_line_source_with_no_title_gets_the_no_unit_text_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # (c)
    pack = _with_spans(_line_spans([HEADER, *ROWS]))
    units, issues = _issues(monkeypatch, pack)
    assert units == {}
    assert NO_UNIT in issues
    assert not [i for i in issues if i.startswith(NOT_EXTRACTED)]


def _earnings_issues(pack: Any, extracted: tuple[tuple[str, str], ...]) -> list[str]:
    context = o2_case.payload_for("source_context")
    store = SimpleNamespace(
        read=lambda: SimpleNamespace(
            attempts=[SimpleNamespace(ticket_id="t", steps=[SimpleNamespace(payload_sha256="c")])]
        ),
        payload=lambda _sha: context,
        pack=lambda: pack,
    )
    source = next(s for s in pack.sources if s.source_id == FIN)
    evidence = SourceEvidence(
        read=tuple((FIN, span.locator) for span in source.spans), extracted=extracted
    )
    binding = SimpleNamespace(step_id="financials", ticket_id="t")
    return list(ew._source_issues(cast(Any, store), cast(Any, binding), "x", evidence, ()))


def test_the_earnings_workflow_requires_the_units_the_financial_workflow_locates() -> None:
    spans = _line_spans(["Consolidated Balance Sheets", HEADER, ROWS[0], H_IS, HEADER, ROWS[1]])
    pack = _with_spans(spans)
    financial = next(s for s in pack.sources if s.source_id == FIN)
    located = list(fw._statement_units(financial.spans))
    assert located == ["line:1-3", "line:4-6"]
    missing = _earnings_issues(pack, ())
    assert f"{NOT_EXTRACTED}{FIN} line:1-3, {FIN} line:4-6" in missing
    partial = _earnings_issues(pack, ((FIN, "line:1-3"),))
    assert f"{NOT_EXTRACTED}{FIN} line:4-6" in partial
    done = _earnings_issues(pack, tuple((FIN, locator) for locator in located))
    assert not [i for i in done if i.startswith(NOT_EXTRACTED) or i == NO_UNIT]


def test_the_earnings_workflow_gives_the_no_unit_text() -> None:
    issues = _earnings_issues(_with_spans(_line_spans([HEADER, *ROWS])), ())
    assert NO_UNIT in issues
    assert not [i for i in issues if i.startswith(NOT_EXTRACTED)]


# The reviewer's probe lines (parent-only, period and dash variants of real title lines) and its
# answers, verbatim: the kinds of title `_title_kinds` finds in each.
VARIANTS = [
    (
        "LIFE TIME GROUP HOLDINGS, INC. (PARENT COMPANY ONLY) CONDENSED BALANCE SHEETS (In thousands)",
        [],
    ),
    ("LIFE TIME GROUP HOLDINGS, INC. (PARENT COMPANY) CONDENSED BALANCE SHEETS (In thousands)", []),
    (
        "LIFE TIME GROUP HOLDINGS, INC. PARENT COMPANY ONLY CONDENSED BALANCE SHEETS (In thousands)",
        [],
    ),
    (
        "SCHEDULE I CONDENSED FINANCIAL INFORMATION OF REGISTRANT LIFE TIME GROUP HOLDINGS, INC. CONDENSED BALANCE SHEETS (In thousands)",
        [],
    ),
    (
        "LIFE TIME GROUP HOLDINGS, INC. CONDENSED BALANCE SHEETS (PARENT COMPANY ONLY) (In thousands)",
        [],
    ),
    (
        "F-2 Table of Contents TRANSDIGM GROUP INCORPORATED CONSOLIDATED BALANCE SHEETS AS OF SEPTEMBER 30, 2024 AND 2023 (Amounts in millions, except share amounts)",
        ["BS"],
    ),
    (
        "F-3 Table of Contents TRANSDIGM GROUP INCORPORATED CONSOLIDATED STATEMENTS OF INCOME FOR THE FISCAL YEARS ENDED SEPTEMBER 30, 2024, 2023 AND 2022 (Amounts in millions)",
        ["IS"],
    ),
    (
        "F-6 Table of Contents TRANSDIGM GROUP INCORPORATED CONSOLIDATED STATEMENTS OF CASH FLOWS FOR THE FISCAL YEARS ENDED SEPTEMBER 30, 2024, 2023 AND 2022 (Amounts in millions)",
        ["CFS"],
    ),
    (
        "XYZ CORP CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS FOR THE THREE AND SIX MONTHS ENDED JUNE 30, 2025 AND 2024 (Unaudited)",
        ["IS"],
    ),
    (
        "XYZ CORP CONDENSED CONSOLIDATED BALANCE SHEETS AS OF JUNE 30, 2025 (UNAUDITED) AND DECEMBER 31, 2024",
        ["BS"],
    ),
    ("XYZ Corp Condensed Consolidated Balance Sheets – Unaudited (In millions)", ["BS"]),
    ("Condensed Consolidating Balance Sheet As of December 31, 2024", []),
]


@pytest.mark.parametrize(("line", "want"), VARIANTS)
def test_title_variants_are_read_as_the_reviewer_reads_them(line: str, want: list[str]) -> None:
    assert sorted(fw._title_kinds(line)) == want


def _units(lines: list[str]) -> list[str]:
    return list(fw._statement_units(_line_spans(lines)))


CFS = "XYZ Corp Consolidated Statements of Cash Flows (In millions)"
NOTES = "Notes to Consolidated Financial Statements"


def test_a_continued_cfs_title_and_see_notes_footers_leave_one_unit() -> None:  # L2
    lines = [
        CFS,
        HEADER,
        ROWS[0],
        "(See Notes to Consolidated Financial Statements)",
        "See accompanying notes to consolidated financial statements.",
        "The Notes to Consolidated Financial Statements are an integral part of these statements.",
        "XYZ Corp Consolidated Statements of Cash Flows (Continued)",
        HEADER,
        ROWS[1],
        NOTES,
    ]
    assert _units(lines) == ["line:1-9"]


def test_schedule_i_after_the_notes_is_not_a_unit_and_contents_is_not_the_cutoff() -> None:  # M1
    lines = [
        (
            "Notes to Consolidated Financial Statements for Fiscal Years Ended September 30, 2024, "
            "2023 and 2022 F-8 to F-45"
        ),
        "Consolidated Balance Sheets",
        HEADER,
        ROWS[0],
        "Consolidated Statements of Operations",
        HEADER,
        ROWS[0],
        "Consolidated Statements of Cash Flows",
        HEADER,
        ROWS[0],
        NOTES + " (Unaudited)",
        "Note 1. Basis of presentation",
        "Condensed Balance Sheets (In thousands)",
        HEADER,
        ROWS[0],
        "Condensed Statements of Operations (In thousands)",
        HEADER,
    ]
    assert _units(lines) == ["line:2-4", "line:5-7", "line:8-10"]


N = "NOTES TO CONSOLIDATED FINANCIAL STATEMENTS"
# The re-review's probe lines and answers, verbatim (t12-2/probe_new_risks.py).
RISKS = [
    (
        (
            "XYZ HOLDINGS, INC. AND SUBSIDIARIES " + N + " (UNAUDITED) NOTE 1 - ORGANIZATION "
            "XYZ Holdings, Inc. (the Parent Company) owns"
        ),
        ["NOTES"],
    ),
    (
        (
            "XYZ HOLDINGS, INC. AND SUBSIDIARIES " + N + " NOTE 1 - BASIS OF PRESENTATION "
            "The registrant and its subsidiaries"
        ),
        ["NOTES"],
    ),
    (
        (
            "XYZ HOLDINGS, INC. AND SUBSIDIARIES " + N + " NOTE 1 - BASIS "
            "Principles of consolidation; consolidating variable interest entities"
        ),
        ["NOTES"],
    ),
    ("Notes to Consolidated Financial Statements F-7 through F-40", []),
    ("Notes to Consolidated Financial Statements Page 7", []),
    ("Notes to Condensed Consolidated Financial Statements (Unaudited) 6", []),
    ("Notes to Consolidated Financial Statements .......... 9", []),
    ("Notes to Consolidated Financial Statements 8 - 25", []),
    ("CONSOLIDATED BALANCE SHEETS (In millions) Registrant's own shares excluded", []),
    ("PARENT COMPANY HOLDINGS LLC CONSOLIDATED BALANCE SHEETS (In thousands)", ["BS"]),
    (
        (
            "CONSOLIDATED STATEMENTS OF OPERATIONS FOR THE THREE AND NINE MONTHS ENDED "
            "SEPTEMBER 30, 2024 AND 2023 (UNAUDITED)"
        ),
        ["IS"],
    ),
    (
        (
            "CONSOLIDATED STATEMENTS OF CASH FLOWS FOR THE NINE MONTHS ENDED SEPTEMBER 30, 2024 "
            "AND 2023 (Unaudited)"
        ),
        ["CFS"],
    ),
    ("Consolidated Balance Sheets - (Continued)", ["BS"]),
]


@pytest.mark.parametrize(("line", "want"), RISKS)
def test_notes_and_contents_and_marker_lines(line: str, want: list[str]) -> None:
    assert sorted(fw._title_kinds(line)) == want


def test_a_notes_title_naming_the_parent_company_still_ends_the_cfs_unit() -> None:
    lines = [
        "XYZ CORP CONSOLIDATED STATEMENTS OF CASH FLOWS (UNAUDITED)",
        HEADER,
        ROWS[0],
        (
            "XYZ HOLDINGS, INC. AND SUBSIDIARIES " + N + " (UNAUDITED) NOTE 1 - BASIS OF "
            "PRESENTATION iHeartMedia, Inc., the parent company of iHeartCommunications, Inc.,"
        ),
    ]
    assert _units(lines) == ["line:1-3"]


def test_a_contents_notes_entry_with_a_page_range_is_not_the_cutoff() -> None:
    lines = [
        "INDEX TO CONSOLIDATED FINANCIAL STATEMENTS",
        "Consolidated Balance Sheets F-3",
        "Consolidated Statements of Operations F-4",
        "Consolidated Statements of Cash Flows F-6",
        "Notes to Consolidated Financial Statements F-7 through F-40",
        "XYZ CORP CONSOLIDATED BALANCE SHEETS (In millions)",
        "Cash 1 2",
        "XYZ CORP CONSOLIDATED STATEMENTS OF OPERATIONS (In millions)",
        "Revenue 1 2",
        "XYZ CORP CONSOLIDATED STATEMENTS OF CASH FLOWS (In millions)",
        "Net income 1 2",
        "XYZ CORP " + N,
        "Note 1",
    ]
    assert _units(lines) == ["line:6-7", "line:8-9", "line:10-11"]


@pytest.mark.parametrize(
    "form",
    [
        "Consolidated Statements of Cash Flows (Continued)",
        "Consolidated Statements of Cash Flows (Continued) (In millions)",
        "Consolidated Statements of Cash Flows — Continued",
        (
            "Consolidated Statements of Cash Flows (continued) for the years ended December 31, "
            "2024 and 2023"
        ),
    ],
)
def test_every_continued_form_keeps_one_unit(form: str) -> None:
    lines = [
        "Consolidated Statements of Cash Flows (In millions)",
        "Net income 1 2",
        form,
        "Cash end 1 2",
        NOTES,
        "Note 1",
    ]
    assert _units(lines) == ["line:1-4"]
