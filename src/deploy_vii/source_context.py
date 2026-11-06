"""CP-1 source-first context: located classifications, scope and subsequent events.

Source readability is not analytical authority. This layer has no financial
arithmetic and does not apply subsequent events to historical observations.
"""

import re
from collections.abc import Iterator
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, ValidationError

from deploy_vii.contracts import (
    PREFILLED_MARKER,
    Citation,
    Contract,
    Hash,
    Identifier,
    Run,
    Source,
    Text,
)
from deploy_vii.financial_contracts import Currency, Located, Unit
from deploy_vii.financial_periods import _id
from deploy_vii.financial_validation import records
from deploy_vii.preparation import PreparedPack
from deploy_vii.prose import is_blank
from deploy_vii.readiness import absence_issues, citation_issues

EvidenceClass = Literal[
    "audited_financial_statements",
    "unaudited_with_auditor",
    "unaudited_without_auditor",
    "lender_sponsor",
    "rating",
    "internal",
    "external",
]
EvidenceTier = Literal["1", "2a", "2b", "2c", "2d", "3a", "3b"]
Role = Literal["issuer", "borrower", "guarantor_group", "restricted_group", "other"]
_TIERS: dict[EvidenceClass, EvidenceTier] = {
    "audited_financial_statements": "1",
    "unaudited_with_auditor": "2a",
    "unaudited_without_auditor": "2b",
    "lender_sponsor": "2c",
    "rating": "2d",
    "internal": "3a",
    "external": "3b",
}
# Task 7.14: a financial source's historical and period-end scopes state these four strings
# (rule 1), the same for every such scope of one entity (rule 2, `_disagreements`): the book's
# and its periods' strings are copied from them. Forecast and unspecified scopes are not bound.
# Task 8.0b: the one kind set and the one order of the four strings, shared with
# `context_binding` and `live.submission` (the order names the fields in their issues).
STATED_KINDS = frozenset({"historical_duration", "period_end"})
DIMENSIONS = ("currency", "unit", "entity_perimeter", "accounting_basis")


class EntityContext(Contract):
    entity_id: Identifier
    name: Text | None
    entity_type: Literal["legal_entity", "group", "unknown"]
    roles: tuple[Role, ...]
    fiscal_year_end: Text | None
    citations: tuple[Citation, ...]
    limitations: tuple[Text, ...] = ()


class ReportingScope(Contract):
    scope_id: Identifier
    entity_id: Identifier
    period_label: Text
    period_kind: Literal["historical_duration", "period_end", "forecast", "unspecified"]
    start_date: date | None
    end_date: date | None
    currency: Currency | None
    unit: Unit | None
    entity_perimeter: Text | None
    accounting_basis: Text | None
    citations: Located
    limitations: tuple[Text, ...] = ()


def scope_matches_period(
    scope: ReportingScope, period_type: str, start_date: date | None, end_date: date | None
) -> bool:
    """Task 8.0b: whether a period's type and dates select `scope`, the one rule
    `context_binding` binds by and the financials prefill (`live.submission._period_scopes`)
    fills from. A historical-duration or period-end scope with the period's end date; unless
    the period is `PERIOD_END`, a historical-duration scope with its start date too. Dates
    only: the entity and the four strings are each caller's own."""
    if scope.end_date is None or scope.end_date != end_date:
        return False
    if period_type == "PERIOD_END":
        return scope.period_kind in STATED_KINDS
    return (
        scope.period_kind == "historical_duration"
        and scope.start_date is not None
        and scope.start_date == start_date
    )


class SourceContext(Contract):
    source_id: Identifier
    classification: Literal["financial", "nonfinancial", "unassessed"]
    document_type: Text | None
    published_on: date | None
    evidence_class: EvidenceClass | None
    evidence_rationale: Text
    analytical_use: Text
    citations: tuple[Citation, ...]
    scopes: Annotated[tuple[ReportingScope, ...], Field(max_length=2000)] = ()
    event_scan: Literal["events_identified", "no_events_identified", "unassessed"] = "unassessed"
    event_ids: tuple[Identifier, ...] = ()
    event_scan_citations: tuple[Citation, ...] = ()
    event_scan_explanation: Text
    limitations: tuple[Text, ...] = ()


class SubsequentEvent(Contract):
    event_id: Identifier
    reporting_scope_id: Identifier
    event_date: date
    known_on: date
    status: Literal["completed", "announced", "proposed"]
    description: Text
    effect: Text
    citations: Located
    historical_treatment: Literal["excluded_from_reported_period"] = "excluded_from_reported_period"


class SourceContextReview(Contract):
    schema_version: Literal["source-context-review/1"] = "source-context-review/1"
    pack_sha256: Hash = Field(json_schema_extra={PREFILLED_MARKER: "pack"})
    entities: Annotated[tuple[EntityContext, ...], Field(max_length=2000)]
    sources: Annotated[tuple[SourceContext, ...], Field(max_length=2000)]
    events: Annotated[tuple[SubsequentEvent, ...], Field(max_length=20000)] = ()
    limitations: tuple[Text, ...] = ()


class ContextGap(Contract):
    gap_id: Identifier
    category: Literal[
        "source", "classification", "scope", "entity", "event_scan", "event", "limitation"
    ]
    reference: Text
    description: Text
    citations: tuple[Citation, ...]
    scope_ids: tuple[Identifier, ...] = ()


class SourceRegisterRow(Contract):
    source_id: Identifier
    filename: Text
    source_sha256: Hash | None
    availability: Literal["ready", "missing", "unreadable"]
    extraction_status: Literal["complete", "degraded", "blocked"]
    evidence_tier: EvidenceTier | None
    assessment: SourceContext
    extraction_limitations: tuple[Text, ...]


class EntityRegisterRow(Contract):
    entity: EntityContext
    scope_ids: tuple[Identifier, ...]
    source_ids: tuple[Identifier, ...]


class SourceContextReport(Contract):
    schema_version: Literal["source-context/2"] = "source-context/2"
    run: Run
    pack_sha256: Hash
    context_review_sha256: Hash
    status: Literal["candidate", "restricted", "blocked"]
    sources: tuple[SourceRegisterRow, ...]
    entities: tuple[EntityRegisterRow, ...]
    events: tuple[SubsequentEvent, ...]
    gaps: tuple[ContextGap, ...]
    limitations: tuple[Text, ...]


def exact_period_issues(pack: PreparedPack, review: SourceContextReview) -> tuple[str, ...]:
    """Bind stated dates to consolidated XBRL contexts retained at source ingestion.

    PDF-only documents retain the existing cited-date validation. An HTML filing
    with exact contexts cannot substitute calendar estimates for its fiscal dates.
    """
    pattern = re.compile(
        r"XBRL context [^;]+; entity [^;]+; scheme [^;]+; "
        r"(?:(duration) (\d{4}-\d{2}-\d{2}) through (\d{4}-\d{2}-\d{2})"
        r"|(instant) (\d{4}-\d{2}-\d{2}))"
    )
    sources = {s.source_id: s for s in pack.sources}
    issues = []
    for assessment in review.sources:
        source = sources.get(assessment.source_id)
        if source is None:
            continue
        dates = {
            ("historical_duration", m[2], m[3]) if m[1] else ("period_end", None, m[5])
            for span in source.spans
            for line in span.text.splitlines()
            if (m := pattern.fullmatch(line)) is not None
        }
        if not dates:
            continue
        for scope in assessment.scopes:
            if scope.period_kind not in STATED_KINDS:
                continue
            value = (
                scope.period_kind,
                scope.start_date.isoformat() if scope.start_date else None,
                scope.end_date.isoformat() if scope.end_date else None,
            )
            if value not in dates:
                issues.append(
                    f"Use exact source XBRL dates: {assessment.source_id} {scope.scope_id}"
                )
    return tuple(issues)


def validate_source_context(pack: PreparedPack, review: SourceContextReview) -> tuple[str, ...]:
    try:
        pack = PreparedPack.model_validate_json(pack.model_dump_json())
        review = SourceContextReview.model_validate_json(review.model_dump_json())
    except ValidationError as error:
        return (f"Invalid source context contract: {error}",)
    # Inventory and citation failures precede assertions about individual records.
    issues: list[str] = []
    issues.extend(exact_period_issues(pack, review))
    if review.pack_sha256 != pack.content_hash():
        issues.append("Source context does not bind current prepared pack")
    sources = {s.source_id: s for s in pack.sources}
    if (
        len(review.sources) != len(sources)
        or {s.source_id for s in review.sources} != sources.keys()
    ):
        issues.append("Assess every prepared source exactly once")
    entities = {e.entity_id: e for e in review.entities}
    if len(entities) != len(review.entities):
        issues.append("Duplicate entity identity")
    scopes = {scope.scope_id: scope for source in review.sources for scope in source.scopes}
    if len(scopes) != sum(len(s.scopes) for s in review.sources):
        issues.append("Duplicate reporting scope identity")
    events = {e.event_id: e for e in review.events}
    if len(events) != len(review.events):
        issues.append("Duplicate subsequent-event identity")
    issues.extend(citation_issues(tuple(records(review, Citation)), pack.sources))
    # Entity assertions must be located; unresolved fields need explicit limitations.
    for entity in review.entities:
        if len(set(entity.roles)) != len(entity.roles):
            issues.append(f"Duplicate entity role: {entity.entity_id}")
        has_assertions = bool(
            entity.name or entity.roles or entity.fiscal_year_end or entity.entity_type != "unknown"
        )
        if has_assertions and not entity.citations:
            issues.append(f"Entity assertions require located content: {entity.entity_id}")
        is_incomplete = (
            not entity.name
            or not entity.roles
            or not entity.fiscal_year_end
            or entity.entity_type == "unknown"
        )
        if is_incomplete and not entity.limitations:
            issues.append(f"Incomplete entity context requires limitation: {entity.entity_id}")
        issues.extend(_blank_limitations(entity.limitations, entity.entity_id))
    # Built once (0d-d): each event's cited sources, and every (source, event) a scan lists.
    event_sources = {key: {c.source_id for c in event.citations} for key, event in events.items()}
    scanned = {(s.source_id, event_id) for s in review.sources for event_id in s.event_ids}
    first_review: dict[str, SourceContext] = {}
    for item in review.sources:
        first_review.setdefault(item.source_id, item)
    # Source-local checks retain review order, including event attachments.
    referenced_events: set[str] = set()
    for assessment in review.sources:
        source = sources.get(assessment.source_id)
        if source is None:
            continue
        if source.status != "ready" and (
            assessment.classification != "unassessed"
            or assessment.scopes
            or assessment.evidence_class
            or assessment.event_scan != "unassessed"
            or assessment.document_type
            or assessment.published_on
        ):
            issues.append(f"Unavailable source cannot supply assessed context: {source.source_id}")
        if (assessment.document_type or assessment.published_on) and not assessment.citations:
            issues.append(f"Source metadata requires located content: {source.source_id}")
        if assessment.classification != "unassessed" and (
            not assessment.citations or not assessment.document_type
        ):
            issues.append(
                f"Source classification requires type and located content: {source.source_id}"
            )
        if assessment.classification == "unassessed" and (
            assessment.evidence_class or assessment.scopes
        ):
            issues.append(
                "Unassessed source cannot supply evidence tier or reporting scope: "
                f"{source.source_id}"
            )
        if assessment.published_on and assessment.published_on > pack.run.as_of:
            issues.append(f"Source publication is after as-of date: {source.source_id}")
        if any(
            c.source_id != source.source_id
            for c in (*assessment.citations, *assessment.event_scan_citations)
        ):
            issues.append(f"Source context cites another source: {source.source_id}")
        for scope in assessment.scopes:
            if scope.entity_id not in entities:
                issues.append(f"Unknown scope entity: {scope.scope_id}")
            if any(c.source_id != source.source_id for c in scope.citations):
                issues.append(f"Reporting scope cites another source: {scope.scope_id}")
            if scope.start_date and scope.end_date and scope.start_date > scope.end_date:
                issues.append(f"Reversed reporting dates: {scope.scope_id}")
            if scope.period_kind == "period_end" and scope.start_date is not None:
                issues.append(f"Period-end scope cannot have a start date: {scope.scope_id}")
            if (
                scope.period_kind != "forecast"
                and scope.end_date
                and scope.end_date > pack.run.as_of
            ):
                issues.append(f"Historical reporting scope ends after as-of date: {scope.scope_id}")
            if (
                scope.period_kind in STATED_KINDS
                and scope.end_date
                and assessment.published_on
                and scope.end_date > assessment.published_on
            ):
                issues.append(
                    f"Historical reporting scope ends after publication: {scope.scope_id}"
                )
            issues.extend(_lacks(assessment, scope))
            issues.extend(_blank_limitations(scope.limitations, scope.scope_id))
        issues.extend(_blank_limitations(assessment.limitations, source.source_id))
        if is_blank(assessment.event_scan_explanation):
            issues.append(f"Empty event scan explanation: {source.source_id}")
        source_event_ids = set(assessment.event_ids)
        if (
            len(source_event_ids) != len(assessment.event_ids)
            or not source_event_ids <= events.keys()
        ):
            issues.append(f"Duplicate or unknown source event: {source.source_id}")
        if (assessment.event_scan == "events_identified") != bool(assessment.event_ids):
            issues.append(f"Event scan conclusion and references disagree: {source.source_id}")
        if assessment.event_scan != "unassessed" and not assessment.event_scan_citations:
            issues.append(f"Event scan requires located evidence: {source.source_id}")
        for event_id in assessment.event_ids:
            if event_id in events and source.source_id not in event_sources[event_id]:
                issues.append(
                    f"Event attachment lacks evidence from source: {source.source_id} {event_id}"
                )
        referenced_events.update(assessment.event_ids)
    issues.extend(_disagreements(review))
    # Event chronology and evidence coverage follow all source-local checks.
    for event in review.events:
        event_scope = scopes.get(event.reporting_scope_id)
        if (
            event_scope is None
            or event_scope.end_date is None
            or event_scope.period_kind not in STATED_KINDS
        ):
            issues.append(f"Subsequent event requires a dated historical scope: {event.event_id}")
        elif event.event_date <= event_scope.end_date:
            issues.append(f"Event is not after reporting period: {event.event_id}")
        if event.known_on > pack.run.as_of or (
            event.status == "completed" and event.event_date > pack.run.as_of
        ):
            issues.append(f"Subsequent event is not known at as-of date: {event.event_id}")
        if event.status == "completed" and event.known_on < event.event_date:
            issues.append(f"Completion evidence precedes event date: {event.event_id}")
        if event.event_id not in referenced_events:
            issues.append(f"Subsequent event is absent from source scans: {event.event_id}")
        for source_id in sorted({c.source_id for c in event.citations}):
            source_review = first_review.get(source_id)
            if (
                source_review
                and source_review.published_on
                and event.known_on > source_review.published_on
            ):
                issues.append(
                    f"Event knowledge date is after cited publication: {source_id} {event.event_id}"
                )
            if (source_id, event.event_id) not in scanned:
                issues.append(
                    f"Event evidence omitted by source scan: {source_id} {event.event_id}"
                )
    issues.extend(_blank_limitations(review.limitations, "review"))
    issues.extend(absence_issues(pack, _prose_scopes(review)))
    return tuple(issues)


def _blank_limitations(limitations: tuple[str, ...], where: str) -> Iterator[str]:
    """OI-14: `Text` refuses only `""`; a limitation of whitespace or invisible characters
    (`prose.is_blank`) renders a blank gap row. One issue per blank limitation; the text is
    not echoed."""
    for limitation in limitations:
        if is_blank(limitation):
            yield f"Empty limitation text: {where}"


def _lacks(assessment: SourceContext, scope: ReportingScope) -> Iterator[str]:
    """Task 7.14, rule 1: a historical or period-end scope of a financial source states all
    four dimensions; one issue per missing or blank (`prose.is_blank`) field. Forecast and
    unspecified scopes, and a non-financial source's scopes, are not held to it."""
    if assessment.classification == "financial" and scope.period_kind in STATED_KINDS:
        for name in DIMENSIONS:
            value = getattr(scope, name)
            if value is None or is_blank(value):
                yield f"Financial scope lacks {name}: {scope.scope_id}"


def _disagreements(review: SourceContextReview) -> Iterator[str]:
    """Task 7.14 (batches e1-cp1-13/-14), rule 2: the historical and period-end scopes of one
    entity, over every financial source, state the same four strings. Those are the scopes
    `context_binding` and the financials prefill (`live.submission._period_scopes`) choose from
    by entity and dates alone, so one book's periods must find one tuple. Compared exactly, with
    no normalisation; a null or blank is rule 1's issue alone. One issue per entity and field,
    naming the scope ids that share each stated value, in review order."""
    by_entity: dict[str, list[ReportingScope]] = {}
    for source in review.sources:
        if source.classification == "financial":
            for scope in source.scopes:
                if scope.period_kind in STATED_KINDS:
                    by_entity.setdefault(scope.entity_id, []).append(scope)
    for entity_id, scopes in by_entity.items():
        for name in DIMENSIONS:
            stated: dict[str, list[str]] = {}
            for scope in scopes:
                value = getattr(scope, name)
                if value is not None and not is_blank(value):
                    stated.setdefault(value, []).append(scope.scope_id)
            if len(stated) > 1:
                yield (
                    f"Financial scopes of one entity disagree on {name}: {entity_id} "
                    + " vs ".join(", ".join(ids) for ids in stated.values())
                )


def _prose(item: BaseModel) -> Iterator[str]:
    """Every text value of a contract outside its citations (a quote is source text, not a
    claim), nested records included."""
    for name in type(item).model_fields:
        value = getattr(item, name)
        for child in value if isinstance(value, tuple) else (value,):
            if isinstance(child, Citation):
                continue
            if isinstance(child, BaseModel):
                yield from _prose(child)
            elif isinstance(child, str):
                yield child


def _prose_scopes(review: SourceContextReview) -> Iterator[tuple[str, tuple[str, ...]]]:
    """Each free text with the sources it is about, for the readiness absence rule (decision
    0008, task 2.9): a source context (and its scopes) is about its source; an entity or event
    about the sources it cites; the review's own limitations about every paged source."""
    for assessment in review.sources:
        yield from ((text, (assessment.source_id,)) for text in _prose(assessment))
    records: tuple[EntityContext | SubsequentEvent, ...] = (*review.entities, *review.events)
    for record in records:
        cited = tuple(c.source_id for c in record.citations)
        yield from ((text, cited) for text in _prose(record))
    yield from ((text, ()) for text in review.limitations)


GapCategory = Literal[
    "source", "classification", "scope", "entity", "event_scan", "event", "limitation"
]


def _gap(
    category: GapCategory,
    reference: str,
    description: str,
    citations: tuple[Citation, ...] = (),
    scope_ids: tuple[str, ...] = (),
) -> ContextGap:
    return ContextGap(
        gap_id=_id("context-gap", category, reference, description),
        category=category,
        reference=reference,
        description=description,
        citations=citations,
        scope_ids=scope_ids,
    )


def _scope_gaps(scope: ReportingScope) -> Iterator[ContextGap]:
    """An unresolved field (absent, or blank text: `prose.is_blank`) and each limitation."""
    missing = [
        name
        for name in ("end_date", *DIMENSIONS)
        if (value := getattr(scope, name)) is None or (isinstance(value, str) and is_blank(value))
    ]
    if scope.period_kind in {"historical_duration", "forecast"} and scope.start_date is None:
        missing.append("start_date")
    if scope.period_kind == "unspecified":
        missing.append("period_kind")
    located = scope.citations, (scope.scope_id,)
    if missing:
        yield _gap("scope", scope.scope_id, "Unresolved scope: " + ", ".join(missing), *located)
    for limitation in scope.limitations:
        yield _gap("scope", scope.scope_id, limitation, *located)


def _source_gaps(
    source: Source, assessment: SourceContext, extraction_limits: tuple[str, ...]
) -> Iterator[ContextGap]:
    """One prepared source's availability, classification, scope, event-scan and limitation
    gaps, in that order."""
    source_id, cited = source.source_id, assessment.citations
    if source.status != "ready" or source.extraction_status != "complete":
        yield _gap(
            "source", source_id, f"Source {source.status}; extraction {source.extraction_status}"
        )
    for limitation in extraction_limits:
        yield _gap("source", source_id, limitation)
    if assessment.classification == "unassessed":
        yield _gap("classification", source_id, "Financial relevance has not been assessed")
    if assessment.evidence_class is None:
        yield _gap(
            "classification", source_id, "Evidence quality tier has not been assessed", cited
        )
    if assessment.published_on is None:
        yield _gap("classification", source_id, "Publication date is unavailable", cited)
    if not assessment.scopes:
        yield _gap("scope", source_id, "Source has no located entity/period scope", cited)
    for scope in assessment.scopes:
        yield from _scope_gaps(scope)
    if assessment.event_scan == "unassessed":
        yield _gap(
            "event_scan",
            source_id,
            assessment.event_scan_explanation,
            assessment.event_scan_citations,
        )
    for limitation in assessment.limitations:
        yield _gap("limitation", source_id, limitation, cited)


def _entity_gaps(
    entity: EntityContext, mapped: list[tuple[str, ReportingScope]]
) -> Iterator[ContextGap]:
    """An entity's differing scope strings (an absent or blank one is its scope's gap alone),
    a missing scope and its limitations."""
    for field in DIMENSIONS:
        values = {getattr(scope, field) for _, scope in mapped} - {None}
        values = {value for value in values if not is_blank(value)}
        if len(values) > 1:
            yield _gap(
                "scope",
                entity.entity_id,
                f"Different source {field} values require normalization review",
                tuple(dict.fromkeys(c for _, scope in mapped for c in scope.citations)),
                tuple(scope.scope_id for _, scope in mapped),
            )
    if not mapped:
        yield _gap(
            "entity",
            entity.entity_id,
            "Entity is not mapped to a reporting scope",
            entity.citations,
        )
    for limitation in entity.limitations:
        yield _gap("entity", entity.entity_id, limitation, entity.citations)


def _register_row(
    source: Source, assessment: SourceContext, extraction_limits: tuple[str, ...]
) -> SourceRegisterRow:
    return SourceRegisterRow(
        source_id=source.source_id,
        filename=source.name,
        source_sha256=source.sha256,
        availability=source.status,
        extraction_status=source.extraction_status,
        evidence_tier=None
        if assessment.evidence_class is None
        else _TIERS[assessment.evidence_class],
        assessment=assessment,
        extraction_limitations=extraction_limits,
    )


def source_context(pack: PreparedPack, review: SourceContextReview) -> SourceContextReport:
    issues = validate_source_context(pack, review)
    if issues:
        raise ValueError("; ".join(issues))
    pack = PreparedPack.model_validate_json(pack.model_dump_json())
    review = SourceContextReview.model_validate_json(review.model_dump_json())
    gaps: list[ContextGap] = []
    assessments = {s.source_id: s for s in review.sources}
    rows: list[SourceRegisterRow] = []
    financial_sources = 0
    for source in pack.sources:
        assessment = assessments[source.source_id]
        extraction_limits = tuple(
            dict.fromkeys(
                (
                    *((source.limitation,) if source.limitation else ()),
                    *(c.limitation for c in source.coverage if c.limitation),
                )
            )
        )
        if source.status == "ready" and assessment.classification == "financial":
            financial_sources += 1
        gaps.extend(_source_gaps(source, assessment, extraction_limits))
        rows.append(_register_row(source, assessment, extraction_limits))
    entity_rows: list[EntityRegisterRow] = []
    for entity in review.entities:
        mapped = [
            (s.source_id, scope)
            for s in review.sources
            for scope in s.scopes
            if scope.entity_id == entity.entity_id
        ]
        gaps.extend(_entity_gaps(entity, mapped))
        entity_rows.append(
            EntityRegisterRow(
                entity=entity,
                scope_ids=tuple(scope.scope_id for _, scope in mapped),
                source_ids=tuple(dict.fromkeys(sid for sid, _ in mapped)),
            )
        )
    for role in ("issuer", "borrower", "guarantor_group", "restricted_group"):
        if not any(role in e.roles for e in review.entities):
            gaps.append(_gap("entity", role, f"No located {role} scope supplied"))
    for event in review.events:
        gaps.append(
            _gap(
                "event",
                event.event_id,
                f"Subsequent event ({event.status}) excluded from historical figures: "
                f"{event.description}; {event.effect}",
                event.citations,
                (event.reporting_scope_id,),
            )
        )
    gaps.extend(_gap("limitation", "review", limitation) for limitation in review.limitations)
    if not financial_sources:
        gaps.append(
            _gap("source", "file-gate", "No readable source assessed as containing financial data")
        )
    return SourceContextReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        context_review_sha256=review.content_hash(),
        status="blocked" if not financial_sources else "restricted" if gaps else "candidate",
        sources=tuple(rows),
        entities=tuple(entity_rows),
        events=review.events,
        gaps=tuple(dict.fromkeys(gaps)),
        limitations=(
            (
                "Source context is a located analyst assessment, "
                "not financial or analytical acceptance"
            ),
            (
                "Evidence tiers describe source authority; they do not certify every figure "
                "or resolve conflicting values"
            ),
            *review.limitations,
        ),
    )


def validate_source_context_report(
    pack: PreparedPack, review: SourceContextReview, report: SourceContextReport
) -> tuple[str, ...]:
    try:
        report = SourceContextReport.model_validate_json(report.model_dump_json())
        expected = source_context(pack, review)
    except ValueError as error:
        return (f"Invalid source context report: {error}",)
    return (
        ()
        if report.content_hash() == expected.content_hash()
        else ("Source context differs from recomputed registers",)
    )
