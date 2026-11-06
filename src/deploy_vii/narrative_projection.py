"""Reader-facing synthesis and exact prior-row trace; projection, not acceptance."""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field

from deploy_vii import prose
from deploy_vii.contracts import Citation, Claim, Fact, ReportTable, TableColumn
from deploy_vii.financial_contracts import FinancialBook
from deploy_vii.financial_periods import _id
from deploy_vii.model_interface import _Cell, _Tables
from deploy_vii.narrative import (
    _DIMENSIONS,
    EvidencePart,
    EvidenceRecord,
    IssuerPart,
    NarrativeReport,
    Passage,
    ProsePart,
)
from deploy_vii.statement_output import StatementCell
from deploy_vii.statement_validation import REQUIRED_ITEMS

SCHEMAS = {
    "analysis-coverage": (
        "Analytical dimension coverage",
        None,
        ("Dimension", "Status", "Findings", "Rationale"),
    ),
    "funding-assessment": (
        "Non-debt funding assessment",
        None,
        ("Status", "Reviewed Evidence", "Material Evidence", "Rationale"),
    ),
    "required-stories": (
        "Required event and funding stories",
        None,
        ("Evidence", "Kind", "Reference", "Status", "Findings"),
    ),
    "evidence-trace": (
        "Evidence trace — exact prior records",
        None,
        (
            "Evidence",
            "Evidence ID",
            "Kind",
            "Reference",
            "Used By",
            "Artifact SHA256",
            "Record SHA256",
            "Fields",
        ),
    ),
    "statement-coverage": (
        "Financial statement coverage",
        None,
        (
            "Period",
            "Statement",
            "Supplied Lines",
            "Missing Required",
            "Conflicting",
            "Not Applicable",
            "Scope",
        ),
    ),
}


@dataclass(frozen=True)
class NarrativeProjection:
    claims: tuple[Claim, ...]
    facts: tuple[Fact, ...]
    tables: tuple[ReportTable, ...]


def _fields(value: object, path: str = "") -> Iterator[str]:
    """Lossless leaf text with JSON-pointer paths and JSON scalar spelling."""
    if isinstance(value, dict) and value:
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from _fields(child, path + "/" + escaped)
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from _fields(child, path + "/" + str(index))
    else:
        yield f"{path or '/'} = {json.dumps(value, ensure_ascii=False, allow_nan=False)}"


def _trace_fact_id(identity: str) -> str:
    """The fact id of an evidence-trace row's Evidence cell, as ``_Tables.row`` derives it."""
    return _id(
        "interface-fact",
        "evidence-trace",
        _id("interface-row", "evidence-trace", identity),
        "evidence",
    )


# Run text reserves square brackets and braces for references, and has no escape: in claim text
# the issuer name spells them as parentheses (`Acme [UK] Ltd` -> `Acme (UK) Ltd`). Table text
# keeps the name as supplied.
_RUN_TEXT_NAME = str.maketrans("[]{}", "()()")
_ANALYST = frozenset({"analysis-coverage", "funding-assessment", "required-stories"})
NOT_INTRINSIC = (
    "Exact prior record. Dimensions not intrinsic to this record "
    "must be read from the referenced canonical registers; do not infer them."
)
STATEMENT_DIMENSIONS = (
    "Statement dimensions are the cell's own quantity unit, currency and scale; its period "
    "comes from the validated financial book."
)
STATEMENT_NO_PERIOD = (
    "Statement dimensions are the cell's own quantity unit, currency and scale; its period is "
    "not in the validated financial book."
)


def run_text_name(issuer_name: str) -> str:
    """The issuer name as claim run text spells it: reserved brackets become parentheses."""
    return issuer_name.translate(_RUN_TEXT_NAME)


@dataclass
class _Resolver:
    """Resolves passages against the catalogue and records which owner used each record."""

    issuer_name: str
    catalogue: dict[str, EvidenceRecord]
    labels: dict[str, str]
    uses: dict[str, list[str]] = field(default_factory=dict)

    def use(self, identity: str, owner: str) -> None:
        self.uses.setdefault(identity, []).append(owner)

    def passage(
        self, passage: Passage, owner: str, *, chips: bool = False
    ) -> tuple[str, tuple[Citation, ...]]:
        """Resolve tokens in order; source records remain distinct from analyst prose.

        With ``chips`` (claim text, decision 0005 MC-2) evidence is a ``[<fact id>]`` run
        reference to its evidence-trace Evidence cell, which Python resolves to that cell's
        ``E#`` label, and the issuer name is its run-text spelling (``run_text_name``); table
        text keeps the literal ``[E#]`` and the name as supplied.
        """
        fragments: list[str] = []
        citations: list[Citation] = []
        for part in passage:
            if isinstance(part, ProsePart):
                fragments.append(part.text)
            elif isinstance(part, IssuerPart):
                fragments.append(run_text_name(self.issuer_name) if chips else self.issuer_name)
            elif isinstance(part, EvidencePart):
                record = self.catalogue[part.evidence_id]
                identity = record.evidence_id
                marker = _trace_fact_id(identity) if chips else self.labels[identity]
                fragments.append(f"[{marker}]")
                citations.extend(record.citations)
                self.use(identity, owner)
        return "".join(fragments), tuple(dict.fromkeys(citations))


def _put(
    tables: _Tables,
    key: str,
    row: tuple[tuple[str, ...], str],
    values: tuple[str | _Cell, ...],
    refs: tuple[Citation, ...],
) -> None:
    """One projection row: ``row`` is its identity keys and period text; ``values`` follow the
    table's columns."""
    keys, period = row
    tables.row(key, keys, period, dict(zip(tables.schemas[key][2], values, strict=True)), refs)


def _finding_claims(report: NarrativeReport, resolver: _Resolver) -> list[Claim]:
    claims: list[Claim] = []
    for finding in report.review.findings:
        sections = []
        citations: list[Citation] = []
        for label, field_name, passage in (
            ("Evidence", "evidence", finding.evidence),
            ("Risk mechanic", "risk_mechanic", finding.risk_mechanic),
            ("Credit implication", "credit_implication", finding.credit_implication),
        ):
            text, refs = resolver.passage(passage, f"{finding.finding_id}/{field_name}", chips=True)
            sections.append(f"{label}\n{text}")
            citations.extend(refs)
        claims.append(
            Claim(
                claim_id=finding.finding_id,
                text=f"{finding.dimension.replace('_', ' ').capitalize()} · {finding.title}\n\n"
                + "\n\n".join(sections),
                citations=tuple(dict.fromkeys(citations)),
                limitation=(
                    "Analyst synthesis over referenced prior records. Inspect Evidence Trace for "
                    "exact values, units, periods, roles and hashes. "
                    "Semantic qualification is unrun."
                ),
            )
        )
    return claims


def _coverage_rows(tables: _Tables, report: NarrativeReport, resolver: _Resolver) -> None:
    coverage = {c.dimension: c for c in report.review.coverage}
    for dimension in _DIMENSIONS:
        assessment = coverage.get(dimension)
        if assessment:
            rationale, refs = resolver.passage(assessment.rationale, f"coverage/{dimension}")
            status, findings = assessment.status, assessment.finding_ids
        else:
            rationale, refs = "No coverage assessment supplied", ()
            status, findings = "unassessed", ()
        _put(
            tables,
            "analysis-coverage",
            ((dimension,), "Narrative scope: " + report.inputs.scope),
            (dimension, status, "; ".join(findings) or "None supplied", rationale),
            refs,
        )


def _funding_row(tables: _Tables, report: NarrativeReport, resolver: _Resolver) -> None:
    funding = report.review.funding
    rationale, refs = resolver.passage(funding.rationale, "funding/rationale")
    for role, identities in (
        ("reviewed", funding.reviewed_statement_ids),
        ("material", funding.material_statement_ids),
    ):
        for identity in identities:
            resolver.use(identity, "funding/" + role)
    _put(
        tables,
        "funding-assessment",
        (("funding",), "Declared prior balance-sheet scope"),
        (
            funding.status,
            "; ".join(funding.reviewed_statement_ids) or "None supplied",
            "; ".join(funding.material_statement_ids) or "None supplied",
            rationale,
        ),
        refs,
    )


def _story_rows(tables: _Tables, report: NarrativeReport, resolver: _Resolver) -> None:
    stories = {s.evidence_id: s for s in report.review.stories}
    for identity in report.required_story_ids:
        record = resolver.catalogue[identity]
        story = stories.get(identity)
        resolver.use(identity, "required-story")
        _put(
            tables,
            "required-stories",
            ((identity,), "See exact event or funding record"),
            (
                identity,
                record.kind,
                record.reference,
                "supplied" if story else "missing",
                "; ".join(story.finding_ids)
                if story
                else "No finding supplied; BLOCK gap retained",
            ),
            record.citations,
        )


def _trace_cell(record: EvidenceRecord, book: FinancialBook) -> _Cell:
    """The Fields cell of one evidence-trace row: the exact record as JSON-pointer lines. A
    statement cell carries its own quantity unit, currency and scale (as ``statement_view``
    states them: a per-share or shares cell keeps its family, never the book's) and its book
    period; any other record carries no dimension."""
    fields = "\n".join(_fields(json.loads(record.record_json)))
    if not record.kind.startswith("statement_"):
        return _Cell(fields, record.citations, note=NOT_INTRINSIC)
    cell = StatementCell.model_validate_json(record.record_json)
    period = next((p for p in book.periods if p.period_id == cell.period_id), None)
    return _Cell(
        fields,
        record.citations,
        unit=cell.quantity_unit,
        currency=cell.currency,
        scale=cell.factor,
        period=f"{period.period_id}: {period.start_date} to {period.end_date}" if period else None,
        note=STATEMENT_DIMENSIONS if period else STATEMENT_NO_PERIOD,
    )


def _trace_rows(tables: _Tables, book: FinancialBook, resolver: _Resolver) -> None:
    for identity, owners in resolver.uses.items():
        record = resolver.catalogue[identity]
        _put(
            tables,
            "evidence-trace",
            ((identity,), "Prior-record scope; inspect fields and canonical registers"),
            (
                resolver.labels[identity],
                identity,
                record.kind,
                record.reference,
                "; ".join(dict.fromkeys(owners)),
                record.artifact_sha256,
                record.record_sha256,
                _trace_cell(record, book),
            ),
            record.citations,
        )


def _statement_coverage_rows(tables: _Tables, book: FinancialBook, report: NarrativeReport) -> None:
    statement_cells = report.inputs.ledger.audit.statements.cells
    for period in book.periods:
        for statement in ("IS", "CFS", "BS"):
            rows = [
                c
                for c in statement_cells
                if c.period_id == period.period_id and c.statement == statement
            ]
            _put(
                tables,
                "statement-coverage",
                ((period.period_id, statement), f"{period.start_date} to {period.end_date}"),
                (
                    period.period_id,
                    statement,
                    str(sum(c.line_id is not None for c in rows)),
                    "; ".join(
                        c.item_id
                        for c in rows
                        if c.item_id in REQUIRED_ITEMS[statement] and c.status == "missing"
                    )
                    or "None in declared scope",
                    "; ".join(c.item_id for c in rows if c.status == "conflicting")
                    or "None in declared scope",
                    "; ".join(c.item_id for c in rows if c.status == "not_applicable")
                    or "None in declared scope",
                    "Point-in-time period; flow statement not applicable"
                    if period.period_type == "PERIOD_END" and statement != "BS"
                    else "Declared extraction only; filing completeness is unqualified",
                ),
                tuple(dict.fromkeys(c for row in rows for c in row.citations)),
            )


def project_narrative(
    book: FinancialBook, report: NarrativeReport, issuer_name: str
) -> NarrativeProjection:
    """Project caller-recomputed records; this helper does not authenticate inputs."""
    catalogue = {r.evidence_id: r for r in report.inputs.catalogue}
    resolver = _Resolver(
        issuer_name,
        catalogue,
        labels={identity: f"E{index}" for index, identity in enumerate(catalogue, 1)},
    )
    tables = _Tables(
        book,
        schemas={
            key: (title, None, tuple(c.lower().replace(" ", "_") for c in columns))
            for key, (title, _, columns) in SCHEMAS.items()
        },
    )
    claims = _finding_claims(report, resolver)
    _coverage_rows(tables, report, resolver)
    _funding_row(tables, report, resolver)
    _story_rows(tables, report, resolver)
    _trace_rows(tables, book, resolver)
    _statement_coverage_rows(tables, book, report)
    facts = tuple(
        f.model_copy(
            update={
                "label": f.table_id.replace("-", " ").capitalize() + " · " + f.field,
                "value_class": "analyst_judgment" if f.table_id in _ANALYST else None,
            }
        )
        for f in tables.facts
    )
    layouts = tuple(
        t.model_copy(
            update={
                "columns": tuple(
                    TableColumn(field=c.field, label=label)
                    for c, label in zip(t.columns, SCHEMAS[t.table_id][2], strict=True)
                ),
                "limitation": (
                    "Candidate projection of prior records and supplied analysis; "
                    "no analytical acceptance inferred."
                ),
            }
        )
        for t in tables.layouts()
    )
    bound = prose.bind(facts)
    names = (run_text_name(issuer_name),)
    for claim in claims:  # fail closed if a chip misses its trace row
        if found := prose.issues(claim.text, bound, names=names):
            raise ValueError(f"Narrative claim does not resolve: {claim.claim_id}: {found[0]}")
    return NarrativeProjection(tuple(claims), facts, layouts)
