"""Bounded offline CP-1 participation, verified promotion and deterministic publication.

Execution and the adopted financial core own every calculation and settlement.
This adapter owns finite capabilities, immutable participation evidence and the
final C1 -> C2 receipt. Paths are supplied by trusted setup, never by a message.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Collection, Iterable, Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Literal, TextIO, cast
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from deploy_vii.canonical_tables import CanonicalTables
from deploy_vii.contracts import Contract, Hash, Identifier, Input, Run, Span
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.cp1_quality import cp1_quality_inputs
from deploy_vii.cp1_workflow import (
    CP1_PROMOTION,
    PROMOTED,
    CP1Handoff,
    FinancialStage,
    FinancialSubmission,
    cp1_registers,
    promote_cp1,
    read_cp1_envelope,
    validate_cp1_stage,
    write_cp1_envelope,
)
from deploy_vii.cp_model_workflow import (
    PUBLISHED,
    CpModelRefused,
    publish_cp_model,
    verify_cp_model_publication,
)
from deploy_vii.downstream_readiness import DownstreamInputs, DownstreamReview
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    NotAuthorized,
    clipped,
    current_inputs,
)
from deploy_vii.financial_contracts import StatementLine
from deploy_vii.live.context import narrative_evidence, readiness_inputs
from deploy_vii.live.prompts import quality_scope
from deploy_vii.live.schema import exact_json, json_object, normalise
from deploy_vii.live.submission import (
    PREFILLED,
    STEPS,
    Known,
    known_bindings,
    prefill,
    submit_model_payload,
)
from deploy_vii.live.tools import ToolRules, cited_locators
from deploy_vii.model.history import OUTFLOW_METRICS
from deploy_vii.narrative import NarrativeReview
from deploy_vii.preparation import OCR_MARK, PreparedPack
from deploy_vii.quality import QualityReview, assess_quality
from deploy_vii.readiness import ReadinessReview
from deploy_vii.source_context import SourceContextReview
from deploy_vii.statement_extract import FOOTNOTE_MARKER, extract_statement_lines
from deploy_vii.statement_validation import ACCOUNT_LINKS
from deploy_workflow import pdf_headers
from deploy_workflow import statement_compose as sc
from deploy_workflow.host import SourceSession
from deploy_workflow.statement_lines import LineTools, respace, seen_tables
from deploy_workflow.tools.source import SourceError
from deploy_workflow.unit_maps import Expansion, UnitInputs, expand
from deploy_workflow.workflow import SourceEvidence, WorkflowError, _put, read_line

_LINE_LOCATOR = re.compile(r"line:([0-9]+)")
_PAGE_LOCATOR = re.compile(r"page:[0-9]+")
Step = Literal[
    "source_readiness", "source_context", "financials", "narrative", "readiness", "quality"
]
SOURCE_STEPS = ("source_readiness", "source_context", "financials")
FILES = ("model.html", "calculation.json", "receipt.json")
MAX_CALLS = 16
MAX_INVOKES = 64  # pack-tool calls per step (a safety net behind MAX_TURNS); source steps only
MAX_TURNS = 30  # model requests per (module, step, attempt); hybrid's measured bound
MAX_MESSAGES = 128
MAX_LINE = 4 * 1024 * 1024
# A located statement page holds a whole line that is a statement heading: the synthetic
# "[CONSOLIDATED] INCOME STATEMENT | CASH FLOW STATEMENT | BALANCE SHEET" and the filed SEC
# "CONSOLIDATED [CONDENSED] BALANCE SHEETS | STATEMENTS OF OPERATIONS | STATEMENTS OF CASH FLOWS".
# Comprehensive income and stockholders' equity statements are not located statements.
STATEMENT_HEADING = re.compile(
    r"^\s*(?:CONSOLIDATED\s+)?(?:CONDENSED\s+)?"
    r"(?:INCOME STATEMENT|CASH FLOW STATEMENT|BALANCE SHEETS?"
    r"|STATEMENTS OF OPERATIONS|STATEMENTS OF CASH FLOWS)\s*$",
    re.MULTILINE,
)
SCHEMAS: dict[str, type[Contract]] = {
    "source_readiness": ReadinessReview,
    "source_context": SourceContextReview,
    "financials": FinancialSubmission,
    "narrative": NarrativeReview,
    "readiness": DownstreamReview,
    "quality": QualityReview,
}


class FinancialBinding(Contract):
    run_id: Identifier
    issuer_id: Identifier
    as_of: str
    method_version: str
    pack_sha256: Hash
    snapshot_sha256: Hash
    module_id: Literal["CP-0", "CP-1"]
    step_id: Step
    ticket_id: Identifier
    attempt: int
    inputs: tuple[Input, ...]


class FinancialCall(Contract):
    schema_version: Literal["tool-receipt/1"]
    call_id: str
    sequence: int
    binding: FinancialBinding
    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "refused", "error"]
    body: str | None
    error_code: str | None
    source_evidence: SourceEvidence


class InputRead(Contract):
    binding: FinancialBinding
    sequence: int
    operation: Literal["read_inputs"] = "read_inputs"
    inputs_sha256: Hash
    body: str


class FinancialSubmissionBinding(Contract):
    schema_version: Literal["submission-binding/1"] = "submission-binding/1"
    binding: FinancialBinding
    payload_sha256: Hash
    successful_call_ids: tuple[str, ...]
    call_ids: tuple[str, ...]
    source_evidence: SourceEvidence


class StageSubmission(Contract):
    sequence: int
    binding: FinancialSubmissionBinding
    stored_payload_sha256: Hash
    canonical_review_sha256: Hash | None
    disposition: Literal["valid", "invalid", "refused"]
    issues: tuple[str, ...]
    snapshot_after_sha256: Hash
    nulls_resolved: tuple[str, ...] = ()
    prefilled: tuple[str, ...] = ()
    prefilled_kinds: tuple[str, ...] = ()
    step_sha256: Hash | None = None
    step_output_sha256: Hash | None = None


class PromotedRecord(Contract):
    ticket_id: Identifier
    result_sha256: Hash
    status: Literal["accepted", "restricted"]


class ModelPublication(Contract):
    ticket_id: Identifier
    result_sha256: Hash
    cp1_result_sha256: Hash
    files: dict[str, Hash]


class RefusedBegin(Contract):
    snapshot_sha256: Hash
    operation: Literal["begin_cp1"] = "begin_cp1"
    reason: str


class PublicationCall(Contract):
    snapshot_before_sha256: Hash
    snapshot_after_sha256: Hash
    status: Literal["published", "refused", "failed"]
    reason: str | None
    ticket_id: Identifier | None
    files: dict[str, Hash]


class FinancialSliceReceipt(Contract):
    schema_version: Literal["cp1-model-slice-receipt/1"] = "cp1-model-slice-receipt/1"
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    participant: str
    transport: Literal["python-api", "bounded-json-lines/1"]
    cp0: PromotedRecord
    cp1: PromotedRecord | None
    model: ModelPublication | None
    refusal: Literal["cp1_not_authorized"] | None
    calls: tuple[FinancialCall, ...]
    input_reads: tuple[InputRead, ...]
    submissions: tuple[StageSubmission, ...]
    refused_begin: RefusedBegin | None
    publications: tuple[PublicationCall, ...]


def _parse[T: BaseModel](model: type[T], value: Any) -> T:
    return model.model_validate_json(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _audit(store: Execution, kind: str, digest: str) -> Path:
    return store.directory / "financial-slice-audit" / kind / digest


def _retain(store: Execution, kind: str, value: Contract) -> None:
    _put(_audit(store, kind, value.content_hash()), value.model_dump_json().encode())


def _raw(store: Execution, digest: str) -> str:
    raw = _audit(store, "payloads", digest).read_bytes()
    if _hash(raw) != digest:
        raise WorkflowError("identity_mismatch")
    return raw.decode("utf-8")


def _snapshot(store: Execution, digest: str) -> ExecutionSnapshot:
    raw = (store.directory / "snapshots" / (digest + ".json")).read_bytes()
    snapshot = ExecutionSnapshot.model_validate_json(raw)
    if _hash(raw) != digest or snapshot.content_hash() != digest:
        raise WorkflowError("identity_mismatch")
    store.pack(snapshot)
    return snapshot


class _FrozenExecution(Execution):
    """A read-only historical view for core validation; never changes the journal."""

    def __init__(self, store: Execution, snapshot: ExecutionSnapshot) -> None:
        super().__init__(store.directory)
        self.snapshot = snapshot

    def read(self) -> ExecutionSnapshot:
        return self.snapshot

    def _write(self, snapshot: ExecutionSnapshot) -> None:
        raise WorkflowError("not_permitted")


def _binding(snapshot: ExecutionSnapshot, attempt: Attempt, step_id: str) -> FinancialBinding:
    return _parse(
        FinancialBinding,
        {
            "run_id": snapshot.run.run_id,
            "issuer_id": snapshot.run.issuer_id,
            "as_of": snapshot.run.as_of.isoformat(),
            "method_version": snapshot.run.method_version,
            "pack_sha256": snapshot.pack_sha256,
            "snapshot_sha256": snapshot.content_hash(),
            "module_id": attempt.module_id,
            "step_id": step_id,
            "ticket_id": attempt.ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
        },
    )


def _historical(store: Execution, binding: FinancialBinding) -> _FrozenExecution:
    snapshot = _snapshot(store, binding.snapshot_sha256)
    attempt = next(a for a in snapshot.attempts if a.ticket_id == binding.ticket_id)
    sequence = ("source_readiness",) if attempt.module_id == "CP-0" else CP1_PROMOTION
    if (
        _binding(snapshot, attempt, binding.step_id) != binding
        or attempt.status != "pending"
        or attempt.issues
        or attempt.interruption
        or attempt.payload_sha256 is not None
        or attempt.result_sha256 is not None
        or current_inputs(snapshot, attempt.module_id) != attempt.inputs
        or tuple(s.step_id for s in attempt.steps) != sequence[: len(attempt.steps)]
        or any(s.status != "valid" for s in attempt.steps)
        or len(attempt.steps) >= len(sequence)
        or sequence[len(attempt.steps)] != binding.step_id
    ):
        raise WorkflowError("identity_mismatch")
    return _FrozenExecution(store, snapshot)


def _quality_read(registers: CanonicalTables) -> tuple[str, str]:
    # Ruling item 87: serve prompts.quality_scope with each evidence record narrowed to
    # kind and reference; the review stays bound to the full QualityInputs hash.
    inputs = cp1_quality_inputs(registers)
    scope = quality_scope(registers, inputs)
    for entry in scope["evidence"]:
        entry["record"] = {key: entry["record"][key] for key in ("kind", "reference")}
    return inputs.content_hash(), json.dumps(scope, sort_keys=True, separators=(",", ":"))


def _projection(store: Execution, binding: FinancialBinding) -> tuple[str, str]:
    historical = _historical(store, binding)
    attempt = next(a for a in historical.read().attempts if a.ticket_id == binding.ticket_id)
    if binding.step_id == "quality":
        return _quality_read(cp1_registers(historical, attempt.ticket_id))
    if binding.step_id not in ("narrative", "readiness"):
        raise WorkflowError("not_permitted")
    for index, step in enumerate(attempt.steps, 1):
        outcome = validate_cp1_stage(
            historical,
            historical.pack(),
            attempt.model_copy(update={"steps": attempt.steps[:index]}),
        )
        if outcome.issues or not outcome.retained_as(step):
            raise WorkflowError("identity_mismatch")
    step = attempt.steps[-1]
    if step.output_sha256 is None:
        raise WorkflowError("identity_mismatch")
    raw = historical.step_output(step.output_sha256)
    if binding.step_id == "narrative":
        stage = FinancialStage.model_validate_json(raw)
        return stage.narrative_inputs.content_hash(), narrative_evidence(stage)
    downstream = DownstreamInputs.model_validate_json(raw)
    return downstream.content_hash(), readiness_inputs(downstream)


def _ready_hashes(pack: PreparedPack) -> dict[str, str]:
    """Each ready source's hash by id, as `known_bindings` reads them."""
    return {s.source_id: s.sha256 for s in pack.sources if s.status == "ready" and s.sha256}


def _filled(
    store: Execution, binding: FinancialBinding, payload: str
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if binding.step_id == "source_readiness":
        # CP1H-R15: the offered CP-0 schema drops `Citation.source_sha256` (DVII marks it
        # prefilled), so Python fills it from the pack. `pack_sha256` stays model-supplied.
        pack = store.pack()
        known = Known(pack_sha256=pack.content_hash(), sources=_ready_hashes(pack), step={})
        filled = prefill(ReadinessReview, payload, known, frozenset({"source"}))
        return filled.payload, (), filled.paths, filled.kinds
    model = STEPS[binding.step_id].schema
    normal, resolved = normalise(model, payload)
    filled = prefill(
        model,
        normal,
        known_bindings(store, binding.ticket_id, binding.step_id),
        PREFILLED[binding.step_id],
    )
    return filled.payload, resolved, filled.paths, filled.kinds


# A line source locates a statement unit at a line that holds a statement title in statement
# position (CP1H-R18). The forms: balance sheet(s) or statement(s) of financial position; of
# operations, income or earnings; of cash flows; the synthetic "income statement" and "cash flow
# statement"; each with optional "condensed" and "consolidated". Comprehensive income, equity and
# "Notes to ... financial statements" titles are not units but end one.
_TITLE_FORMS = {
    "BS": r"balance\s+sheets?|statements?\s+of\s+financial\s+position",
    "IS": r"statements?\s+of\s+(?:operations|income|earnings)|income\s+statements?",
    "CI": (
        r"statements?\s+of\s+comprehensive(?:\s*\((?:loss|income)\))?"
        r"(?:\s+(?:income|loss)(?:\s*\((?:loss|income)\))?)?"
    ),
    "CFS": r"statements?\s+of\s+cash\s+flows?|cash\s+flows?\s+statements?",
    "EQ": (
        r"statements?\s+of\s+(?:changes\s+in\s+)?"
        r"(?:(?:stockholders|shareholders|members|partners|owners)['\u2019]?\s+)?(?:equity|deficit)"
    ),
    "NOTES": (
        r"notes\s+to\s+(?:the\s+)?(?:(?:condensed|consolidated|combined|unaudited)\s+)*"
        r"financial\s+statements"
    ),
}
_TITLE = re.compile(
    r"(?<![\w-])(?:condensed\s+)?(?:consolidated\s+)?(?:"
    + "|".join(f"(?P<{kind}>{form})" for kind, form in _TITLE_FORMS.items())
    + ")",
    re.IGNORECASE,
)
# What may follow a title on its line, in any order: "of <Company>" or "and Comprehensive Income";
# a period ("for the three and six months ended <date>", "for the fiscal years ended <date>, <year>
# and <year>"); "as of <date> [(unaudited)] [and <date>]"; a parenthetical ("(Unaudited)", "(In
# millions)"); a dash suffix ("- Unaudited"). A page number or prose after it makes the line a
# contents entry or a mention.
_DATE = r"[A-Za-z]+\s+[0-9]{1,2},\s*[0-9]{4}"
_TITLE_TAIL = re.compile(
    r"(?:\s+(?:and|of|AND|OF)(?:\s+(?:(?!(?:AND|OF)\b)[A-Z][^\s()0-9:]*|in|&))*"
    r"|\s+(?i:(?:for\s+(?:the\s+)?)?(?:(?:three|six|nine|twelve)(?:\s+and\s+(?:three|six|nine|twelve))?"
    rf"\s+months|(?:fiscal\s+)?years?)\s+ended)\s+{_DATE}(?:\s*,\s*[0-9]{{4}})*"
    rf"(?:\s*,?\s+(?i:and)\s+(?:{_DATE}|[0-9]{{4}}))*"
    rf"|\s+(?i:as\s+of)\s+{_DATE}(?:\s*\([^()]*\))?(?:\s*,\s*[0-9]{{4}})*"
    rf"(?:\s*,?\s+(?i:and)\s+(?:{_DATE}|[0-9]{{4}}))*"
    r"|\s*\([^()]*\)"
    r"|\s*[\u2013\u2014-]+\s*(?i:\(?(?:unaudited|continued)\)?))*\s*"
)
# A marker that a statement title is not the consolidated primary one, searched in the text
# before the title, a newline, then the text after it: "Schedule I", "of the registrant" or
# "consolidating" before the title, "(Parent Company [Only])" or "Parent Only" just before it, a
# "(Parent ...)" or "(Registrant ...)" parenthetical just after it. The structural rule in
# `_line_unit_ranges` (no unit after the notes begin) is the main guard; this catches the same
# tables when they stand before any notes title. A statement kind only: a notes title may run on
# into the first note, which names the parent company.
_PARENT_ONLY = re.compile(
    r"\bschedule\s+i\b|\bof\s+(?:the\s+)?registrant\b|\bconsolidating\b"
    r"|\b(?:parent\s+company(?:\s+only)?|parent\s+only)\)?\s*\n"
    r"|\n\s*\(\s*(?:parent|registrant)\b[^()]*\)",
    re.IGNORECASE,
)
# A contents entry whose page number is the next line.
_PAGE_ONLY = re.compile(r"(?:[0-9]{1,3}|[ivxlc]+|[A-Z]-[0-9]{1,3})")
# A page source also takes the IFRS income statement title, "Statement(s) of Profit or (Loss)"
# (CP1H-R23); the line path's `_TITLE` is unchanged.
_PAGE_FORMS = {
    **_TITLE_FORMS,
    "IS": _TITLE_FORMS["IS"] + r"|statements?\s+of\s+profit\s+or\s+\(?loss\)?",
}
_PAGE_TITLE = re.compile(
    r"(?<![\w-])(?:condensed\s+)?(?:consolidated\s+)?(?:"
    + "|".join(f"(?P<{kind}>{form})" for kind, form in _PAGE_FORMS.items())
    + ")",
    re.IGNORECASE,
)
# On a page a statement title is not followed by "and" and anything but a comprehensive statement
# ("Balance Sheet and Liquidity" is a section heading of a release).
_PAGE_TAIL = re.compile(
    r"(?!\s+(?i:and)\s+(?!(?i:(?:other\s+)?comprehensive)))" + _TITLE_TAIL.pattern
)
# A period-header line: a four-digit year or "ended" (CP1H-R23.17). A unit line ("(In millions)",
# "Amounts in ...") is text, not a period header.
_PERIOD_HEADER = re.compile(r"\b(?:19|20)[0-9]{2}\b|\bended\b", re.IGNORECASE)
# A company-only statement of a group's annual report: "Company Statements of ..." or "Company
# Balance Sheet(s)" with neither "consolidated" nor "group" in the title line.
_COMPANY_ONLY = re.compile(
    r"company\s+(?:statements?|balance\s+sheets?)\b(?!.*\b(?:consolidated|group)\b)",
    re.IGNORECASE,
)
_COMPANY_WORD = re.compile(r"company", re.IGNORECASE)


def _title_kinds(
    text: str, pattern: re.Pattern[str] = _TITLE, tail: re.Pattern[str] = _TITLE_TAIL
) -> set[str]:
    """The kinds of the titles `text` holds in statement position. A title is not in statement
    position after a lowercase word (prose: "in the consolidated balance sheets"), after "See" or
    "(See" (a "See Notes to ..." footer), near a parent-company, registrant or consolidating
    marker, or when more than `_TITLE_TAIL` follows it on the line (a contents entry with a page
    number, "Balance Sheet Data:"). A notes title may be followed by the notes' first words but not
    by a page or page range ("Notes to ... Statements 70", "F-8 to F-45"), a closing bracket, or "are"/"is" ("The Notes
    to ... are an integral part")."""
    kinds: set[str] = set()
    for match in pattern.finditer(text):
        kind = match.lastgroup or ""
        before = text[max(0, match.start() - 100) : match.start()]
        rest = text[match.end() :]
        words = before.split()
        if words and (
            words[-1].islower() or (kind == "NOTES" and words[-1].lower().lstrip("(") == "see")
        ):
            continue
        if kind != "NOTES" and _PARENT_ONLY.search(before + "\n" + rest[:150]):
            continue
        if kind == "NOTES":
            if re.match(r"\s*(?:[.,;)]|(?:are|is)\b)", rest) or re.fullmatch(
                _TITLE_TAIL.pattern
                + r"(?:\.{2,}\s*)?(?i:page\s+)?(?:[A-Z]-)?[0-9]{1,3}"
                + r"(?:\s*(?i:to|through|[\u2013\u2014-])\s*(?:[A-Z]-)?[0-9]{1,3})?",
                rest,
            ):
                continue
        elif not tail.fullmatch(rest):
            continue
        kinds.add(kind)
    return kinds


def _line_unit_ranges(texts: dict[int, str]) -> list[tuple[int, int, str | None]]:
    """The (first, last, kind) of each statement unit of a line source, given its text by line
    number. A unit starts at a balance sheet, income (operations, earnings) or cash flow title
    line, or at a comprehensive income title line when no income-type title is in statement
    position in the source. Primary statements precede their notes: a title after the source's
    first "Notes to ... financial statements" title starts no unit (Schedule I, guarantor
    tables). Title lines that follow one another start one unit. A unit ends at the line before
    the next title of any kind (equity and comprehensive included, "Notes to ..." too) or at the
    source's last line; a "(Continued)" title of the unit's own kind continues it. A unit's kind is
    the one kind (BS, IS or CFS; CI counts as IS) its first title line was located by, else None."""
    titles: dict[int, set[str]] = {}
    for number in sorted(texts):
        kinds = _title_kinds(texts[number])
        if kinds and not _PAGE_ONLY.fullmatch(texts.get(number + 1, "").strip()):
            titles[number] = kinds
    cutoff = min((n for n, kinds in titles.items() if "NOTES" in kinds), default=None)
    located = {"BS", "IS", "CFS"} | (set() if any("IS" in k for k in titles.values()) else {"CI"})
    marked = {
        n for n, kinds in titles.items() if kinds & located and (cutoff is None or n <= cutoff)
    }

    def continues(number: int, kinds: set[str]) -> bool:
        return bool(titles[number] & kinds) and bool(
            re.search(
                r"\(\s*continued\s*\)|[\u2013\u2014-]\s*continued\b",
                texts[number],
                re.IGNORECASE,
            )
        )

    last = max(texts, default=0)
    ranges: list[tuple[int, int, str | None]] = []
    for first in sorted(number for number in marked if number - 1 not in marked):
        if ranges and first <= ranges[-1][1]:
            continue
        kinds = titles[first] & located
        run = first
        while run + 1 in marked:
            run += 1
        after = min((n for n in titles if n > run and not continues(n, kinds)), default=last + 1)
        kind = {"IS" if k == "CI" else k for k in kinds}
        ranges.append((first, after - 1, kind.pop() if len(kind) == 1 else None))
    return ranges


def _numbered(spans: Sequence[Span]) -> dict[int, Span] | None:
    """The spans of a line source by line number; None for any other source."""
    numbered = {
        int(m.group(1)): span for span in spans if (m := _LINE_LOCATOR.fullmatch(span.locator))
    }
    return numbered if spans and len(numbered) == len(spans) else None


def _page_title_kinds(text: str) -> list[tuple[int, set[str]]]:
    """The (line index, kinds) of each statement title in statement position on a page, in order.
    A title may run over two consecutive lines; one followed by a page-number line is a contents
    entry; a company-only title, and a statement title near a parent-company marker, are none."""
    lines = text.split("\n")
    found: list[tuple[int, set[str]]] = []
    previous = ""
    for index, raw in enumerate(lines):
        line = " ".join(raw.split())
        if not line:
            continue
        split_company = _COMPANY_WORD.fullmatch(previous) and _COMPANY_ONLY.match(
            f"{previous} {line}"
        )
        previous = line
        if split_company or _COMPANY_ONLY.match(line):
            continue
        following = next((" ".join(x.split()) for x in lines[index + 1 :] if x.strip()), "")
        if _PAGE_ONLY.fullmatch(following):
            continue
        kinds = _title_kinds(line, _PAGE_TITLE, _PAGE_TAIL)
        next_line = " ".join(lines[index + 1].split()) if index + 1 < len(lines) else ""
        joined = f"{line} {next_line}"
        if next_line and not _COMPANY_ONLY.match(next_line) and not _COMPANY_ONLY.match(joined):
            kinds |= _title_kinds(joined, _PAGE_TITLE, _PAGE_TAIL)
        near = "\n".join((" ".join(lines[index - 1].split()) if index else "", line, following))
        if _PARENT_ONLY.search(near):
            kinds &= {"NOTES"}
        if kinds:
            found.append((index, kinds))
    return found


def _opens_table(text: str, first_row: int) -> bool:
    """A text line stands before the page's period header (the first line with a four-digit year
    or "ended"; a unit line such as "(In millions)" is text, CP1H-R23.17), within the lines
    before its first data row, in any case: a new table's caption
    ("Reconciliation of Net Income ..." over a non-GAAP table), not the continuation of a
    statement whose period header comes first.

    ponytail: a real continuation page that repeats no period header and opens on a caption is
    refused too (fails closed: the page is then no unit, never a wrong one)."""
    head = text.split("\n")[:first_row]
    header = next((i for i, line in enumerate(head) if _PERIOD_HEADER.search(line)), len(head))
    return any(line.strip() for line in head[:header])


def _page_units(spans: Sequence[Span]) -> dict[str, str | None]:
    """The statement units of a page source's `page:N` spans, by locator, each with its kind (BS,
    IS or CFS; CI counts as IS; None when the titles name several or no kind) (CP1H-R23).

    A page is a unit when the extractor yields a data row from it and its first title is a balance
    sheet, income, comprehensive income or cash flow title; equity and notes titles start no unit.
    A page with no statement title continues the previous page's unit (its kind) when no equity or
    notes title stands before its first data row and no caption opens it (`_opens_table`).

    The result is cached by the page spans' (locator, text): `_statement_units`,
    `_statement_kinds` and the helpers of every `inputs()` and gate call read the same pages, and
    the extractor is the cost (about 220 ms per two passes over the 107-page CZR 10-K)."""
    pages = {
        int(span.locator.split(":")[1]): (span.locator, span.text)
        for span in spans
        if _PAGE_LOCATOR.fullmatch(span.locator)
    }
    return dict(_units_of_pages(tuple(pages[number] for number in sorted(pages))))


@lru_cache(maxsize=8)
def _units_of_pages(pages: tuple[tuple[str, str], ...]) -> dict[str, str | None]:
    """`_page_units` of the numbered `(locator, text)` pages in page order."""
    units: dict[str, str | None] = {}
    for locator, text in pages:
        number = int(locator.split(":")[1])
        rows = extract_statement_lines(text, locator).lines
        if not rows:
            continue
        first_row = rows[0].line_no - 1
        titles = _page_title_kinds(text)
        primary = {"BS", "IS", "CI", "CFS"}
        if titles and titles[0][1] <= primary:
            mapped = {"IS" if k == "CI" else k for _, found in titles for k in found & primary}
            units[locator] = mapped.pop() if len(mapped) == 1 else None
        elif any(index < first_row for index, _ in titles) or _opens_table(text, first_row):
            continue  # an equity or notes title, or a caption (`_opens_table`), opens the page
        elif f"page:{number - 1}" in units:
            units[locator] = units[f"page:{number - 1}"]
    return units


def _statement_units(spans: Sequence[Span]) -> dict[str, str]:
    """The statement units of one source's spans, by locator, each with its text (B22, CP1H-R18).

    A source with a `page:N` span, or with any other kind of span, has one unit per page located
    by `_page_units` and per other statement-heading span (its locator, its text). A line source
    (every span `line:N`) has one unit per statement title line in statement position,
    `line:K-E`, as `_line_unit_ranges` locates them. A unit's text is its lines joined by
    newlines."""
    numbered = _numbered(spans)
    if numbered is None:
        pages = _page_units(spans)
        return {
            s.locator: s.text
            for s in spans
            if s.locator in pages or STATEMENT_HEADING.search(s.text)
        }
    return {
        f"line:{first}-{end}": "\n".join(
            numbered[n].text for n in range(first, end + 1) if n in numbered
        )
        for first, end, _ in _line_unit_ranges({n: span.text for n, span in numbered.items()})
    }


def _statement_kinds(spans: Sequence[Span]) -> dict[str, str]:
    """The kind each unit was located by, by locator (CP1H-R20, R23): a line unit's, and a page
    unit's from its statement title. A page unit located only by its heading has none: it is read
    by `_statement`'s heading. A unit located under several kinds has none."""
    numbered = _numbered(spans)
    if numbered is None:
        return {locator: kind for locator, kind in _page_units(spans).items() if kind}
    return {
        f"line:{first}-{end}": kind
        for first, end, kind in _line_unit_ranges({n: span.text for n, span in numbered.items()})
        if kind
    }


def _missing_units(
    units: Iterable[tuple[str, str]], extracted: Iterable[tuple[str, str]]
) -> list[str]:
    """The "<source_id> <locator>" text of each located unit not extracted, in order, with ", "
    between them: the parts of the refusal's list."""
    done = set(extracted)
    parts: list[str] = []
    for source_id, locator in units:
        if (source_id, locator) not in done:
            parts.extend((", ", f"{source_id} {locator}") if parts else (f"{source_id} {locator}",))
    return parts


def _unbound_sources(ready: dict[str, str], payload: str, evidence: SourceEvidence) -> list[str]:
    """The ids, sorted and without duplicates, of the sources a CP-0 payload cites that are not
    ready sources of the pack. A page citation never read is already refused as unread, so its
    source is left to that rule."""
    read = evidence.seen().read
    return sorted(
        {
            source_id
            for source_id, locator in cited_locators(payload)
            if source_id not in ready
            and not (_PAGE_LOCATOR.fullmatch(locator) and (source_id, locator) not in read)
        }
    )


_UNCOVERED_LIMIT = 200
_COVERAGE_CHECKS = ("statement", "period", "label", "amount", "quote")
_NO_COLUMN = "no column maps a declared period"


def _amount_matches(amount: Any, value: Any) -> bool:
    """A line's amount holds an extracted value; a printed nil dash (None) is held by 0 or None."""
    return amount in (None, 0) if value is None else bool(amount == value)


def _amount_holds(line: StatementLine, value: Any) -> bool:
    """`_amount_matches`, or a withheld refund (S12-A02, user ruling B): a positive printed cell (a
    net inflow) on a line of an outflow account recorded as `missing` with a null amount and a
    reason, never as a flipped figure. Any other missing line still fails the amount check."""
    observation = line.value
    return _amount_matches(observation.amount, value) or (
        value is not None
        and value > 0
        and observation.amount is None
        and observation.status == "missing"
        and bool(observation.reason)
        and ACCOUNT_LINKS.get((line.statement, line.item_id)) in OUTFLOW_METRICS
    )


def _ids_text(ids: frozenset[str]) -> str:
    return f"one of {', '.join(sorted(ids))}" if len(ids) > 1 else next(iter(ids))


def _short(label: str) -> str:
    return label if len(label) <= 40 else label[:39] + "\u2026"


def _cites_row(line: StatementLine, table: Any, extracted: Any, *, quoting: bool) -> bool:
    """The line cites the row's source and locator (with its label in the quote if `quoting`)."""
    if line.quantity is not None or line.label_parts is not None:
        if not line.label_parts:
            return False
        amount_part = line.label_parts[-1]
        if amount_part.line_no != extracted.line_no or amount_part.locator != extracted.locator:
            return False
    return any(
        c.source_id == table.source_id
        and c.locator == extracted.locator
        and (not quoting or extracted.label in c.quote)
        for c in line.value.citations
    )


def _column_failure(  # noqa: PLR0911, PLR0913 - pre-existing (9 returns, 7 arguments at base, unchanged)
    book: Any,
    table: Any,
    extracted: Any,
    statement: str | None,
    column: tuple[Any, Any],
    source_sha256: str | None = None,
    context_tables: Sequence[Any] | None = None,
) -> tuple[int, str] | None:
    """The first failing check of one mapped column (its acceptable period ids, its extracted
    value), as an index in `_COVERAGE_CHECKS` and its reason text; None when a line of the book
    passes every check. The row's own lines are those in the column's periods that cite this row
    (the decision's own test); the label is a check on them, not how they are found. With none: a
    line there with the row's label, statement and amount that cites another row names the quote,
    else the period. Then the own lines' first wrong field: statement, label, amount, quote."""
    ids, value = column
    where = _ids_text(ids)
    label = " ".join(extracted.label.split())
    kind = statement or "unknown"
    in_period = [line for line in book.statement_lines if line.period_id in ids]
    own = [line for line in in_period if _cites_row(line, table, extracted, quoting=False)]
    if not own:
        if any(
            " ".join(line.label.split()) == label
            and line.statement == statement
            and _amount_matches(line.value.amount, value)
            for line in in_period
        ):
            return 4, f"quote: {where} has no citation of {extracted.locator} quoting the label"
        return 1, f'period: no {kind} line "{_short(extracted.label)}" for {where}'
    pool = [line for line in own if line.statement == statement]
    if not pool:
        return 0, f"statement: {where} cites this row as {own[0].statement}, expected {kind}"
    typed = [line for line in pool if line.quantity is not None or line.label_parts is not None]
    typed_unit = any(
        (line.quantity is not None or line.label_parts is not None)
        and any(
            c.source_id == table.source_id and c.locator == extracted.locator
            for c in line.value.citations
        )
        for line in book.statement_lines
    )
    family = sc.source_quantity_family(table, extracted)
    if (typed_unit or family != "monetary") and len(typed) != len(pool):
        return 2, f"label: {where} requires explicit source quantity and label parts"
    if typed and (
        source_sha256 is None
        or any(
            not sc.validate_typed_statement_line(
                table, extracted, line, book, source_sha256, context_tables
            )
            for line in typed
        )
    ):
        return 2, f"label: {where} has typed source parts or dimensions that do not verify"
    labelled = [line for line in pool if line in typed or " ".join(line.label.split()) == label]
    if not labelled:
        return 2, f'label: {where} cites this row with label "{_short(pool[0].label)}"'
    pool = [line for line in labelled if _amount_holds(line, value)]
    if not pool:
        return 3, f"amount: {where} expects {value}"
    if not typed and not any(_cites_row(line, table, extracted, quoting=True) for line in pool):
        return 4, f"quote: {where} has no citation of {extracted.locator} quoting the label"
    return None


def _first_failure(
    book: Any, table: Any, extracted: Any, statement: str | None, column: tuple[Any, Any]
) -> int | None:
    """The index in `_COVERAGE_CHECKS` of `_column_failure`, or None."""
    failure = _column_failure(book, table, extracted, statement, column)
    return None if failure is None else failure[0]


_Rows = frozenset[tuple[str, str]]
# a unit's own rows, and its peers: for each, its rows and its own printed header (CP1H-R23.27.2)
_Unit = tuple[_Rows, tuple[tuple[_Rows, tuple[str, ...]], ...]]
_NO_UNIT: _Unit = (frozenset(), ())


def _cites(line: StatementLine, rows: _Rows) -> bool:
    """The line cites a (source_id, row locator) of `rows`."""
    return any((c.source_id, c.locator) in rows for c in line.value.citations)


def _null_column(
    book: Any,
    statement: str | None,
    unit: _Unit,
    columns: tuple[frozenset[str], ...],
    index: int,
) -> bool:
    """A mapped column of a unit that needs no coverage in this book (CP1H-R23.16, R23.19, R23.27):
    (a) no line of the book cites a row of the unit under the column's periods; (b) another mapped
    column of the unit is covered (a unit with every column empty is not excused); (c) for each of
    the column's periods the book has a line of the row's statement citing a row of a peer.
    `unit` is (own rows, peers) as (source_id, row locator) pairs; a peer is a located unit on
    another source than the unit, of the unit's statement kind, not read by OCR, and its rows
    count only for a period its own printed header maps in this book. Its rows are themselves
    required under that period, which verifies the claim that another unit gives it. The default
    `_NO_UNIT` has no peers and excuses no column."""
    own, peers = unit
    lines = book.statement_lines
    ids = columns[index]
    if any(line.period_id in ids and _cites(line, own) for line in lines):
        return False
    others = [other for i, other in enumerate(columns) if i != index and other]
    if not any(line.period_id in other and _cites(line, own) for other in others for line in lines):
        return False
    given = [
        (rows, frozenset().union(*mapped))
        for rows, headers in peers
        if (mapped := _mapped_columns(headers, book.periods, statement)) is not None
    ]
    return all(
        any(
            line.statement == statement
            and line.period_id == period
            and any(period in mapped and _cites(line, rows) for rows, mapped in given)
            for line in lines
        )
        for period in ids
    )


def _uncovered_reason(  # noqa: PLR0913 - existing coverage-gate signature, unchanged here
    table: Any,
    extracted: Any,
    statement: str | None,
    books: Any,
    unit: _Unit = _NO_UNIT,
    page_text: str | None = None,
    source_sha256: str | None = None,
    context_tables: Sequence[Any] | None = None,
) -> str | None:
    """None when some book covers the row: at least one header column maps to its periods and every
    mapped column has a line with the row's statement, period, label, amount and a citation of the
    row's own line holding its label, except a column `_null_column` excuses (CP1H-R23.16). Else
    the first failing check of the first book that maps a column, with its detail; `_NO_COLUMN`
    when no book maps one (CP1H-R20). `unit` is as in `_null_column`; the default excuses no
    column."""
    reason = None
    for book in books:
        mapped = (
            _mapped_columns(table.headers, book.periods, statement)
            if page_text is None
            else _header_columns(table, book, page_text=page_text, statement=statement)
        )
        if mapped is None or len(mapped) != len(extracted.values):
            continue
        columns = [
            (ids, value)
            for index, (ids, value) in enumerate(zip(mapped, extracted.values, strict=True))
            if ids and not _null_column(book, statement, unit, mapped, index)
        ]
        failures = [
            _column_failure(
                book, table, extracted, statement, column, source_sha256, context_tables
            )
            for column in columns
        ]
        failed = [failure for failure in failures if failure is not None]
        if not failed:
            return None
        reason = reason or failed[0][1]
    return reason or _NO_COLUMN


def _source_context(store: Execution, binding: FinancialBinding) -> SourceContextReview:
    """The ticket's retained `source_context` review (its first step)."""
    attempt = next(a for a in store.read().attempts if a.ticket_id == binding.ticket_id)
    return SourceContextReview.model_validate_json(store.payload(attempt.steps[0].payload_sha256))


def _located_units(pack: Any, financial_ids: Collection[str]) -> dict[tuple[str, str], str]:
    """The located statement units of the ready financial sources, `(source_id, locator)` to the
    unit's text: what the gate requires (less the OCR pages) and the expansion may compose
    (CP1H-R23.27.3)."""
    return {
        (source.source_id, locator): text
        for source in pack.sources
        if source.source_id in financial_ids and source.status == "ready"
        for locator, text in _statement_units(source.spans).items()
    }


def _located_kinds(pack: Any, financial_ids: Collection[str]) -> dict[tuple[str, str], str | None]:
    return {
        (source.source_id, locator): kind
        for source in pack.sources
        if source.source_id in financial_ids and source.status == "ready"
        for locator, kind in _statement_kinds(source.spans).items()
    }


def _located_pdf_units(pack: Any, financial_ids: Collection[str]) -> dict[tuple[str, str], str]:
    # Only actual PDF page locators use raw page context; line and synthetic
    # text sources retain their existing extracted headers.
    return {
        (source.source_id, locator): text
        for source in pack.sources
        if source.source_id in financial_ids
        and source.status == "ready"
        and source.media_type == "application/pdf"
        for locator, text in _statement_units(source.spans).items()
        if _PAGE_LOCATOR.fullmatch(locator)
    }


def expand_unit_maps(
    store: Execution, binding: FinancialBinding, payload: str, evidence: SourceEvidence
) -> Expansion:
    """The submit entry's expansion (CP1H-R23.16): a financials payload with `unit_maps` becomes
    the composed `FinancialSubmission` JSON, from the epoch's own extraction. Any other step, and
    a payload with no maps, is returned as it is."""
    if binding.step_id != "financials":
        return Expansion(payload, ())
    document = json_object(payload)
    raw_maps = document.get("unit_maps") if document is not None else None
    book_dimensions: dict[str, tuple[str, str]] = {}
    if document is not None and isinstance(raw_maps, list) and raw_maps:
        # Expansion runs before the normal submit prefill. Reuse that authenticated resolver on
        # the submitted financial object, but keep its result out of the payload so the normal
        # submit path still owns prefill and audit recording.
        scope_payload = exact_json(_without_scope_dimensions(document))
        filled, _, _, _ = _filled(store, binding, scope_payload)
        original_document = document
        filled_document = json_object(filled)
        if filled_document is None or _scope_prefill_conflict(original_document, filled_document):
            return Expansion(
                payload,
                (
                    "unit_maps: submitted financial scope conflicts with authenticated source scope; nothing composed",
                ),
            )
        financial = filled_document.get("financial")
        books = financial.get("books") if isinstance(financial, dict) else None
        if isinstance(books, list):
            book_dimensions = {
                book["book_id"]: (book["currency"], book["unit"])
                for book in books
                if isinstance(book, dict)
                and isinstance(book.get("book_id"), str)
                and isinstance(book.get("currency"), str)
                and isinstance(book.get("unit"), str)
            }

    def inputs() -> UnitInputs:
        context = _source_context(store, binding)
        ids = tuple(s.source_id for s in context.sources if s.classification == "financial")
        tables = seen_tables(LineTools(store.pack(), sources=ids), evidence.seen(), context)
        hashes = known_bindings(store, binding.ticket_id, binding.step_id).sources
        other = _other_statement_rows(store.pack(), ids, tables)
        pack = store.pack()
        page_units = _located_pdf_units(pack, ids)
        kinds = _located_kinds(pack, ids)

        def header(table: Any, book: dict[str, Any]) -> tuple[frozenset[str], ...] | None:
            key = (table.source_id, table.locator)
            return _header_columns(
                table, book, page_text=page_units.get(key), statement=kinds.get(key)
            )

        return UnitInputs(
            tables,
            hashes,
            other,
            ocr_pages=_ocr_pages(pack, ids),
            note_pages=_note_pages(pack, ids, tables),
            note_rows=_note_rows(pack, ids, tables),
            ocr_header=header,
            located=frozenset(_located_units(pack, ids)),
            book_dimensions=book_dimensions,
        )

    return expand(payload, extracted=set(evidence.extracted), inputs=inputs)


_SCOPE_DIMENSION_FIELDS = frozenset({"entity_perimeter", "accounting_basis", "currency", "unit"})
_MISSING_PATH = object()


def _without_scope_dimensions(document: dict[str, Any]) -> dict[str, Any]:
    """Copy the visible submission without model-supplied scope fields for trusted prefill."""
    financial = document.get("financial")
    books = financial.get("books") if isinstance(financial, dict) else None
    if not isinstance(financial, dict) or not isinstance(books, list):
        return document
    clean_books: list[Any] = []
    for book in books:
        if not isinstance(book, dict):
            clean_books.append(book)
            continue
        clean_book = {
            key: value for key, value in book.items() if key not in _SCOPE_DIMENSION_FIELDS
        }
        periods = book.get("periods")
        if isinstance(periods, list):
            clean_book["periods"] = [
                {key: value for key, value in period.items() if key not in _SCOPE_DIMENSION_FIELDS}
                if isinstance(period, dict)
                else period
                for period in periods
            ]
        clean_books.append(clean_book)
    return {**document, "financial": {**financial, "books": clean_books}}


def _scope_prefill_conflict(original: dict[str, Any], filled: dict[str, Any]) -> bool:
    """Reject supplied hidden scope values that disagree with authenticated prefill results."""
    original_financial = original.get("financial")
    filled_financial = filled.get("financial")
    original_books = (
        original_financial.get("books") if isinstance(original_financial, dict) else None
    )
    filled_books = filled_financial.get("books") if isinstance(filled_financial, dict) else None
    if not isinstance(original_books, list):
        return False
    if not isinstance(filled_books, list) or len(original_books) != len(filled_books):
        return any(
            isinstance(book, dict)
            and any(book.get(field) is not None for field in _SCOPE_DIMENSION_FIELDS)
            for book in original_books
        )
    for original_book, filled_book in zip(original_books, filled_books, strict=True):
        if not isinstance(original_book, dict) or not isinstance(filled_book, dict):
            continue
        for field in _SCOPE_DIMENSION_FIELDS:
            supplied = original_book.get(field)
            if supplied is not None and supplied != filled_book.get(field, _MISSING_PATH):
                return True
        original_periods = original_book.get("periods")
        filled_periods = filled_book.get("periods")
        if not isinstance(original_periods, list) or not isinstance(filled_periods, list):
            continue
        if len(original_periods) != len(filled_periods) and any(
            isinstance(period, dict)
            and any(period.get(field) is not None for field in _SCOPE_DIMENSION_FIELDS)
            for period in original_periods
        ):
            return True
        for original_period, filled_period in zip(original_periods, filled_periods, strict=False):
            if not isinstance(original_period, dict) or not isinstance(filled_period, dict):
                continue
            for field in _SCOPE_DIMENSION_FIELDS:
                supplied = original_period.get(field)
                if supplied is not None and supplied != filled_period.get(field, _MISSING_PATH):
                    return True
    return False


def _evidence_issues(
    store: Execution, binding: FinancialBinding, payload: str, evidence: SourceEvidence
) -> tuple[str, ...]:
    if binding.step_id not in SOURCE_STEPS:
        return ()
    context = _source_context(store, binding) if binding.step_id == "financials" else None
    issues = list(
        ToolRules().issues(binding.step_id, payload, seen=evidence.seen(), context=context)
    )
    if binding.step_id == "source_readiness":
        for source_id in _unbound_sources(_ready_hashes(store.pack()), payload, evidence):
            issues.append(clipped(("Unavailable or changed source: ", source_id)))
    if context is None:
        return tuple(issues)
    financial_ids = tuple(s.source_id for s in context.sources if s.classification == "financial")
    pack = store.pack()
    units = _located_units(pack, financial_ids)
    header_units = _located_pdf_units(pack, financial_ids)
    # ponytail: ceiling: a unit on a page read by OCR is not required, neither its extraction nor
    # its rows' coverage, because Python composes it only when its arithmetic check passed and
    # the gate would otherwise demand the OCR figures Python refused (R23.23.1); an image-only
    # statement's figures are never forced by coverage. Upgrade: require them once OCR checks
    # cover detail rows.
    # ponytail: ceiling: a model-written OCR line is unchecked; upgrade: a row-level citation
    # check once OCR checks cover detail rows (a page-source citation names only the page, so a
    # cited-row check would demand the OCR misreads, R23.23.2 item 2 withdrawn).
    required = set(units) - _ocr_pages(pack, financial_ids)
    if not units:
        issues.append("No statement unit is located in the financial sources")
    elif not required <= set(evidence.extracted):
        missing = _missing_units([key for key in units if key in required], evidence.extracted)
        issues.append(clipped(("Financials must extract every located statement unit: ", *missing)))
    kinds = {
        (source.source_id, locator): kind
        for source in pack.sources
        if source.source_id in financial_ids and source.status == "ready"
        for locator, kind in _statement_kinds(source.spans).items()
    }
    tables = seen_tables(LineTools(pack, sources=financial_ids), evidence.seen(), context)
    try:
        submission = FinancialSubmission.model_validate_json(payload)
    except ValueError:
        return tuple(issues)  # The real core supplies shape errors.
    measured = set()
    rows = {
        (table.source_id, table.locator): frozenset(
            (table.source_id, line.locator) for line in table.lines
        )
        for table in tables
        if table.source_id is not None and (table.source_id, table.locator) in required
    }
    other = _other_statement_rows(pack, financial_ids, tables)
    table_by_key = {
        (table.source_id, table.locator): table for table in tables if table.source_id is not None
    }
    source_hashes = _ready_hashes(pack)
    for table in tables:
        if table.source_id is None:
            continue
        key = (table.source_id, table.locator)
        if key not in required:
            continue
        # a null column's peers (R23.27.2): a required (so non-OCR) located unit on another source,
        # located as the same statement kind; `_null_column` adds the unit's own header test
        peers = tuple(
            (rows[k], _context_headers(table_by_key[k], kinds.get(k), header_units.get(k)))
            for k in rows
            if kinds.get(key) is not None and k[0] != key[0] and kinds.get(k) == kinds[key]
        )
        unit: _Unit = (rows[key], peers)
        page_text = header_units.get(key)
        statement_text = units[key]
        if table.lines:
            measured.add(key)
        for extracted in table.lines:
            if extracted.line_no in other.get(key, {}):
                # ponytail: ceiling: a row whose caption names another statement than its unit's
                # (a cash reconciliation under a balance sheet caption on a cash flow page) is not
                # required, so coverage does not force a figure printed only in such a table;
                # upgrade: read a BS row's flow columns as balances at their end dates (R23.22).
                continue
            statement = _statement(extracted.caption, statement_text, kinds.get(key))
            reason = _uncovered_reason(
                table,
                extracted,
                statement,
                submission.financial.books,
                unit,
                page_text,
                source_hashes.get(table.source_id),
                tuple(candidate for candidate in tables if candidate.source_id == table.source_id),
            )
            if reason is not None:
                head = "Uncovered extracted statement line: "
                where = f"{table.source_id} {table.locator} line {extracted.line_no}"
                issues.append(clipped((head, where, "; ", reason), _UNCOVERED_LIMIT))
    if measured != required:
        issues.append("Statement extraction is unmeasured; empty tables do not establish coverage")
    return tuple(issues)


_STATEMENT_KINDS = (
    ("IS", ("INCOME STATEMENT", "STATEMENTS OF OPERATIONS")),
    ("CFS", ("CASH FLOW STATEMENT", "STATEMENTS OF CASH FLOWS")),
    ("BS", ("BALANCE SHEET", "FINANCIAL POSITION")),
)


_CAPTION_PHRASES = (
    ("CFS", ("CASH FLOW",)),
    ("BS", ("BALANCE SHEET", "FINANCIAL POSITION")),
    (
        "IS",
        (
            "INCOME STATEMENT",
            "STATEMENT OF OPERATIONS",
            "STATEMENTS OF OPERATIONS",
            "STATEMENT OF INCOME",
            "STATEMENTS OF INCOME",
            "STATEMENT OF EARNINGS",
            "STATEMENTS OF EARNINGS",
        ),
    ),
)


def _statement(caption: str | None, page_text: str, located: str | None = None) -> str | None:
    """A line's statement: the page's one heading kind; else a caption naming a statement outright;
    else the kind a line unit was located by (`located`, from `_statement_kinds`; CP1H-R20).

    A bare word such as INCOME in a caption names no statement.
    """
    kinds = {
        kind
        for heading in STATEMENT_HEADING.finditer(page_text)
        for kind, words in _STATEMENT_KINDS
        if any(word in heading.group() for word in words)
    }
    if len(kinds) == 1:
        return kinds.pop()
    upper = (caption or "").upper()
    for kind, phrases in _CAPTION_PHRASES:
        if any(phrase in upper for phrase in phrases):
            return kind
    return located


class _HeaderPeriod(BaseModel):
    """The fields of a `FinancialPeriod` that `_mapped_columns` reads. The expansion runs before
    the scope dimensions are filled in (currency, unit, basis, perimeter), so the model's period
    does not yet validate as a whole `FinancialPeriod`; these fields are the model's own."""

    period_id: str
    fiscal_year: str
    fiscal_quarter: int | None
    period_type: str
    start_date: date | None
    end_date: date | None


def _ocr_header(
    table: Any, book: dict[str, Any], statement: str | None = None
) -> tuple[frozenset[str], ...] | None:
    """The period ids each column of the table's own printed header maps to in the payload's book
    (`_mapped_columns`, for the unit's located `statement` kind), or None when the book's periods
    lack the header fields or no column maps (CP1H-R23.23.2): an OCR unit composes only when this
    verifies the model's column map."""
    raw = book.get("periods")
    if not isinstance(raw, list):
        return None
    try:
        periods = [_HeaderPeriod.model_validate(period) for period in raw]
    except ValidationError:
        return None
    return _mapped_columns(table.headers, periods, statement)


def _context_headers(table: Any, statement: str | None, pdf_text: str | None) -> tuple[str, ...]:
    if statement == "CI":
        statement = "IS"
    if pdf_text is None or statement not in ("BS", "IS", "CFS"):
        return cast(tuple[str, ...], table.headers)
    extracted = getattr(table, "lines", ())
    if not extracted:
        extracted = extract_statement_lines(
            pdf_text, getattr(table, "locator", "page:1"), getattr(table, "source_id", None)
        ).lines
    first_data_line = min((line.line_no for line in extracted), default=1)
    return (
        pdf_headers.mapping_headers(
            pdf_text,
            first_data_line=first_data_line,
            statement=cast(Literal["BS", "IS", "CFS"], statement),
        )
        or ()
    )


def _header_columns(
    table: Any, book: dict[str, Any], *, page_text: str | None = None, statement: str | None = None
) -> tuple[frozenset[str], ...] | None:
    """Map either extracted headers or PDF-only recovered printed context."""
    if page_text is None:
        return (
            _ocr_header(table, book, statement)
            if isinstance(book, dict)
            else _mapped_columns(table.headers, getattr(book, "periods", ()), statement)
        )
    periods = book.get("periods") if isinstance(book, dict) else getattr(book, "periods", None)
    if periods is None:
        return None
    headers = _context_headers(table, statement, page_text)
    if isinstance(book, dict):
        try:
            periods = [_HeaderPeriod.model_validate(p) for p in periods]
        except ValidationError:
            return None
    # A page unit located only by its heading has no located kind: read it as `_statement` does.
    flow = statement or _statement(None, page_text)
    return _mapped_columns(headers, periods, flow) if headers else None


def _ocr_pages(pack: Any, financial_ids: Collection[str]) -> frozenset[tuple[str, str]]:
    """The `(source_id, locator)` of each page of a financial source whose text was read by OCR
    (its coverage limitation starts with `OCR_MARK`, CP1H-R23.23). A unit on such a page composes
    only when its arithmetic check passed."""
    return frozenset(
        (source.source_id, item.locator)
        for source in pack.sources
        if source.source_id in financial_ids
        for item in source.coverage
        if (item.limitation or "").startswith(OCR_MARK)
    )


_NOTE_CELL = re.compile(r"(?i)notes?(?:\s+references?)?|references")
_CELL_GAP = re.compile(r"\s{2,}")
_HEADER_LINE = re.compile(
    r"(?<![0-9])(?:19|20)[0-9]{2}(?![0-9])|in\s+(?:millions|thousands|billions)", re.IGNORECASE
)
_GLUED_NOTE = re.compile(r"(?<=[0-9a-z])(?:Notes?|References)(?![a-z])")
_YEAR_TOKEN = re.compile(r"\b(?:19|20)\d{2}\b")
_LINE_RANGE = re.compile(r"line:([0-9]+)-([0-9]+)")


def _cells(line: str) -> list[str]:
    """The non-empty cells of a line: split on `|` where the line holds one, else on runs of two
    or more spaces."""
    parts = line.split("|") if "|" in line else _CELL_GAP.split(line)
    return [cell.strip() for cell in parts if cell.strip()]


def _has_note_column(text: str) -> bool:
    """Whether the text prints a note-reference column (CP1H-R23.24, R23.24.1): a cell that is
    exactly "Note", "Notes", "Note References" or "References"; or, on a line holding a 19xx/20xx
    year or "in millions/thousands/billions", the word Note, Notes or References glued to a
    preceding digit or lower-case letter ("2024Note", as pdftotext prints it). The whole text
    counts, not only the extractor's header block: VMED25 p172 prints "Note References" on its
    units line."""
    for line in text.splitlines():
        if any(_NOTE_CELL.fullmatch(cell) for cell in _cells(line)):
            return True
        if _HEADER_LINE.search(line) and _GLUED_NOTE.search(line.replace("\xa0", " ")):
            return True
    return False


def _table_text(spans: Sequence[Span], locator: str) -> tuple[list[str], int] | None:
    """The lines of a table's own text and the line number before its first line, or None where
    the spans do not hold it. A `page:N` table is that page span's text; a `line:K-E` table is
    source lines K..E respaced as `line_table` respaces them (`respace`)."""
    if _PAGE_LOCATOR.fullmatch(locator):
        span = next((s for s in spans if s.locator == locator), None)
        return None if span is None else (span.text.split("\n"), 0)
    found = _LINE_RANGE.fullmatch(locator)
    numbered = _numbered(spans)
    if found is None or numbered is None:
        return None
    first, last = int(found.group(1)), int(found.group(2))
    if any(number not in numbered for number in range(first, last + 1)):
        return None
    return [respace(numbered[n].text) for n in range(first, last + 1)], first - 1


def _table_texts(
    pack: Any, financial_ids: Collection[str], tables: Iterable[Any]
) -> Iterable[tuple[Any, list[str], int]]:
    """Each table of a ready financial source with its text lines and line offset."""
    sources = {
        source.source_id: source
        for source in pack.sources
        if source.source_id in financial_ids and source.status == "ready"
    }
    for table in tables:
        source = sources.get(table.source_id)
        text = None if source is None else _table_text(source.spans, table.locator)
        if text is not None:
            yield table, text[0], text[1]


def _note_pages(
    pack: Any, financial_ids: Collection[str], tables: Iterable[Any] | None = None
) -> frozenset[tuple[str, str]]:
    """The `(source_id, locator)` of each table that prints a note-reference column
    (CP1H-R23.24, R23.24.1). With `tables` (the composed tables), every one of them whose own
    text does; without, the located statement units of a financial source. A row of such a table
    whose first value could be a note number is left to the model."""
    if tables is None:
        return frozenset(
            (source.source_id, locator)
            for source in pack.sources
            if source.source_id in financial_ids and source.status == "ready"
            for locator, text in _statement_units(source.spans).items()
            if _has_note_column(text)
        )
    return frozenset(
        (table.source_id, table.locator)
        for table, lines, _ in _table_texts(pack, financial_ids, tables)
        if _has_note_column("\n".join(lines))
    )


def _note_rows(
    pack: Any, financial_ids: Collection[str], tables: Iterable[Any]
) -> dict[tuple[str, str], frozenset[int]]:
    """Per note table, the numbers of its `footnote_marker` rows below its first second header
    (CP1H-R23.24.1). The extractor drops a leading small number as a note on such a row; below a
    second table's header that number may have been a value. A second header is a line after the
    first data row that either is not a data row and has two or more cells, or holds two or more
    year tokens (the extractor reads "Group 2025 2024 2023" as a data row). A `line:K-E` table
    that prints a note column contributes every `footnote_marker` row instead (R23.24.2)."""
    result: dict[tuple[str, str], frozenset[int]] = {}
    for table, lines, offset in _table_texts(pack, financial_ids, tables):
        data = {row.line_no for row in table.lines}
        if not data or not _has_note_column("\n".join(lines)):
            continue
        if _LINE_RANGE.fullmatch(table.locator):
            # ponytail: on a line source every dropped note goes to the model (R23.24.2), because
            # respace changes the cells of a second header and no cell-based test is safe there.
            # Ceiling: an HTML note table's correctly dropped notes also go to the model. Upgrade
            # path: a token-based second-header test for line tables.
            marked = frozenset(row.line_no for row in table.lines if FOOTNOTE_MARKER in row.flags)
            if marked:
                result[(table.source_id, table.locator)] = marked
            continue
        for number in range(min(data) + 1, offset + len(lines) + 1):
            line = lines[number - offset - 1].removesuffix("\r")
            if (number not in data and len(_cells(line)) >= 2) or (
                len(_YEAR_TOKEN.findall(line)) >= 2
            ):
                rows = frozenset(
                    row.line_no
                    for row in table.lines
                    if row.line_no > number and FOOTNOTE_MARKER in row.flags
                )
                if rows:
                    result[(table.source_id, table.locator)] = rows
                break
    return result


def _other_statement_rows(
    pack: Any, financial_ids: Collection[str], tables: Iterable[Any]
) -> dict[tuple[str, str], dict[int, str]]:
    """Per located unit (source_id, locator), `{line_no: statement}` of the rows whose own
    `_statement` is not None and differs from the unit's located kind, where that kind is not None
    (CP1H-R23.22). Such a row sits under a caption of another statement; Python writes no line for
    it and the gate does not require one."""
    texts = {
        (source.source_id, locator): text
        for source in pack.sources
        if source.source_id in financial_ids and source.status == "ready"
        for locator, text in _statement_units(source.spans).items()
    }
    kinds = {
        (source.source_id, locator): kind
        for source in pack.sources
        if source.source_id in financial_ids and source.status == "ready"
        for locator, kind in _statement_kinds(source.spans).items()
    }
    result: dict[tuple[str, str], dict[int, str]] = {}
    for table in tables:
        if table.source_id is None:
            continue
        key = (table.source_id, table.locator)
        located = kinds.get(key)
        if located is None or key not in texts:
            continue
        for line in table.lines:
            statement = _statement(line.caption, texts[key], located)
            if statement is not None and statement != located:
                result.setdefault(key, {})[line.line_no] = statement
    return result


_MONTHS = {
    name: number
    for number, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        1,
    )
}
_FLOW_TYPES = {
    "Three": ("QUARTER", 3),
    "Six": ("YTD", 6),
    "Nine": ("YTD", 9),
    "Year": ("FY", 12),
}
_SPAN_CELL = re.compile(
    r"(?:(Three|Six|Nine) Months Ended|(Year)s? Ended) ([A-Z][a-z]+) (\d{1,2}),?|"
    r"([A-Z][a-z]+) (\d{1,2}),?"
)
_DATE_CELL = re.compile(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})")
_YEAR_CELL = re.compile(r"(?:19|20)\d{2}")


def _iso(year: str, month: str, day: str) -> str | None:
    """The ISO date of an English month name, day and year, or None when it is not a date."""
    if month not in _MONTHS:
        return None
    try:
        return date(int(year), _MONTHS[month], int(day)).isoformat()
    except ValueError:
        return None


def _header_cells(header: str) -> list[str]:
    return re.split(r"\s*\|\s*|\s{2,}", header.strip())


def _span(cell: str) -> tuple[str | None, str, str, int] | None:
    """(period type, or None for a balance date; month; day; month count) of a span cell."""
    found = _SPAN_CELL.fullmatch(cell)
    if found is None or (found[3] or found[5]) not in _MONTHS:
        return None
    if found[5] is not None:
        return None, found[5], found[6], 0
    kind, months = _FLOW_TYPES[found[1] or found[2]]
    return kind, found[3], found[4], months


def _is_column_cell(cell: str) -> bool:
    return bool(
        re.fullmatch(r"Q[1-4] \d{4}|FY \d{4}|(?:Opening|Q[1-4]|FY) \d{4}-\d{2}-\d{2}", cell)
        or _date_cell(cell)
    )


def _date_cell(cell: str) -> str | None:
    found = _DATE_CELL.fullmatch(cell)
    return _iso(found[3], found[1], found[2]) if found else None


_DAY_WINDOWS = {3: (84, 98), 6: (175, 189), 9: (266, 280), 12: (357, 371)}


def _months(period: Any) -> int | None:
    """The month count whose inclusive day-count window holds the period, else None."""
    start: date | None = period.start_date
    end: date | None = period.end_date
    if start is None or end is None:
        return None
    days = (end - start).days + 1
    return next((m for m, (low, high) in _DAY_WINDOWS.items() if low <= days <= high), None)


def _hit(spec: tuple[str, ...], period: Any) -> bool:
    kind, end = spec[0], str(period.end_date)
    year = re.findall(r"\d{4}", period.fiscal_year)
    if kind == "quarter":
        return (
            period.period_type == "QUARTER"
            and period.fiscal_quarter == int(spec[1])
            and year == [spec[2]]
        )
    if kind == "annual":
        return period.period_type == "FY" and year == [spec[1]]
    if kind == "dated":
        return end == spec[2] and (
            (spec[1] == "Opening" and period.period_type == "PERIOD_END")
            or (spec[1] == "FY" and period.period_type == "FY")
            or (
                spec[1].startswith("Q")
                and period.period_type == "QUARTER"
                and period.fiscal_quarter == int(spec[1][1])
            )
        )
    if kind == "flow":
        return end == spec[2] and period.period_type == spec[1] and _months(period) == int(spec[3])
    if kind == "balance":
        return end == spec[1] and period.period_type != "LTM"
    return False


def _matching(spec: tuple[str, ...], periods: Any) -> frozenset[str] | None:
    """Period ids for one column spec; all but a balance need exactly one match."""
    ids = [period.period_id for period in periods if _hit(spec, period)]
    if not ids or (spec[0] != "balance" and len(ids) != 1):
        return None
    return frozenset(ids)


def _single_spec(cell: str) -> tuple[str, ...]:
    quarter = re.fullmatch(r"Q([1-4]) (\d{4})", cell)
    annual = re.fullmatch(r"FY (\d{4})", cell)
    dated = re.fullmatch(r"(Opening|Q[1-4]|FY) (\d{4}-\d{2}-\d{2})", cell)
    if quarter:
        return ("quarter", quarter[1], quarter[2])
    if annual:
        return ("annual", annual[1])
    if dated:
        return ("dated", dated[1], dated[2])
    iso = _date_cell(cell)
    return ("balance", iso) if iso else ("unsupported",)


def _is_year_or_date(cell: str) -> bool:
    return bool(_YEAR_CELL.fullmatch(cell) or _DATE_CELL.fullmatch(cell))


def _column_year(cell: str, span: tuple[str | None, str, str, int]) -> str | None:
    """The year of a column cell: a bare year, or a full date on a flow span's own month and day."""
    if _YEAR_CELL.fullmatch(cell):
        return cell
    found = _DATE_CELL.fullmatch(cell)
    if found is None or span[0] is None or found[1] != span[1] or int(found[2]) != int(span[2]):
        return None
    return found[3]


def _span_specs(
    spans: list[tuple[str | None, str, str, int]], years: list[str]
) -> list[tuple[str, ...]]:
    """One spec per year column: span i covers the year columns i*n/k to (i+1)*n/k - 1."""
    width = len(years) // len(spans)
    specs: list[tuple[str, ...]] = []
    for index, year in enumerate(years):
        kind, month, day, months = spans[index // width]
        iso = _iso(year, month, day)
        if iso is None:
            return []
        specs.append(("balance", iso) if kind is None else ("flow", kind, iso, str(months)))
    return specs


def _drop_label(cells: list[str], keep: Any) -> list[str]:
    return cells if cells and keep(cells[0]) else cells[1:]


def _spec_row(headers: tuple[str, ...], index: int) -> list[tuple[str, ...]] | None:
    """The column specs of header `index`: a single row of columns, or a span row over a year row."""
    cells = _header_cells(headers[index])
    spans = [_span(cell) for cell in _drop_label(cells, lambda c: _span(c) is not None)]
    if spans and all(spans):
        if index + 1 == len(headers):
            return None
        row = _drop_label(_header_cells(headers[index + 1]), _is_year_or_date)
        count = len(row)
        if not count or count % len(spans):
            return None
        found = [s for s in spans if s]
        width = count // len(found)
        years = [_column_year(cell, found[i // width]) for i, cell in enumerate(row)]
        if not all(years):
            return None
        return _span_specs(found, [y for y in years if y]) or None
    specs = [_single_spec(cell) for cell in _drop_label(cells, _is_column_cell)]
    return specs or None


def _flow_span_row(header: str) -> bool:
    """True when the header is a span row naming a flow period (Three/Six/Nine Months, Years)."""
    cells = _drop_label(_header_cells(header), lambda c: _span(c) is not None)
    spans = [_span(cell) for cell in cells]
    return bool(spans) and all(spans) and any(s and s[0] for s in spans)


def _column_periods(headers: tuple[str, ...], periods: Any) -> tuple[frozenset[str], ...] | None:
    """One set of acceptable period ids per column from explicit headings; nothing is inferred.

    A column is `Q<n> <yyyy>`, `FY <yyyy>`, `(Opening|Q<n>|FY) <date>`, a full date (a balance:
    any non-LTM period ending then), or a year under a span row (`Three Months Ended`, `Six or
    Nine Months Ended`, `Years Ended` give one period of that type ending then; a bare month and
    day is a balance date). The column sets must be pairwise disjoint.
    """
    for index in range(len(headers)):
        specs = _spec_row(headers, index)
        if specs is None:
            if _flow_span_row(headers[index]):
                return None
            continue
        found = []
        for spec in specs:
            ids = _matching(spec, periods)
            if ids is None:
                break
            found.append(ids)
        if len(found) == len(specs) and len(frozenset[str]().union(*found)) == sum(map(len, found)):
            return tuple(found)
        if specs[0][0] == "flow":
            return None
    return None


_FLOW_STATEMENTS = frozenset(("IS", "CI", "CFS"))


def _mapped_columns(
    headers: tuple[str, ...], periods: Any, statement: str | None = None
) -> tuple[frozenset[str], ...] | None:
    """`_column_periods` for coverage (CP1H-R20): per header column, the period ids it maps to, or
    an empty set where it maps to none. None where no column maps, or where two columns that map
    share a period, or on a flow-span row that fails to map: the fail-closed cases of
    `_column_periods`. One column may map to several periods (a balance date); a line in any of
    them covers it. A column that several declared periods match, and that is not a balance, is
    ambiguous: None. A balance date names an instant, not a flow's duration: under an income or
    cash-flow `statement` it maps to no period, so a dated header never verifies a full-year
    column as Q4."""
    for index in range(len(headers)):
        specs = _spec_row(headers, index)
        if specs is None:
            if _flow_span_row(headers[index]):
                return None
            continue
        found = []
        for spec in specs:
            flow_date = spec[0] == "balance" and statement in _FLOW_STATEMENTS
            hits = frozenset(
                period.period_id for period in periods if not flow_date and _hit(spec, period)
            )
            if spec[0] != "balance" and len(hits) > 1:
                return None
            found.append(hits)
        mapped = [ids for ids in found if ids]
        if mapped and len(frozenset[str]().union(*mapped)) == sum(map(len, mapped)):
            return tuple(found)
        if specs[0][0] == "flow":
            return None
    return None


def _record(store: Execution, module_id: str) -> PromotedRecord:
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == module_id)
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    if (
        attempt.status != "finished"
        or attempt.issues
        or head.status not in ("accepted", "restricted")
    ):
        raise WorkflowError("identity_mismatch")
    return PromotedRecord(
        ticket_id=attempt.ticket_id, result_sha256=head.result_sha256, status=head.status
    )


def _files(directory: Path) -> dict[str, str]:
    return {name: _hash((directory / name).read_bytes()) for name in FILES}


class FinancialWorkflow:
    def __init__(self, store: Execution, attempt: Attempt, model_directory: Path) -> None:
        self._store, self._model_directory = store, model_directory
        self._operation = Lock()
        self._calls: list[FinancialCall] = []
        self._reads: list[InputRead] = []
        self._submissions: list[StageSubmission] = []
        self._publications: list[PublicationCall] = []
        self._refused_begin: RefusedBegin | None = None
        self._refusal: Literal["cp1_not_authorized"] | None = None
        self._model: ModelPublication | None = None
        self._participant = "trusted-python"
        self._transport: Literal["python-api", "bounded-json-lines/1"] = "python-api"
        self._limits: Counter[tuple[str, str, str]] = Counter()
        self._phase = "analytical"
        self._sealed = False
        self._activate(attempt, "source_readiness")

    @classmethod
    def create(
        cls, directory: Path, pack: PreparedPack, *, model_directory: Path
    ) -> "FinancialWorkflow":
        if pack.run.requested_modules != ("CP-1", "CP-MODEL"):
            raise WorkflowError("not_permitted")
        if (
            model_directory.exists()
            or model_directory.resolve() == directory.resolve()
            or directory.resolve() in model_directory.resolve().parents
        ):
            raise WorkflowError("not_permitted")
        store = Execution.create(directory, pack)
        return cls(store, store.begin("CP-0"), model_directory)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        if not self._operation.acquire(blocking=False):
            raise WorkflowError("not_permitted")
        try:
            if self._sealed:
                raise WorkflowError("not_permitted")
            yield
        finally:
            self._operation.release()

    def _current(self) -> ExecutionSnapshot:
        snapshot = self._store.read()
        if snapshot.content_hash() != self._current_sha256:
            raise WorkflowError("stale_binding")
        self._store.pack(snapshot)
        return snapshot

    def _activate(self, attempt: Attempt, step_id: str) -> None:
        snapshot = self._store.read()
        self._binding = _binding(snapshot, attempt, step_id)
        self._current_sha256 = snapshot.content_hash()
        self._session = (
            SourceSession.from_execution(self._store, attempt.ticket_id, step_id)
            if step_id in SOURCE_STEPS
            else None
        )
        self._epoch_calls: list[FinancialCall] = []
        _historical(self._store, self._binding)

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            self._current()
            key = (self._binding.ticket_id, self._binding.step_id, "invoke")
            if self._phase != "analytical" or self._limits[key] >= MAX_INVOKES:
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            if self._session is None:
                call = FinancialCall(
                    schema_version="tool-receipt/1",
                    call_id=str(uuid4()),
                    sequence=len(self._epoch_calls) + 1,
                    binding=self._binding,
                    tool=tool_name,
                    arguments=arguments,
                    status="refused",
                    body=None,
                    error_code="not_permitted",
                    source_evidence=SourceEvidence(),
                )
            else:
                call = _parse(FinancialCall, self._session.invoke(tool_name, arguments))
            call = _parse(FinancialCall, call.model_dump(mode="json"))
            if call.binding != self._binding or call.sequence != len(self._epoch_calls) + 1:
                raise WorkflowError("identity_mismatch")
            _retain(self._store, "calls", call)
            self._epoch_calls.append(call)
            self._calls.append(call)
            return call.model_dump(mode="json")

    def read_inputs(self) -> dict[str, Any]:
        with self._locked():
            self._current()
            key = (self._binding.ticket_id, self._binding.step_id, "read_inputs")
            if self._phase != "analytical" or self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            digest, body = _projection(self._store, self._binding)
            self._limits[key] += 1
            record = InputRead(
                binding=self._binding, sequence=self._limits[key], inputs_sha256=digest, body=body
            )
            _retain(self._store, "input-reads", record)
            self._reads.append(record)
            self._current()
            return record.model_dump(mode="json")

    def submit_review(self, payload: str) -> dict[str, Any]:
        with self._locked():
            self._current()
            if (
                self._phase != "analytical"
                or type(payload) is not str
                or len(payload.encode()) > MAX_LINE
            ):
                raise WorkflowError("not_permitted")
            key = (self._binding.ticket_id, self._binding.step_id, "submit_review")
            if self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            if self._session is None and not any(r.binding == self._binding for r in self._reads):
                raise WorkflowError("not_permitted")
            evidence = (
                self._epoch_calls[-1].source_evidence if self._epoch_calls else SourceEvidence()
            )
            expansion = expand_unit_maps(self._store, self._binding, payload, evidence)
            payload = expansion.payload
            payload_bytes = payload.encode()
            binding = FinancialSubmissionBinding(
                binding=self._binding,
                payload_sha256=_hash(payload_bytes),
                call_ids=tuple(c.call_id for c in self._epoch_calls),
                successful_call_ids=tuple(c.call_id for c in self._epoch_calls if c.status == "ok"),
                source_evidence=evidence,
            )
            if (
                self._session is not None
                and _parse(FinancialSubmissionBinding, self._session.bind_submission(payload))
                != binding
            ):
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "payloads", binding.payload_sha256), payload_bytes)
            _retain(self._store, "bindings", binding)
            stored, resolved, paths, kinds = _filled(self._store, self._binding, payload)
            stored_bytes = stored.encode()
            stored_hash = _hash(stored_bytes)
            _put(_audit(self._store, "payloads", stored_hash), stored_bytes)
            issues = _evidence_issues(self._store, self._binding, stored, evidence)
            self._current()
            attempt = None
            disposition: Literal["valid", "invalid", "refused"] = "refused"
            submitted_step = None
            if not issues:
                if self._binding.step_id == "source_readiness":
                    attempt = submit_cp0_review(self._store, self._binding.ticket_id, stored)
                else:
                    submitted = submit_model_payload(
                        self._store, self._binding.ticket_id, self._binding.step_id, payload
                    )
                    if (
                        submitted.payload,
                        submitted.nulls_resolved,
                        submitted.prefilled,
                        submitted.prefilled_kinds,
                    ) != (stored, resolved, paths, kinds):
                        raise WorkflowError("identity_mismatch")
                    attempt = submitted.journal
                candidates = (
                    attempt.steps
                    if attempt.steps and attempt.steps[-1].step_id == self._binding.step_id
                    else attempt.step_repairs
                )
                if (
                    not candidates
                    or candidates[-1].payload_sha256 != stored_hash
                    or candidates[-1].step_id != self._binding.step_id
                ):
                    raise WorkflowError("identity_mismatch")
                submitted_step = candidates[-1]
                disposition = (
                    "valid"
                    if submitted_step.status == "valid" and not attempt.issues
                    else "invalid"
                )
                issues = submitted_step.issues or attempt.issues
            after = self._store.read()
            try:
                canonical = (
                    SCHEMAS[self._binding.step_id].model_validate_json(stored).content_hash()
                )
            except ValueError:
                canonical = None
            after_hash = after.content_hash()
            record = StageSubmission(
                sequence=len(self._submissions) + 1,
                binding=binding,
                stored_payload_sha256=stored_hash,
                canonical_review_sha256=canonical,
                disposition=disposition,
                issues=issues,
                snapshot_after_sha256=after_hash,
                nulls_resolved=resolved,
                prefilled=paths,
                prefilled_kinds=kinds,
                step_sha256=None if submitted_step is None else submitted_step.content_hash(),
                step_output_sha256=None if submitted_step is None else submitted_step.output_sha256,
            )
            _retain(self._store, "submissions", record)
            self._submissions.append(record)
            step_id = self._binding.step_id
            self._current_sha256 = after_hash
            if attempt is not None:
                if disposition == "valid" and step_id == "source_readiness":
                    try:
                        self._activate(self._store.begin("CP-1"), "source_context")
                    except NotAuthorized as error:
                        self._refusal = "cp1_not_authorized"
                        self._refused_begin = RefusedBegin(
                            snapshot_sha256=after_hash, reason=str(error)
                        )
                        _retain(self._store, "refused-begin", self._refused_begin)
                        self._phase = "not_authorized"
                elif disposition == "valid" and step_id == "quality":
                    self._phase = "promoted"
                elif disposition == "valid":
                    self._activate(attempt, CP1_PROMOTION[len(attempt.steps)])
                elif attempt.status == "pending":
                    self._activate(attempt, step_id)
                elif attempt.number == 0:
                    self._activate(
                        self._store.begin(attempt.module_id),
                        "source_readiness" if attempt.module_id == "CP-0" else "source_context",
                    )
                else:
                    self._phase = "failed"
            return {
                "schema_version": "financial-review-outcome/1",
                "status": disposition,
                "issues": list(issues),
                "step_id": step_id,
                "refusal": self._refusal,
                "snapshot_sha256": self._current_sha256,
                "next_step": self._binding.step_id if self._phase == "analytical" else None,
                "stored_payload_sha256": stored_hash,
                "prefilled": list(paths),
                **({"notes": list(expansion.notes)} if expansion.notes else {}),
            }

    def publish_model(self) -> dict[str, Any]:
        with self._locked():
            before = self._current()
            if self._phase not in ("promoted", "not_authorized") or len(self._publications) >= 2:
                raise WorkflowError("not_permitted")
            ticket = None
            reason = None
            files: dict[str, str] = {}
            status: Literal["published", "refused", "failed"] = "refused"
            try:
                attempt = publish_cp_model(self._store, output=self._model_directory)
                ticket = attempt.ticket_id
                if verify_cp_model_publication(self._store, self._model_directory):
                    raise WorkflowError("identity_mismatch")
                model = _record(self._store, "CP-MODEL")
                cp1 = _record(self._store, "CP-1")
                files = _files(self._model_directory)
                self._model = ModelPublication(
                    ticket_id=model.ticket_id,
                    result_sha256=model.result_sha256,
                    cp1_result_sha256=cp1.result_sha256,
                    files=files,
                )
                status = "published"
                self._phase = "complete"
            except Exception as error:  # fail-open by design: finalize owned partial publications
                reason = str(error)
                after = self._store.read()
                new = [
                    a
                    for a in after.attempts
                    if a.ticket_id not in {a.ticket_id for a in before.attempts}
                ]
                if new:
                    status = "failed"
                    ticket = new[0].ticket_id if len(new) == 1 else None
                    if len(new) != 1 or new[0].module_id != "CP-MODEL":
                        self._phase = "failed"
                        raise WorkflowError("identity_mismatch") from error
                    if new[0].status == "pending":
                        try:
                            self._store.interrupt(
                                new[0].ticket_id, "Publication did not complete: " + reason
                            )
                        except Exception as cleanup_error:  # noqa: BLE001 - quarantine remains independent
                            reason += "; interruption failed: " + type(cleanup_error).__name__
                            self._phase = "failed"
                    if self._model_directory.exists():
                        for name in FILES:
                            try:
                                path = self._model_directory / name
                                if path.is_file():
                                    files[name] = _hash(path.read_bytes())
                            except OSError as hash_error:
                                reason += "; partial hash failed: " + type(hash_error).__name__
                        try:
                            self._model_directory.rename(
                                self._model_directory.with_name(
                                    self._model_directory.name + ".failed-" + str(uuid4())
                                )
                            )
                        except OSError as quarantine_error:
                            reason += "; quarantine failed: " + type(quarantine_error).__name__
                            self._phase = "failed"
                    if any(h.module_id == "CP-MODEL" for h in self._store.read().heads):
                        self._phase = "failed"
                elif self._phase == "not_authorized" and isinstance(error, CpModelRefused):
                    self._phase = "complete"
            after = self._store.read()
            record = PublicationCall(
                snapshot_before_sha256=before.content_hash(),
                snapshot_after_sha256=after.content_hash(),
                status=status,
                reason=reason,
                ticket_id=ticket,
                files=files,
            )
            _retain(self._store, "publications", record)
            self._publications.append(record)
            self._current_sha256 = after.content_hash()
            return {
                "status": "ok" if status == "published" else "refused",
                "error_code": None
                if status == "published"
                else self._refusal or "publication_refused",
                "snapshot_sha256": self._current_sha256,
            }

    def write_receipt(self, destination: Path) -> FinancialSliceReceipt:
        with self._locked():
            snapshot = self._current()
            if self._phase != "complete":
                raise WorkflowError("not_permitted")
            receipt = FinancialSliceReceipt(
                run=snapshot.run,
                pack_sha256=snapshot.pack_sha256,
                snapshot_sha256=snapshot.content_hash(),
                participant=self._participant,
                transport=self._transport,
                cp0=_record(self._store, "CP-0"),
                cp1=None if self._refusal else _record(self._store, "CP-1"),
                model=self._model,
                refusal=self._refusal,
                calls=tuple(self._calls),
                input_reads=tuple(self._reads),
                submissions=tuple(self._submissions),
                refused_begin=self._refused_begin,
                publications=tuple(self._publications),
            )
            _verify(
                self._store,
                receipt,
                model_directory=None if self._refusal else self._model_directory,
                sealed=False,
            )
            self._current()
            _put(
                self._store.directory / "financial-slice-audit" / "receipt.sha256",
                receipt.content_hash().encode(),
            )
            _put(destination, receipt.model_dump_json().encode())
            self._current()
            self._sealed = True
            return receipt


def _verify(
    store: Execution, receipt: FinancialSliceReceipt, *, model_directory: Path | None, sealed: bool
) -> None:
    from deploy_vii.execution import head_of

    snapshot = store.read()
    if (snapshot.run, snapshot.pack_sha256, snapshot.content_hash()) != (
        receipt.run,
        receipt.pack_sha256,
        receipt.snapshot_sha256,
    ):
        raise WorkflowError("stale_binding")
    store.pack(snapshot)
    expected_heads = {"CP-0"} if receipt.refusal else {"CP-0", "CP-1", "CP-MODEL"}
    if {h.module_id for h in snapshot.heads} != expected_heads or len(snapshot.heads) != len(
        expected_heads
    ):
        raise WorkflowError("identity_mismatch")
    for head in snapshot.heads:
        qualification = (
            PROMOTED
            if head.module_id == "CP-1"
            else PUBLISHED
            if head.module_id == "CP-MODEL"
            else None
        )
        if head != head_of(store.head_module(head), qualification):
            raise WorkflowError("identity_mismatch")
    retained_steps = Counter(
        (a.ticket_id, step.content_hash())
        for a in snapshot.attempts
        if a.module_id in ("CP-0", "CP-1")
        for step in (*a.steps, *a.step_repairs)
    )
    recorded_steps = Counter(
        (s.binding.binding.ticket_id, s.step_sha256)
        for s in receipt.submissions
        if s.disposition != "refused"
    )
    if retained_steps != recorded_steps:
        raise WorkflowError("identity_mismatch")
    ancestors = set()
    cursor = snapshot
    while True:
        digest = cursor.content_hash()
        if (
            digest in ancestors
            or cursor.run != receipt.run
            or cursor.pack_sha256 != receipt.pack_sha256
        ):
            raise WorkflowError("identity_mismatch")
        ancestors.add(digest)
        if cursor.parent is None:
            break
        cursor = _snapshot(store, cursor.parent)
    bindings = (
        [c.binding for c in receipt.calls]
        + [r.binding for r in receipt.input_reads]
        + [s.binding.binding for s in receipt.submissions]
    )
    coordinates = [b.snapshot_sha256 for b in bindings] + [
        s.snapshot_after_sha256 for s in receipt.submissions
    ]
    coordinates += [p.snapshot_before_sha256 for p in receipt.publications] + [
        p.snapshot_after_sha256 for p in receipt.publications
    ]
    if any(digest not in ancestors for digest in coordinates):
        raise WorkflowError("identity_mismatch")
    if (
        sealed
        and (store.directory / "financial-slice-audit" / "receipt.sha256").read_text()
        != receipt.content_hash()
    ):
        raise WorkflowError("identity_mismatch")
    collections = {
        "calls": receipt.calls,
        "input-reads": receipt.input_reads,
        "submissions": receipt.submissions,
        "bindings": tuple(s.binding for s in receipt.submissions),
        "publications": receipt.publications,
        "refused-begin": () if receipt.refused_begin is None else (receipt.refused_begin,),
    }
    for kind, values in collections.items():
        expected = {v.content_hash(): v.model_dump_json().encode() for v in values}
        directory = store.directory / "financial-slice-audit" / kind
        actual = {p.name for p in directory.iterdir()} if directory.exists() else set()
        if actual != set(expected) or any(
            _audit(store, kind, digest).read_bytes() != raw for digest, raw in expected.items()
        ):
            raise WorkflowError("identity_mismatch")
    if len({c.call_id for c in receipt.calls}) != len(receipt.calls):
        raise WorkflowError("identity_mismatch")
    for records, cap in ((receipt.calls, MAX_INVOKES), (receipt.input_reads, MAX_CALLS)):
        counts = Counter((record.binding.ticket_id, record.binding.step_id) for record in records)
        if any(count > cap for count in counts.values()):
            raise WorkflowError("identity_mismatch")
    submission_counts = Counter(
        (s.binding.binding.ticket_id, s.binding.binding.step_id) for s in receipt.submissions
    )
    if any(count > MAX_CALLS for count in submission_counts.values()):
        raise WorkflowError("identity_mismatch")
    _publication_history(store, receipt)
    replayed: dict[str, SourceSession] = {}
    for call in receipt.calls:
        historical = _historical(store, call.binding)
        key = call.binding.content_hash()
        prior = [
            c for c in receipt.calls if c.binding == call.binding and c.sequence < call.sequence
        ]
        if call.sequence != len(prior) + 1 or call.sequence > MAX_INVOKES:
            raise WorkflowError("identity_mismatch")
        if call.binding.step_id in SOURCE_STEPS:
            if key not in replayed:
                replayed[key] = SourceSession.from_execution(
                    historical, call.binding.ticket_id, call.binding.step_id
                )
            expected_call = _parse(FinancialCall, replayed[key].invoke(call.tool, call.arguments))
            if expected_call.model_copy(update={"call_id": call.call_id}) != call:
                raise WorkflowError("identity_mismatch")
        elif (
            call.status != "refused"
            or call.error_code != "not_permitted"
            or call.body is not None
            or call.source_evidence != SourceEvidence()
        ):
            raise WorkflowError("identity_mismatch")
    for read in receipt.input_reads:
        digest, body = _projection(store, read.binding)
        prior_reads = [
            r
            for r in receipt.input_reads
            if r.binding.ticket_id == read.binding.ticket_id
            and r.binding.step_id == read.binding.step_id
            and r.sequence < read.sequence
        ]
        if (
            (read.inputs_sha256, read.body) != (digest, body)
            or read.sequence != len(prior_reads) + 1
            or read.sequence > MAX_CALLS
        ):
            raise WorkflowError("identity_mismatch")
    valid = []
    for sequence, submission in enumerate(receipt.submissions, 1):
        if submission.sequence != sequence:
            raise WorkflowError("identity_mismatch")
        binding = submission.binding
        historical = _historical(store, binding.binding)
        raw = _raw(store, binding.payload_sha256)
        filled, resolved, paths, kinds = _filled(historical, binding.binding, raw)
        if (filled, resolved, paths, kinds) != (
            _raw(store, submission.stored_payload_sha256),
            submission.nulls_resolved,
            submission.prefilled,
            submission.prefilled_kinds,
        ):
            raise WorkflowError("identity_mismatch")
        scoped = [c for c in receipt.calls if c.binding == binding.binding]
        prefix = scoped[: len(binding.call_ids)]
        evidence = prefix[-1].source_evidence if prefix else SourceEvidence()
        if (
            binding.call_ids != tuple(c.call_id for c in prefix)
            or binding.successful_call_ids != tuple(c.call_id for c in prefix if c.status == "ok")
            or binding.source_evidence != evidence
        ):
            raise WorkflowError("identity_mismatch")
        issues = _evidence_issues(historical, binding.binding, filled, evidence)
        after = _snapshot(store, submission.snapshot_after_sha256)
        if after.run != receipt.run or after.pack_sha256 != receipt.pack_sha256:
            raise WorkflowError("identity_mismatch")
        if submission.disposition == "refused":
            if (
                not issues
                or submission.issues != issues
                or after.content_hash() != binding.binding.snapshot_sha256
                or submission.step_sha256 is not None
            ):
                raise WorkflowError("identity_mismatch")
            continue
        if issues:
            raise WorkflowError("identity_mismatch")
        canonical = None
        try:
            canonical = SCHEMAS[binding.binding.step_id].model_validate_json(filled).content_hash()
        except ValueError:
            pass
        if canonical != submission.canonical_review_sha256:
            raise WorkflowError("identity_mismatch")
        attempt = next(a for a in after.attempts if a.ticket_id == binding.binding.ticket_id)
        before_attempt = next(
            a for a in historical.read().attempts if a.ticket_id == binding.binding.ticket_id
        )
        candidates = (
            attempt.steps
            if len(attempt.steps) > len(before_attempt.steps)
            else attempt.step_repairs[len(before_attempt.step_repairs) :]
        )
        matches = [s for s in candidates[-1:] if s.content_hash() == submission.step_sha256]
        if (
            len(matches) != 1
            or matches[0].payload_sha256 != submission.stored_payload_sha256
            or matches[0].output_sha256 != submission.step_output_sha256
        ):
            raise WorkflowError("identity_mismatch")
        step = matches[0]
        if submission.disposition == "valid":
            if step.status != "valid" or submission.issues:
                raise WorkflowError("identity_mismatch")
            valid.append((attempt.ticket_id, step.step_id, step.content_hash()))
            if binding.binding.step_id not in SOURCE_STEPS and not any(
                r.binding == binding.binding for r in receipt.input_reads
            ):
                raise WorkflowError("identity_mismatch")
        elif step.status != "invalid" or step.issues != submission.issues:
            raise WorkflowError("identity_mismatch")
    if _record(store, "CP-0") != receipt.cp0:
        raise WorkflowError("identity_mismatch")
    cp0_attempt = next(a for a in snapshot.attempts if a.ticket_id == receipt.cp0.ticket_id)
    _verify_cp0(store, snapshot, cp0_attempt)
    expected_steps = [
        (cp0_attempt.ticket_id, s.step_id, s.content_hash()) for s in cp0_attempt.steps
    ]
    if receipt.refusal:
        if (
            receipt.refusal != "cp1_not_authorized"
            or receipt.cp1 is not None
            or receipt.model is not None
            or model_directory is not None
            or receipt.refused_begin is None
        ):
            raise WorkflowError("identity_mismatch")
        if any(a.module_id != "CP-0" for a in snapshot.attempts) or any(
            h.module_id != "CP-0" for h in snapshot.heads
        ):
            raise WorkflowError("identity_mismatch")
        try:
            current_inputs(snapshot, "CP-1")
        except NotAuthorized as error:
            if (
                str(error) != receipt.refused_begin.reason
                or receipt.refused_begin.snapshot_sha256 != snapshot.content_hash()
            ):
                raise WorkflowError("identity_mismatch") from None
        else:
            raise WorkflowError("identity_mismatch")
        if len(receipt.publications) != 1:
            raise WorkflowError("identity_mismatch")
        publication = receipt.publications[0]
        with tempfile.TemporaryDirectory() as refused_directory:
            try:
                publish_cp_model(
                    _FrozenExecution(store, snapshot), output=Path(refused_directory) / "absent"
                )
            except CpModelRefused as error:
                if publication != PublicationCall(
                    snapshot_before_sha256=snapshot.content_hash(),
                    snapshot_after_sha256=snapshot.content_hash(),
                    status="refused",
                    reason=str(error),
                    ticket_id=None,
                    files={},
                ):
                    raise WorkflowError("identity_mismatch") from None
            else:
                raise WorkflowError("identity_mismatch")
    else:
        if (
            receipt.cp1 is None
            or receipt.model is None
            or receipt.refused_begin is not None
            or model_directory is None
        ):
            raise WorkflowError("identity_mismatch")
        if (
            _record(store, "CP-1") != receipt.cp1
            or set(receipt.model.files) != set(FILES)
            or _files(model_directory) != receipt.model.files
        ):
            raise WorkflowError("identity_mismatch")
        attempt = next(a for a in snapshot.attempts if a.ticket_id == receipt.cp1.ticket_id)
        _verify_promotion(store, snapshot, attempt)
        expected_steps += [(attempt.ticket_id, s.step_id, s.content_hash()) for s in attempt.steps]
        model = _record(store, "CP-MODEL")
        if (model.ticket_id, model.result_sha256, receipt.cp1.result_sha256) != (
            receipt.model.ticket_id,
            receipt.model.result_sha256,
            receipt.model.cp1_result_sha256,
        ):
            raise WorkflowError("identity_mismatch")
        if verify_cp_model_publication(store, model_directory):
            raise WorkflowError("identity_mismatch")
        _verify_model_settlement(store, snapshot, model_directory)
        if (
            not receipt.publications
            or receipt.publications[-1].status != "published"
            or receipt.publications[-1].ticket_id != model.ticket_id
            or receipt.publications[-1].files != receipt.model.files
            or receipt.publications[-1].snapshot_after_sha256 != snapshot.content_hash()
        ):
            raise WorkflowError("identity_mismatch")
    if not all(item in valid for item in expected_steps):
        raise WorkflowError("identity_mismatch")
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise WorkflowError("stale_binding")


def _verify_cp0(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    from deploy_vii.execution import settle
    from deploy_vii.readiness import build_readiness, validate_review

    if len(attempt.steps) != 1 or attempt.steps[0].status != "valid":
        raise WorkflowError("identity_mismatch")
    step = attempt.steps[0]
    review = ReadinessReview.model_validate_json(store.payload(step.payload_sha256))
    if validate_review(store.pack(snapshot), review):
        raise WorkflowError("identity_mismatch")
    candidate = build_readiness(store.pack(snapshot), review, attempt=attempt.number)
    if (
        candidate.content_hash() != step.output_sha256
        or store.step_output(step.output_sha256 or "") != candidate.model_dump_json()
    ):
        raise WorkflowError("identity_mismatch")
    finished, result = settle(
        snapshot,
        attempt,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("CP0 candidate differs",),
        pack=store.pack(snapshot),
        load=store.head_module,
    )
    if finished != attempt or result != store.head_module(
        next(h for h in snapshot.heads if h.module_id == "CP-0")
    ):
        raise WorkflowError("identity_mismatch")


def _publication_history(store: Execution, receipt: FinancialSliceReceipt) -> None:
    """Every begun Model attempt and non-begin refusal has its retained actual transition."""
    snapshot = store.read()
    attempts = {a.ticket_id: a for a in snapshot.attempts if a.module_id == "CP-MODEL"}
    recorded = Counter(p.ticket_id for p in receipt.publications if p.ticket_id is not None)
    if recorded != Counter(attempts.keys()) or not 1 <= len(receipt.publications) <= 2:
        raise WorkflowError("identity_mismatch")
    previous_after = None
    for index, publication in enumerate(receipt.publications):
        before = _snapshot(store, publication.snapshot_before_sha256)
        after = _snapshot(store, publication.snapshot_after_sha256)
        if previous_after is not None and previous_after != publication.snapshot_before_sha256:
            raise WorkflowError("identity_mismatch")
        previous_after = publication.snapshot_after_sha256
        if publication.status == "refused":
            if (
                before != after
                or publication.ticket_id is not None
                or publication.files
                or not publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            if not receipt.refusal and not (
                publication.reason.startswith("Output ")
                and "already exists; publish into a new directory" in publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            continue
        before_tickets = {a.ticket_id for a in before.attempts}
        added = [a for a in after.attempts if a.ticket_id not in before_tickets]
        if (
            len(added) != 1
            or added[0].module_id != "CP-MODEL"
            or added[0].ticket_id != publication.ticket_id
            or added[0] != attempts.get(publication.ticket_id)
        ):
            raise WorkflowError("identity_mismatch")
        if tuple(
            a for a in after.attempts if a.ticket_id != publication.ticket_id
        ) != before.attempts or set(publication.files) - set(FILES):
            raise WorkflowError("identity_mismatch")
        attempt = added[0]
        if publication.status == "published":
            if (
                index != len(receipt.publications) - 1
                or attempt.status != "finished"
                or attempt.issues
                or publication.reason is not None
                or receipt.model is None
                or publication.files != receipt.model.files
            ):
                raise WorkflowError("identity_mismatch")
        elif (
            attempt.status != "finished"
            or not attempt.issues
            or attempt.interruption is None
            or not publication.reason
        ):
            raise WorkflowError("identity_mismatch")


def _verify_promotion(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Re-enter the public promotion validator with a non-writing finish probe."""
    from deploy_vii.execution import settle

    if (
        len(attempt.steps) != 5
        or tuple(s.step_id for s in attempt.steps) != CP1_PROMOTION
        or any(s.status != "valid" for s in attempt.steps)
    ):
        raise WorkflowError("identity_mismatch")
    if next(h for h in snapshot.heads if h.module_id == "CP-1").qualification != PROMOTED:
        raise WorkflowError("identity_mismatch")
    registers = cp1_registers(store, attempt.ticket_id)
    handoff = CP1Handoff.model_validate_json(
        store.step_output(attempt.steps[4].output_sha256 or "")
    )
    review = QualityReview.model_validate_json(store.payload(attempt.steps[4].payload_sha256))
    if handoff.registers_sha256 != registers.content_hash() or handoff.quality != assess_quality(
        cp1_quality_inputs(registers), review
    ):
        raise WorkflowError("identity_mismatch")

    class Probe(_FrozenExecution):
        def finish(self, ticket_id: str, payload: str, validator: Any, **kwargs: Any) -> Attempt:
            if ticket_id != attempt.ticket_id or payload != store.payload(
                attempt.payload_sha256 or ""
            ):
                raise WorkflowError("identity_mismatch")
            finished, result = settle(
                snapshot,
                attempt,
                payload,
                validator,
                pack=store.pack(snapshot),
                load=store.head_module,
            )
            if finished != attempt or result != store.result(attempt.result_sha256 or ""):
                raise WorkflowError("identity_mismatch")
            return finished

    pending = attempt.model_copy(update={"status": "pending"})
    probe_snapshot = snapshot.model_copy(
        update={
            "attempts": tuple(
                pending if a.ticket_id == pending.ticket_id else a for a in snapshot.attempts
            )
        }
    )
    if (
        promote_cp1(
            Probe(store, probe_snapshot),
            attempt.ticket_id,
            store.payload(attempt.steps[4].payload_sha256),
        )
        != attempt
    ):
        raise WorkflowError("identity_mismatch")
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "envelope"
        write_cp1_envelope(store, destination)
        read_cp1_envelope(store, destination)


def _verify_model_settlement(
    store: Execution, snapshot: ExecutionSnapshot, directory: Path
) -> None:
    """The public publisher rebuilds the complete candidate; finish is a read-only probe."""
    from deploy_vii.execution import settle

    head = next(h for h in snapshot.heads if h.module_id == "CP-MODEL")
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    if head.qualification != PUBLISHED:
        raise WorkflowError("identity_mismatch")

    class Probe(_FrozenExecution):
        def begin(self, module_id: str) -> Attempt:
            if module_id != "CP-MODEL":
                raise WorkflowError("not_permitted")
            return attempt.model_copy(
                update={"status": "pending", "payload_sha256": None, "result_sha256": None}
            )

        def finish(self, ticket_id: str, payload: str, validator: Any, **kwargs: Any) -> Attempt:
            if ticket_id != attempt.ticket_id or payload != store.payload(
                attempt.payload_sha256 or ""
            ):
                raise WorkflowError("identity_mismatch")
            finished, result = settle(
                snapshot,
                attempt,
                payload,
                validator,
                pack=store.pack(snapshot),
                load=store.head_module,
            )
            if finished != attempt or result != store.result(head.result_sha256):
                raise WorkflowError("identity_mismatch")
            return finished

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "model"
        if publish_cp_model(Probe(store, snapshot), output=output) != attempt or _files(
            output
        ) != _files(directory):
            raise WorkflowError("identity_mismatch")


def verify_financial_slice_receipt(
    store: Execution, receipt: FinancialSliceReceipt, *, model_directory: Path | None = None
) -> None:
    """Authenticate portable sealed participation evidence and exact selected publication."""
    try:
        receipt = FinancialSliceReceipt.model_validate_json(receipt.model_dump_json())
        _verify(store, receipt, model_directory=model_directory, sealed=True)
    except WorkflowError:
        raise
    except (ValueError, OSError, KeyError, StopIteration, TypeError, UnicodeError):
        raise WorkflowError("identity_mismatch") from None


def _request_of(line: str) -> dict[str, Any]:
    """The request object on one whole line (`read_line` has read an over-length one to its end);
    an over-length or unterminated line, or anything but a JSON object, is `bad_arguments`."""
    if len(line) > MAX_LINE or not line.endswith("\n"):
        raise WorkflowError("bad_arguments")
    request = json.loads(line, parse_constant=_nonfinite_json)
    if type(request) is not dict:
        raise WorkflowError("bad_arguments")
    return request


def serve_json_lines(
    workflow: FinancialWorkflow,
    reader: TextIO,
    writer: TextIO,
    *,
    destination: Path,
    participant: str,
) -> None:
    if workflow._calls or workflow._submissions or workflow._reads:
        raise WorkflowError("not_permitted")
    workflow._participant, workflow._transport = participant, "bounded-json-lines/1"
    for _ in range(MAX_MESSAGES):
        line = read_line(reader, writer, MAX_LINE)
        if not line:
            return
        try:
            request = _request_of(line)
            operation = request.get("operation")
            if operation == "invoke" and set(request) == {"operation", "tool", "arguments"}:
                result = workflow.invoke(request["tool"], request["arguments"])
            elif operation == "submit_review" and set(request) == {"operation", "payload"}:
                result = workflow.submit_review(request["payload"])
            elif operation == "read_inputs" and set(request) == {"operation"}:
                result = workflow.read_inputs()
            elif operation == "publish_model" and set(request) == {"operation"}:
                result = workflow.publish_model()
            elif operation == "write_receipt" and set(request) == {"operation"}:
                receipt = workflow.write_receipt(destination)
                result = {
                    "status": "ok",
                    "receipt_sha256": receipt.content_hash(),
                    "snapshot_sha256": receipt.snapshot_sha256,
                }
            else:
                raise WorkflowError("not_permitted")
        except (WorkflowError, SourceError) as error:
            result = {"status": "refused", "error_code": error.code}
        except (ValueError, TypeError, KeyError, UnicodeError):
            result = {"status": "refused", "error_code": "bad_arguments"}
        except Exception:  # noqa: BLE001 - sanitized bounded analytical transport
            result = {"status": "error", "error_code": "internal_error"}
        writer.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
        writer.flush()


def _nonfinite_json(value: str) -> None:
    raise ValueError("Non-finite JSON number")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded offline CP1 financial workflow")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--participant", required=True)
    args = parser.parse_args()
    pack = PreparedPack.model_validate_json(args.pack.read_bytes())
    workflow = FinancialWorkflow.create(args.directory, pack, model_directory=args.model_directory)
    serve_json_lines(
        workflow, sys.stdin, sys.stdout, destination=args.receipt, participant=args.participant
    )


if __name__ == "__main__":
    main()
