"""The financials gate measures SHC through the real tools (CP1H T14, offline proof for live run 3).

Live run 2's financials step failed only at the extraction and measurement layer: no statement
unit was located, and "no statement lines extracted" left the step "unmeasured". This test drives
the two real SHC financial filings through the live loop's own path (``SourceTools`` reads and
``extract_statements`` on exactly the answer key's units, then ``financial_workflow._evidence_issues``
for the ``financials`` step) with a schema-valid submission that holds no statement lines, so
the content checks run. It proves that the layer now passes, before any money is spent.

Answer keys (read, never written): ``cases/statement-units/shc-earnings-update.json`` and
``cases/statement-rows/shc-earnings-update.json``.

The pack is built directly as two line sources (converted by ``convert_html``, checked against the
key's ``converted_sha256``) on the shared test pack, not staged through ``stage_sources``: only the
two financial filings are converted, each once per module.
"""

import hashlib
import json
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from test_line_locators import FIN, make_pack

from deploy_vii.contracts import Span
from deploy_vii.cp1_workflow import FinancialSubmission
from deploy_vii.financial_contracts import FinancialPeriod
from deploy_vii.live.tools import (
    MAX_LINE_READ_BYTES,
    MAX_LINES_PER_EXTRACT,
    MAX_LINES_PER_READ,
    MAX_PAGES_PER_EXTRACT,
)
from deploy_vii.preparation import PreparedPack
from deploy_vii.source_context import SourceContextReview
from deploy_workflow import financial_workflow as fw
from deploy_workflow.html_text import convert_html
from deploy_workflow.statement_lines import LineTools, seen_tables
from deploy_workflow.tools.source import SourceTools
from deploy_workflow.workflow import SourceEvidence

REPO = Path(__file__).resolve().parents[1]
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")
CASE = "shc-earnings-update"
UNITS_KEY = REPO / "cases" / "statement-units" / f"{CASE}.json"
ROWS_KEY = REPO / "cases" / "statement-rows" / f"{CASE}.json"
HASH = hashlib.sha256(b"cp1h-t14 prefilled hash").hexdigest()  # the prefilled hash fields
FORBIDDEN = (
    "Financials must extract every located statement unit",
    "No statement unit is located in the financial sources",
    "Statement extraction is unmeasured",
    "Financials must read every supplied financial",
)


def _key(path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def _units_key() -> dict[str, dict[str, Any]]:
    """The key's sources that hold at least one unit, by source id."""
    return {s["source_id"]: s for s in _key(UNITS_KEY)["sources"] if s["units"]}


def _rows_key() -> dict[str, dict[str, Any]]:
    return {s["source_id"]: s for s in _key(ROWS_KEY)["sources"] if s["units"]}


@cache
def _lines(file: str, sha: str) -> tuple[str, ...]:
    """The converted lines of one corpus file, converted once and checked against the key."""
    if not CORPUS.is_dir():
        pytest.skip("public corpus directory absent (artifacts/public-corpus/v1)")
    path = CORPUS / file
    if not path.is_file():
        pytest.skip(f"{file} is absent from the public corpus")
    text = convert_html(path.read_bytes()).text
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
    return tuple(text.splitlines())


def _locator(unit: dict[str, Any]) -> str:
    return f"line:{unit['start'].split(':')[1]}-{unit['end'].split(':')[1]}"


class Gate:
    """The SHC financial pack, the tools after the loop's reads and extractions, the issues."""

    def __init__(self) -> None:
        keys = _units_key()
        self.ids = tuple(keys)
        base: PreparedPack = make_pack()
        financial = next(s for s in base.sources if s.source_id == FIN)
        line_sources = []
        self.lines: dict[str, tuple[str, ...]] = {}
        for source_id, item in keys.items():
            lines = _lines(item["file"], item["converted_sha256"])
            self.lines[source_id] = lines
            line_sources.append(
                financial.model_copy(
                    update={
                        "source_id": source_id,
                        "name": item["file"],
                        "sha256": item["converted_sha256"],
                        "spans": tuple(
                            Span(locator=f"line:{i}", text=text) for i, text in enumerate(lines, 1)
                        ),
                        "limitation": None,
                    }
                )
            )
        self.pack: PreparedPack = base.model_copy(
            update={
                "sources": (
                    *(s for s in base.sources if s.source_id != FIN),
                    *line_sources,
                )
            }
        )
        self.context = self._context()
        self.tools = SourceTools(self.pack, self.ids, extraction=True)
        for source_id in self.ids:
            self._read_every_line(source_id)
            self._extract_units(source_id, keys[source_id])
        evidence = self.tools.evidence()
        self.evidence = SourceEvidence(
            read=tuple((a, b) for a, b in evidence["read"]),
            extracted=tuple((a, b) for a, b in evidence["extracted"]),
            surfaced=tuple((a, b) for a, b in evidence["surfaced"]),
            searched=tuple(evidence["searched"]),
        )
        self.submission = self._submission()
        self.issues = list(self._issues())

    def _call(self, name: str, arguments: dict[str, Any]) -> str:
        body, staged = self.tools.stage(name, arguments)
        self.tools.commit(staged)
        return body

    def _read_every_line(self, source_id: str) -> None:
        """`read_pages` over the source's every line, in the largest ranges the limits allow."""
        lines = self.lines[source_id]
        first = 1
        while first <= len(lines):
            last, size = first, len(lines[first - 1].encode("utf-8"))
            while (
                last < len(lines)
                and last - first + 1 < MAX_LINES_PER_READ
                and size + len(lines[last].encode("utf-8")) <= MAX_LINE_READ_BYTES
            ):
                size += len(lines[last].encode("utf-8"))
                last += 1
            self._call(
                "read_pages", {"source_id": source_id, "first_page": first, "last_page": last}
            )
            first = last + 1

    def _extract_units(self, source_id: str, item: dict[str, Any]) -> None:
        """`extract_statements` on exactly the key's units, within the per-call limits."""
        batch: list[str] = []
        covered = 0
        for unit in item["units"]:
            size = int(unit["end"].split(":")[1]) - int(unit["start"].split(":")[1]) + 1
            if batch and (
                len(batch) == MAX_PAGES_PER_EXTRACT or covered + size > MAX_LINES_PER_EXTRACT
            ):
                self._call("extract_statements", {"source_id": source_id, "locators": batch})
                batch, covered = [], 0
            batch.append(_locator(unit))
            covered += size
        if batch:
            self._call("extract_statements", {"source_id": source_id, "locators": batch})

    def _context(self) -> SourceContextReview:
        """A source-context review that classifies the two filings as financial sources."""
        return SourceContextReview.model_validate_json(
            json.dumps(
                {
                    "pack_sha256": HASH,
                    "entities": [],
                    "sources": [
                        {
                            "source_id": source_id,
                            "classification": "financial",
                            "document_type": "SEC filing",
                            "published_on": None,
                            "evidence_class": None,
                            "evidence_rationale": "Sotera Health periodic filing",
                            "analytical_use": "statement lines",
                            "citations": [],
                            "event_scan_explanation": "Not assessed in this test",
                        }
                        for source_id in self.ids
                    ],
                }
            )
        )

    def _submission(self) -> str:
        """A schema-valid financials submission with no statement lines (the periods are the
        filings' own, in `PERIODS`)."""
        first = self.ids[0]
        cite = {
            "source_id": first,
            "source_sha256": _units_key()[first]["converted_sha256"],
            "locator": "line:1",
            "quote": self.lines[first][0],
        }
        disclosure = {
            "status": "not_disclosed",
            "explanation": "Not read here",
            "citations": [cite],
        }
        book = {
            "book_id": "consolidated",
            "entity_perimeter": "Sotera Health Company consolidated",
            "accounting_basis": "US GAAP",
            "currency": "USD",
            "unit": "THOUSANDS",
            "periods": [_period_json(p) for p in PERIODS],
            "accounts": [],
            "addbacks": [],
            "segments": [],
            "kpis": [],
            "facilities": [],
            "pro_forma": [],
            "segment_allocation": [],
            "addback_disclosure": disclosure,
            "segment_disclosure": disclosure,
        }
        return json.dumps(
            {
                "context_step_sha256": HASH,
                "financial": {
                    "pack_sha256": HASH,
                    "run_id": CASE,
                    "issuer_id": "shc",
                    "as_of": "2025-08-08",
                    "books": [book],
                    "analysis": [],
                },
                "definition": {"financial_review_sha256": HASH, "book_id": "consolidated"},
                "binding": {
                    "financial_review_sha256": HASH,
                    "source_context_review_sha256": HASH,
                    "books": [{"book_id": "consolidated", "entity_id": "shc"}],
                },
            }
        )

    def _issues(self) -> tuple[str, ...]:
        context = self.context.model_dump_json()
        store = SimpleNamespace(
            read=lambda: SimpleNamespace(
                attempts=[
                    SimpleNamespace(ticket_id="t", steps=[SimpleNamespace(payload_sha256="c")])
                ]
            ),
            payload=lambda _sha: context,
            pack=lambda: self.pack,
        )
        binding = SimpleNamespace(step_id="financials", ticket_id="t")
        return fw._evidence_issues(
            cast(Any, store), cast(Any, binding), self.submission, self.evidence
        )


# The SHC filings' own periods (calendar fiscal year): the 10-Q's quarter and year-to-date columns
# and its balance dates, the 10-K's fiscal years and its balance dates. (id, type, fiscal year,
# quarter, start, end, days, the header line citing it as (source, line number, quote))
Q10 = "SHC_2025-06-30_10-Q_0001822479-25-000044_shc-20250630"
K10 = "SHC_2024-12-31_10-K_0001822479-25-000015_shc-20241231"
THREE = (Q10, 83, "Three Months Ended June 30,")
SIX = (Q10, 83, "Six Months Ended June 30,")
YEAR = (K10, 268, "Year Ended December 31,")
PERIODS = (
    ("q2-2025", "QUARTER", "FY2025", 2, "2025-04-01", "2025-06-30", 91, THREE),
    ("q2-2024", "QUARTER", "FY2024", 2, "2024-04-01", "2024-06-30", 91, THREE),
    ("ytd6-2025", "YTD", "FY2025", None, "2025-01-01", "2025-06-30", 181, SIX),
    ("ytd6-2024", "YTD", "FY2024", None, "2024-01-01", "2024-06-30", 182, SIX),
    ("fy-2024", "FY", "FY2024", None, "2024-01-01", "2024-12-31", 366, YEAR),
    ("fy-2023", "FY", "FY2023", None, "2023-01-01", "2023-12-31", 365, YEAR),
    ("fy-2022", "FY", "FY2022", None, "2022-01-01", "2022-12-31", 365, YEAR),
    (
        *("end-2025-06-30", "PERIOD_END", "FY2025", None, None, "2025-06-30", None),
        (Q10, 35, "June 30, 2025"),
    ),
    (
        *("end-2024-12-31", "PERIOD_END", "FY2024", None, None, "2024-12-31", None),
        (Q10, 35, "December 31, 2024"),
    ),
    (
        *("end-2023-12-31", "PERIOD_END", "FY2023", None, None, "2023-12-31", None),
        (K10, 218, "As of December 31,"),
    ),
)


def _period_json(period: tuple[Any, ...]) -> dict[str, Any]:
    period_id, kind, year, quarter, start, end, days, (source_id, number, quote) = period
    item = _units_key()[source_id]
    text = _lines(item["file"], item["converted_sha256"])[number - 1]
    assert quote in text, (source_id, number, quote)
    found: dict[str, Any] = {
        "period_id": period_id,
        "fiscal_year": year,
        "fiscal_quarter": quarter,
        "period_type": kind,
        "start_date": start,
        "end_date": end,
        "day_count": days,
        "audit_status": "unaudited",
        "currency": "USD",
        "unit": "THOUSANDS",
        "accounting_basis": "US GAAP",
        "entity_perimeter": "Sotera Health Company consolidated",
        "citations": [
            {
                "source_id": source_id,
                "source_sha256": item["converted_sha256"],
                "locator": f"line:{number}",
                "quote": quote,
            }
        ],
    }
    if start is None:
        found["limitation"] = "A balance date: the filing states no start date"
    return found


@pytest.fixture(scope="module")
def gate() -> Gate:
    return Gate()


def _shc_periods() -> list[Any]:
    """The `PERIODS` as the objects `_column_periods` reads (the validated contract periods)."""
    return [FinancialPeriod.model_validate_json(json.dumps(_period_json(p))) for p in PERIODS]


def test_none_of_the_live_run_2_refusals_appears_and_every_row_is_measured(gate: Gate) -> None:
    # the submission parses, so the gate reaches its measurement (it returns early otherwise)
    FinancialSubmission.model_validate_json(gate.submission)
    for text in FORBIDDEN:
        assert not [issue for issue in gate.issues if text in issue], (text, gate.issues)
    # the submission holds no statement lines, so the gate reports every extracted row uncovered
    prefix = "Uncovered extracted statement line: "
    # each issue appends "; <first failing check>" (T16): compare the exact prefix up to it
    got = [issue.partition("; ")[0] for issue in gate.issues if issue.startswith(prefix)]
    want = [
        f"{prefix}{source_id} {_locator(unit)} line {row['line']}"
        for source_id, item in _rows_key().items()
        for unit in item["units"]
        for row in unit["rows"]
    ]
    assert len(want) == 215
    assert len(got) == len(set(got))
    assert set(got) == set(want)


def test_the_key_units_are_what_the_gate_locates_and_extracts(gate: Gate) -> None:
    key = _units_key()
    for source_id, item in key.items():
        source = next(s for s in gate.pack.sources if s.source_id == source_id)
        located = sorted(fw._statement_units(source.spans))
        assert located == sorted(_locator(u) for u in item["units"]), source_id
        extracted = {loc for src, loc in gate.evidence.extracted if src == source_id}
        assert {_locator(u) for u in item["units"]} <= extracted


def test_the_measured_tables_hold_exactly_the_rows_key(gate: Gate) -> None:
    tables = seen_tables(LineTools(gate.pack, sources=gate.ids), gate.evidence.seen(), gate.context)
    got = {
        (t.source_id, t.locator): [(r.line_no, r.label, list(r.raw_values)) for r in t.lines]
        for t in tables
    }
    want = {
        (source_id, _locator(unit)): [
            (r["line"], r["label"], r["raw_values"]) for r in unit["rows"]
        ]
        for source_id, item in _rows_key().items()
        for unit in item["units"]
    }
    assert len(want) == 6
    assert got == want


def test_every_shc_table_header_maps_its_columns(gate: Gate) -> None:
    tables = seen_tables(LineTools(gate.pack, sources=gate.ids), gate.evidence.seen(), gate.context)
    periods = _shc_periods()
    assert len(tables) == 6
    for table in tables:
        headers = tuple(table.headers)
        assert any(fw._spec_row(headers, i) is not None for i in range(len(headers))), headers
        columns = fw._column_periods(headers, periods)
        assert columns is not None, (table.source_id, table.locator, headers)
        assert table.lines
        assert {len(columns)} == {len(line.values) for line in table.lines}, (
            table.source_id,
            table.locator,
        )
