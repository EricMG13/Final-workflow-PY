"""Statement units located on PDF page sources (CP1H-R23, T20).

`cases/pdf-units/<DOC>.json` is the frozen answer key and `tests/fixtures/pdf_pages/<DOC>/pNNN.txt`
the exact product intake text of the key's pages. A source is built from a document's fixture pages
only. The key and the fixtures are read, never written, here.
"""

import json
from pathlib import Path
from typing import Any, cast

import czr_runs
import pytest

from deploy_vii.contracts import Span
from deploy_workflow import financial_workflow as fw

REPO = Path(__file__).resolve().parents[1]
KEYS = sorted((REPO / "cases" / "pdf-units").glob("*.json"))
DOCS = [pytest.param(key, id=key.stem) for key in KEYS]


def _spans(doc: str) -> list[Span]:
    pages = sorted((REPO / "tests" / "fixtures" / "pdf_pages" / doc).glob("p*.txt"))
    return [
        Span(locator=f"page:{int(page.stem[1:])}", text=page.read_text(encoding="utf-8"))
        for page in pages
    ]


def _key(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _expected(key: dict[str, Any]) -> dict[str, str]:
    """The key's BS, IS, CI and CFS pages by locator, with their kind (CI is IS)."""
    expected: dict[str, str] = {}
    for unit in key["units"]:
        if unit["kind"] == "SE":
            continue
        for page in unit["pages"]:
            expected[f"page:{page}"] = "IS" if unit["kind"] == "CI" else unit["kind"]
    return expected


CZR_PACK_UNITS = {
    "czr-fy2025-10k": {
        "page:54": "BS",
        "page:56": "IS",
        "page:57": "IS",
        "page:60": "CFS",
        "page:61": "CFS",
    },
    "czr-q2-2026-10q": {
        "page:2": "BS",
        "page:4": "IS",
        "page:5": "IS",
        "page:9": "CFS",
        "page:10": "CFS",
    },
    "czr-q2-2026-release": {"page:6": "IS"},
}


@pytest.mark.parametrize("source_id", sorted(CZR_PACK_UNITS))
def test_czr_pack_units_and_kinds_are_the_controller_key(source_id: str) -> None:
    """The three CZR documents of `czr_runs.make_pack()`: the release's segment table and
    non-GAAP reconciliation are not units; the 10-K and 10-Q continuation and comprehensive
    income pages are."""
    source = next(s for s in czr_runs.make_pack().sources if s.source_id == source_id)
    assert set(fw._statement_units(source.spans)) == set(CZR_PACK_UNITS[source_id])
    assert fw._statement_kinds(source.spans) == CZR_PACK_UNITS[source_id]


def test_keys_are_present() -> None:
    assert len(KEYS) == 6


@pytest.mark.parametrize("path", DOCS)
def test_page_units_are_the_key_pages(path: Path) -> None:
    key = _key(path)
    spans = _spans(key["doc"])
    assert spans
    located = fw._statement_units(spans)
    assert set(located) == set(_expected(key))
    for locator, text in located.items():
        assert text == next(s.text for s in spans if s.locator == locator)


@pytest.mark.parametrize("path", DOCS)
def test_page_unit_kinds_are_the_key_kinds(path: Path) -> None:
    key = _key(path)
    assert fw._statement_kinds(_spans(key["doc"])) == _expected(key)


@pytest.mark.parametrize("path", DOCS)
def test_no_other_fixture_page_is_located(path: Path) -> None:
    key = _key(path)
    spans = _spans(key["doc"])
    others = {s.locator for s in spans} - set(_expected(key))
    assert others
    assert not others & set(fw._statement_units(spans))


def test_company_only_pages_are_not_located() -> None:
    spans = _spans("VMED25")
    assert {"page:172", "page:173"} <= {s.locator for s in spans}
    assert not {"page:172", "page:173"} & set(fw._statement_units(spans))


def test_a_continuation_page_takes_the_previous_pages_kind() -> None:
    kinds = fw._statement_kinds(_spans("CZR"))
    assert kinds["page:60"] == "CFS"
    assert kinds["page:61"] == "CFS"


def _release_pages() -> dict[str, str]:
    pack = czr_runs.make_pack()
    source = next(s for s in pack.sources if s.source_id == "czr-q2-2026-release")
    return {s.locator: s.text for s in source.spans}


def _retitled(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new, 1)


RELEASE_IS_TITLE = "CONSOLIDATED CONDENSED STATEMENTS OF OPERATIONS"
RELEASE_P7_CAPTION = (
    "RECONCILIATION OF NET INCOME (LOSS) ATTRIBUTABLE TO CAESARS TO ADJUSTED EBITDA\n(UNAUDITED)"
)
TITLE_CASE_CAPTION = (
    "Reconciliation of Net Income (Loss) Attributable to Caesars to Adjusted EBITDA"
)


@pytest.mark.parametrize(
    "title",
    [
        "Consolidated Statement of Profit or Loss and Other Comprehensive Income",
        "Consolidated Statement of Profit or Loss for the year ended December 31, 2025",
        "Consolidated Statements of Income and Other Comprehensive Income",
        "Statements of Profit or (Loss)",
    ],
)
def test_ifrs_and_other_comprehensive_titles_are_income_statements(title: str) -> None:
    text = _retitled(_release_pages()["page:6"], RELEASE_IS_TITLE, title)
    spans = [Span(locator="page:1", text=text)]
    assert fw._statement_kinds(spans) == {"page:1": "IS"}
    assert set(fw._statement_units(spans)) == {"page:1"}


def test_a_section_heading_with_a_statement_name_is_not_a_title() -> None:
    text = _retitled(_release_pages()["page:6"], RELEASE_IS_TITLE, "Balance Sheet and Liquidity")
    assert not fw._statement_units([Span(locator="page:1", text=text)])


@pytest.mark.parametrize(
    "caption",
    [
        TITLE_CASE_CAPTION + "\n(Unaudited)",
        f"{TITLE_CASE_CAPTION} (In millions)\n(Unaudited)",
        "Reconciliation (in millions)",
        f"(Amounts in millions, except per share data)\n{TITLE_CASE_CAPTION}\n(Unaudited)",
        f"Amounts in millions except per share data\n{TITLE_CASE_CAPTION}",
    ],
)
def test_a_title_case_reconciliation_after_the_income_statement_is_not_a_unit(caption: str) -> None:
    pages = _release_pages()
    text = _retitled(pages["page:7"], "CAESARS ENTERTAINMENT, INC.\n", "")
    text = _retitled(text, RELEASE_P7_CAPTION, caption)
    spans = [Span(locator="page:6", text=pages["page:6"]), Span(locator="page:7", text=text)]
    assert fw._statement_kinds(spans) == {"page:6": "IS"}
    assert set(fw._statement_units(spans)) == {"page:6"}


@pytest.mark.parametrize(
    "title",
    [
        "Company\nStatements of Financial Position",
        "Company Balance Sheet",
        "Company Balance Sheets",
        "Parent Company Statements of Financial Position",
    ],
)
def test_company_only_titles_are_not_located(title: str) -> None:
    page = (REPO / "tests/fixtures/pdf_pages/VMED25/p172.txt").read_text(encoding="utf-8")
    text = _retitled(page, "Company Statements of Financial Position", title)
    assert not fw._statement_units([Span(locator="page:172", text=text)])
