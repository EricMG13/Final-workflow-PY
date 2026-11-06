"""CP-1 synthesis over prior registers; model prose cannot supply numeric fields."""

from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from deploy_vii import prose
from deploy_vii.canonical_audit import DefinitionReview
from deploy_vii.canonical_gaps import CanonicalGapReport, GapDetail, LedgerGap, canonical_gaps
from deploy_vii.context_binding import FinancialContextBinding
from deploy_vii.contracts import PREFILLED_MARKER, Citation, Contract, Hash, Identifier, Text
from deploy_vii.financial_contracts import FinancialReview
from deploy_vii.financial_periods import _id
from deploy_vii.financial_validation import records
from deploy_vii.preparation import PreparedPack
from deploy_vii.source_context import SourceContextReview
from deploy_vii.statement_output import StatementCell
from deploy_vii.statement_validation import OPTIONAL_ITEMS, REQUIRED_ITEMS

Dimension = Literal[
    "leverage",
    "coverage",
    "cash_flow_quality",
    "liquidity",
    "data_quality",
    "definition_risks",
    "key_gaps",
]
_DIMENSIONS: tuple[Dimension, ...] = (
    "leverage",
    "coverage",
    "cash_flow_quality",
    "liquidity",
    "data_quality",
    "definition_risks",
    "key_gaps",
)
_FINANCIAL = {"leverage", "coverage", "cash_flow_quality", "liquidity"}


def _prose(value: str) -> str:
    """Labels (periods, filings, instruments, sections, versions) pass; a bare figure fails.

    The shared run-text rule (``prose.check``, decision 0005 MC-2) with no resolvable ids:
    numbers and gaps enter CP-1 prose only as evidence parts, so any run reference fails too.
    """
    issues = prose.check(value, refs=(), gaps=())
    if prose.is_blank(value) or issues:
        raise ValueError(
            "Narrative prose must be nonblank and use evidence references for numbers"
            + "".join(f"; {issue}" for issue in issues)
        )
    return value


Prose = Annotated[Text, AfterValidator(_prose)]


class ProsePart(Contract):
    kind: Literal["prose"] = "prose"
    text: Prose


class EvidencePart(Contract):
    kind: Literal["evidence"] = "evidence"
    evidence_id: Identifier


class IssuerPart(Contract):
    kind: Literal["issuer"] = "issuer"


Part = Annotated[ProsePart | EvidencePart | IssuerPart, Field(discriminator="kind")]
Passage = Annotated[tuple[Part, ...], Field(min_length=1, max_length=100)]


class EvidenceRecord(Contract):
    evidence_id: Identifier
    kind: Text
    reference: Text
    artifact_sha256: Hash
    record_sha256: Hash
    # Exact serialized prior row, never model-authored replacement data.
    record_json: Text
    citations: tuple[Citation, ...]


class NarrativeInputs(Contract):
    schema_version: Literal["narrative-inputs/1"] = "narrative-inputs/1"
    ledger: CanonicalGapReport
    catalogue: tuple[EvidenceRecord, ...]
    scope: Literal["financial_synthesis", "data_quality_only"]


class Finding(Contract):
    finding_id: Identifier
    dimension: Dimension
    title: Prose
    evidence: Passage
    risk_mechanic: Passage
    credit_implication: Passage


class DimensionCoverage(Contract):
    dimension: Dimension
    status: Literal["addressed", "unassessed", "not_applicable"]
    finding_ids: tuple[Identifier, ...]
    rationale: Passage


class StoryCoverage(Contract):
    evidence_id: Identifier
    finding_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]


class FundingAssessment(Contract):
    status: Literal["unassessed", "no_material_items", "material_items"]
    reviewed_statement_ids: tuple[Identifier, ...]
    material_statement_ids: tuple[Identifier, ...]
    rationale: Passage


class NarrativeReview(Contract):
    schema_version: Literal["narrative-review/1"] = "narrative-review/1"
    inputs_sha256: Hash = Field(json_schema_extra={PREFILLED_MARKER: "step-inputs"})
    findings: Annotated[tuple[Finding, ...], Field(max_length=20000)] = ()
    coverage: tuple[DimensionCoverage, ...] = ()
    stories: tuple[StoryCoverage, ...] = ()
    funding: FundingAssessment
    limitations: tuple[Prose, ...] = ()


class NarrativeReport(Contract):
    schema_version: Literal["canonical-narrative/1"] = "canonical-narrative/1"
    inputs: NarrativeInputs
    review: NarrativeReview
    required_story_ids: tuple[Identifier, ...]
    gaps: tuple[LedgerGap, ...]
    status: Literal["candidate", "restricted", "blocked"]
    analytical_qualification: Literal["unrun"] = "unrun"
    limitations: tuple[Text, ...]


def _catalogue(ledger: CanonicalGapReport) -> tuple[EvidenceRecord, ...]:
    result: list[EvidenceRecord] = []

    def add(kind: str, reference: str, artifact_hash: str, row: Contract) -> None:
        result.append(
            EvidenceRecord(
                evidence_id=_id("narrative-evidence", kind, reference),
                kind=kind,
                reference=reference,
                artifact_sha256=artifact_hash,
                record_sha256=row.content_hash(),
                record_json=row.model_dump_json(),
                citations=tuple(dict.fromkeys(records(row, Citation))),
            )
        )

    context, audit = ledger.context, ledger.audit
    context_hash, audit_hash, ledger_hash = (
        context.content_hash(),
        audit.content_hash(),
        ledger.content_hash(),
    )
    for source in context.sources:
        add("source", source.source_id, context_hash, source)
    for entity in context.entities:
        add("entity", entity.entity.entity_id, context_hash, entity)
    for event in context.events:
        add("subsequent_event", event.event_id, context_hash, event)
    for position in audit.source_positions:
        add("observation", position.observation.observation_id, audit_hash, position)
    statement_hash = audit.statements.content_hash()
    for cell in audit.statements.cells:
        add(
            "statement_" + cell.statement,
            _id("cell", cell.statement, cell.period_id, cell.item_id),
            statement_hash,
            cell,
        )
    for row in audit.normalizations:
        add("normalization", row.normalization_id, audit_hash, row)
    for definition in audit.definitions:
        add(
            "multi_figure_event" if definition.kind == "multi_figure_event" else "definition",
            definition.row_id,
            audit_hash,
            definition,
        )
    reconciliation_hash = audit.reconciliation.content_hash()
    for check in audit.reconciliation.checks:
        add("source_check", check.check_id, reconciliation_hash, check)
    for gap in ledger.gaps:
        add("gap", gap.gap_id, ledger_hash, gap)
    if ledger.kpis:
        kpis = ledger.kpis
        historical_hash, kpi_hash = kpis.historical.content_hash(), kpis.content_hash()
        for period in kpis.historical.periods:
            add("source_period", period.period_id, historical_hash, period)
        for construction in kpis.historical.constructions:
            add("construction", construction.construction_id, historical_hash, construction)
        for historical_value in kpis.historical.values:
            add("historical_value", historical_value.value_id, historical_hash, historical_value)
        for basis in kpis.bases:
            add("basis", basis.basis_id, kpi_hash, basis)
        for value in kpis.values:
            add("canonical_value", value.value_id, kpi_hash, value)
        for kpi in kpis.kpis:
            add("kpi", kpi.calculation_id, kpi_hash, kpi)
        for computation in kpis.computations:
            add("computation", computation.computation_id, kpi_hash, computation)
    if ledger.period_reconciliation:
        report_hash = ledger.period_reconciliation.content_hash()
        for period_check in ledger.period_reconciliation.checks:
            add("period_check", period_check.check_id, report_hash, period_check)
    if len(result) != len({r.evidence_id for r in result}):
        raise ValueError("Ambiguous narrative evidence identity")
    return tuple(result)


def _scope(ledger: CanonicalGapReport) -> Literal["financial_synthesis", "data_quality_only"]:
    """Financial synthesis when a KPI has an amount; data quality only otherwise."""
    if ledger.kpis and any(k.value.amount is not None for k in ledger.kpis.kpis):
        return "financial_synthesis"
    return "data_quality_only"


def narrative_inputs(
    pack: PreparedPack,
    context: SourceContextReview,
    financial: FinancialReview,
    definition: DefinitionReview,
    binding: FinancialContextBinding,
) -> NarrativeInputs:
    ledger = canonical_gaps(pack, context, financial, definition, binding)
    return NarrativeInputs(ledger=ledger, catalogue=_catalogue(ledger), scope=_scope(ledger))


def _balance_sheet(catalogue: tuple[EvidenceRecord, ...]) -> dict[str, StatementCell]:
    """The catalogue's balance-sheet statement cells by evidence id."""
    return {
        r.evidence_id: StatementCell.model_validate_json(r.record_json)
        for r in catalogue
        if r.kind == "statement_BS"
    }


def _required_story_ids(
    catalogue: tuple[EvidenceRecord, ...], material: tuple[str, ...]
) -> tuple[str, ...]:
    """The records that need a story: each event record, then each material funding row."""
    events = (
        r.evidence_id for r in catalogue if r.kind in {"subsequent_event", "multi_figure_event"}
    )
    return tuple(dict.fromkeys((*events, *material)))


def _contract_issue(inputs: NarrativeInputs) -> str | None:
    """Whether the inputs are the ones their own registers recompute (may raise ValueError)."""
    if inputs.catalogue != _catalogue(inputs.ledger):
        return "Narrative catalogue differs from its prior registers"
    if inputs.scope != _scope(inputs.ledger):
        return "Narrative scope differs from available KPI evidence"
    return None


def _identity_issues(inputs: NarrativeInputs, review: NarrativeReview) -> list[str]:
    """The input binding, duplicate identities and unknown evidence ids."""
    issues: list[str] = []
    if review.inputs_sha256 != inputs.content_hash():
        issues.append("Narrative review does not bind current input registers")
    if len(review.findings) != len({f.finding_id for f in review.findings}):
        issues.append("Duplicate narrative finding identity")
    if len(review.coverage) != len({c.dimension for c in review.coverage}):
        issues.append("Duplicate narrative dimension coverage")
    if len(review.stories) != len({s.evidence_id for s in review.stories}):
        issues.append("Duplicate required-story coverage")
    evidence = {r.evidence_id for r in inputs.catalogue}
    issues.extend(
        f"Unknown narrative evidence: {part.evidence_id}"
        for part in records(review, EvidencePart)
        if part.evidence_id not in evidence
    )
    return issues


def _finding_issues(finding: Finding, scope: str) -> list[str]:
    """One finding's evidence, issuer binding, reasoning and scope."""
    issues: list[str] = []
    if not any(isinstance(p, EvidencePart) for p in finding.evidence):
        issues.append(f"Finding lacks prior-register evidence: {finding.finding_id}")
    if not any(
        isinstance(p, IssuerPart)
        for p in (*finding.evidence, *finding.risk_mechanic, *finding.credit_implication)
    ):
        issues.append(f"Finding lacks explicit issuer binding: {finding.finding_id}")
    for name, passage in (("risk", finding.risk_mechanic), ("credit", finding.credit_implication)):
        if not any(isinstance(p, ProsePart) for p in passage):
            issues.append(f"Finding lacks {name} reasoning: {finding.finding_id}")
    if scope == "data_quality_only" and finding.dimension in _FINANCIAL:
        issues.append(f"Financial narrative requires an available KPI: {finding.finding_id}")
    return issues


def _dimension_issues(
    coverage: DimensionCoverage, findings: dict[str, Finding], supplied: set[str]
) -> list[str]:
    """One coverage entry against the findings; ``supplied`` holds its dimension's findings."""
    issues: list[str] = []
    dimension, ids = coverage.dimension, coverage.finding_ids
    if not any(isinstance(p, ProsePart) for p in coverage.rationale):
        issues.append(f"Dimension lacks rationale: {dimension}")
    if len(ids) != len(set(ids)) or any(
        i not in findings or findings[i].dimension != dimension for i in ids
    ):
        issues.append(f"Invalid dimension findings: {dimension}")
    if (coverage.status == "addressed") != bool(ids):
        issues.append(f"Dimension status contradicts findings: {dimension}")
    if set(ids) != supplied:
        issues.append(f"Dimension omits or contradicts supplied findings: {dimension}")
    if coverage.status == "not_applicable" and not any(
        isinstance(p, EvidencePart) for p in coverage.rationale
    ):
        issues.append(f"Inapplicable dimension lacks evidence: {dimension}")
    return issues


def _coverage_issues(review: NarrativeReview, findings: dict[str, Finding]) -> list[str]:
    """Each coverage entry, then each dimension whose findings have no coverage entry (review
    S04: its findings would show beside an "unassessed" coverage row)."""
    by_dimension: dict[Dimension, set[str]] = {d: set() for d in _DIMENSIONS}
    for finding in review.findings:
        by_dimension[finding.dimension].add(finding.finding_id)
    issues = [
        issue
        for coverage in review.coverage
        for issue in _dimension_issues(coverage, findings, by_dimension[coverage.dimension])
    ]
    covered = {c.dimension for c in review.coverage}
    issues.extend(
        f"Dimension findings lack coverage: {dimension}"
        for dimension in _DIMENSIONS
        if by_dimension[dimension] and dimension not in covered
    )
    return issues


def _funding_issues(inputs: NarrativeInputs, funding: FundingAssessment) -> list[str]:
    """The funding conclusion against the located prior balance-sheet rows."""
    reviewed, material = funding.reviewed_statement_ids, funding.material_statement_ids
    issues: list[str] = []
    if not any(isinstance(p, ProsePart) for p in funding.rationale):
        issues.append("Funding assessment lacks rationale")
    balance_sheet = _balance_sheet(inputs.catalogue)
    for ids in (reviewed, material):
        if len(ids) != len(set(ids)) or any(
            i not in balance_sheet or balance_sheet[i].line_id is None for i in ids
        ):
            issues.append("Funding assessment requires distinct located prior balance-sheet rows")
    standard_items = {*REQUIRED_ITEMS["BS"], *OPTIONAL_ITEMS["BS"]}
    for evidence_id in material:
        cell = balance_sheet.get(evidence_id)
        if cell and (cell.line_kind != "detail" or cell.item_id in standard_items):
            issues.append(f"Funding story requires named non-debt liability detail: {evidence_id}")
    if not set(material) <= set(reviewed):
        issues.append("Material funding rows must be part of the reviewed scope")
    if (funding.status == "material_items") != bool(material):
        issues.append("Funding conclusion contradicts material rows")
    if funding.status != "unassessed" and not reviewed:
        issues.append("Assessed funding conclusion requires reviewed balance-sheet scope")
    return issues


def _story_issues(
    inputs: NarrativeInputs, review: NarrativeReview, findings: dict[str, Finding]
) -> list[str]:
    """Each story names a required record and findings that cite it."""
    required = set(_required_story_ids(inputs.catalogue, review.funding.material_statement_ids))
    cited = {
        finding_id: {p.evidence_id for p in finding.evidence if isinstance(p, EvidencePart)}
        for finding_id, finding in findings.items()
    }
    issues: list[str] = []
    for story in review.stories:
        if story.evidence_id not in required:
            issues.append(f"Unknown required story: {story.evidence_id}")
        if len(story.finding_ids) != len(set(story.finding_ids)):
            issues.append(f"Duplicate story finding: {story.evidence_id}")
        issues.extend(
            f"Story finding lacks its required evidence: {story.evidence_id} {finding_id}"
            for finding_id in story.finding_ids
            if story.evidence_id not in cited.get(finding_id, set())
        )
    return issues


def validate_narrative_review(inputs: NarrativeInputs, review: NarrativeReview) -> tuple[str, ...]:
    """Validate against supplied inputs; canonical_narrative recomputes those inputs."""
    try:
        inputs = NarrativeInputs.model_validate_json(inputs.model_dump_json())
        review = NarrativeReview.model_validate_json(review.model_dump_json())
        refused = _contract_issue(inputs)
    except ValueError as error:
        return (f"Invalid narrative contract: {error}",)
    if refused is not None:
        return (refused,)
    findings = {f.finding_id: f for f in review.findings}
    return (
        *_identity_issues(inputs, review),
        *(issue for f in review.findings for issue in _finding_issues(f, inputs.scope)),
        *_coverage_issues(review, findings),
        *_funding_issues(inputs, review.funding),
        *_story_issues(inputs, review, findings),
    )


def _narrative_gaps(inputs: NarrativeInputs, review: NarrativeReview) -> list[tuple[str, str]]:
    """The WARN gaps of an accepted review, as (reference, description): unassessed
    dimensions, the data-quality-only scope and the funding review's scope."""
    found: list[tuple[str, str]] = []
    coverage = {c.dimension: c for c in review.coverage}
    for dimension in _DIMENSIONS:
        if inputs.scope == "data_quality_only" and dimension in _FINANCIAL:
            continue
        if dimension not in coverage or coverage[dimension].status == "unassessed":
            found.append((dimension, f"Narrative dimension is unassessed: {dimension}"))
    if inputs.scope == "data_quality_only":
        found.append(
            ("financial-synthesis", "No available KPI: narrative is limited to data quality")
        )
    funding = review.funding
    if funding.status == "unassessed":
        found.append(
            ("funding-liabilities", "Material non-debt funding liabilities have not been assessed")
        )
    located_bs = {
        i for i, cell in _balance_sheet(inputs.catalogue).items() if cell.line_id is not None
    }
    if funding.status != "unassessed" and not located_bs <= set(funding.reviewed_statement_ids):
        found.append(
            (
                "funding-review-coverage",
                "Funding review does not cover every located balance-sheet row",
            )
        )
    return found


def canonical_narrative(
    pack: PreparedPack,
    context: SourceContextReview,
    financial: FinancialReview,
    definition: DefinitionReview,
    binding: FinancialContextBinding,
    review: NarrativeReview,
) -> NarrativeReport:
    inputs = narrative_inputs(pack, context, financial, definition, binding)
    issues = validate_narrative_review(inputs, review)
    if issues:
        raise ValueError("; ".join(issues))
    review = NarrativeReview.model_validate_json(review.model_dump_json())
    gaps = list(inputs.ledger.gaps)
    review_hash = review.content_hash()
    book_id = inputs.ledger.audit.definition_review.book_id

    def gap(reference: str, description: str, severity: Literal["WARN", "BLOCK"] = "WARN") -> None:
        detail = GapDetail(
            origin="narrative",
            artifact_sha256=review_hash,
            reference=reference,
            metric=None,
            periods=(),
            description=description,
            severity=severity,
            citations=(),
            downstream_impact="CP-1 analytical synthesis remains incomplete or limited",
            recommended_action=(
                "Review the prior registers and supply an evidence-risk-credit chain"
            ),
        )
        gaps.append(
            LedgerGap(gap_id=_id("cp1-gap", book_id, detail.content_hash()), **dict(detail))
        )

    for reference, description in _narrative_gaps(inputs, review):
        gap(reference, description)
    required = _required_story_ids(inputs.catalogue, review.funding.material_statement_ids)
    supplied = {s.evidence_id for s in review.stories}
    for story_id in required:
        if story_id not in supplied:
            gap(story_id, "Required event or non-debt funding story is missing", "BLOCK")
    for i, limitation in enumerate(review.limitations):
        gap(f"limitation:{i}", limitation)
    return NarrativeReport(
        inputs=inputs,
        review=review,
        required_story_ids=required,
        gaps=tuple(gaps),
        status="blocked"
        if any(g.severity == "BLOCK" for g in gaps)
        else "restricted"
        if gaps
        else "candidate",
        limitations=(
            (
                "Structural evidence binding cannot prove issuer-specific meaning, "
                "materiality or reasoning quality"
            ),
            (
                "All numeric evidence is supplied by prior registers; "
                "prose still requires semantic review"
            ),
            (
                "Funding classification is an analyst synthesis over prior balance-sheet rows, "
                "not new extraction"
            ),
            (
                "No consumer readiness, analytical qualification "
                "or completed Module acceptance is inferred"
            ),
        ),
    )


def validate_canonical_narrative(
    pack: PreparedPack,
    context: SourceContextReview,
    financial: FinancialReview,
    definition: DefinitionReview,
    binding: FinancialContextBinding,
    review: NarrativeReview,
    report: NarrativeReport,
) -> tuple[str, ...]:
    try:
        report = NarrativeReport.model_validate_json(report.model_dump_json())
        expected = canonical_narrative(pack, context, financial, definition, binding, review)
    except ValueError as error:
        return (f"Invalid canonical narrative: {error}",)
    return (
        ()
        if report.content_hash() == expected.content_hash()
        else ("Canonical narrative differs from recomputed registers and review",)
    )
