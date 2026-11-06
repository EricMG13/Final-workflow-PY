"""Review S04: CP-1 narrative projection (`deploy_vii.narrative_projection`).

Synthetic regressions on the statement-quantity fixture book (USD, MILLIONS); expected
dimensions are written by hand from the fixture's statement cells, not from the projection.
"""

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
import test_statement_quantity_outputs as fixtures

from deploy_vii.narrative import EvidencePart, EvidenceRecord, IssuerPart, ProsePart
from deploy_vii.narrative_projection import project_narrative
from deploy_vii.statement_output import StatementCell


def _cells() -> tuple[Any, dict[str, StatementCell]]:
    book = fixtures._book()
    pack, review = fixtures._pack_and_review(book)
    report = fixtures._report(book, pack, review)
    wanted = {"other:is_01", "other:is_18", "other:is_22"}
    cells = {c.item_id: c for c in report.cells if c.period_id == "FY2024" and c.item_id in wanted}
    assert set(cells) == wanted
    return book, cells


def _record(evidence_id: str, cell: StatementCell) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        kind="statement_" + cell.statement,
        reference="cell:" + cell.item_id,
        artifact_sha256="a" * 64,
        record_sha256="b" * 64,
        record_json=cell.model_dump_json(),
        citations=cell.citations,
    )


def _report(records: tuple[EvidenceRecord, ...], findings: tuple[Any, ...] = ()) -> Any:
    rationale = (ProsePart(text="Reviewed."),)
    review = SimpleNamespace(
        findings=findings,
        coverage=(),
        funding=SimpleNamespace(
            status="no_material_items",
            reviewed_statement_ids=tuple(r.evidence_id for r in records),
            material_statement_ids=(),
            rationale=rationale,
        ),
        stories=(),
    )
    inputs = SimpleNamespace(
        catalogue=records,
        scope="data_quality_only",
        ledger=SimpleNamespace(audit=SimpleNamespace(statements=SimpleNamespace(cells=()))),
    )
    return SimpleNamespace(inputs=inputs, review=review, required_story_ids=())


@pytest.mark.parametrize(
    ("item", "unit", "currency", "scale"),
    [
        ("other:is_01", "currency", "USD", Decimal(1000000)),
        ("other:is_18", "USD/share", "USD", Decimal(1)),
        ("other:is_22", "million shares", None, Decimal(1000000)),
    ],
)
def test_evidence_trace_dimensions_come_from_the_statement_cell(
    item: str, unit: str, currency: str | None, scale: Decimal
) -> None:
    book, cells = _cells()
    record = _record("ev-" + item.replace(":", "-"), cells[item])
    projection = project_narrative(book, _report((record,)), "Fixture Issuer Inc.")
    fields = next(
        f for f in projection.facts if f.table_id == "evidence-trace" and f.field == "fields"
    )
    assert (fields.unit, fields.currency, fields.scale) == (unit, currency, scale)
    assert fields.period == "FY2024: 2023-10-01 to 2024-09-30"


def test_an_issuer_name_with_reserved_characters_projects() -> None:
    book, cells = _cells()
    record = _record("ev-revenue", cells["other:is_01"])
    finding = SimpleNamespace(
        finding_id="f-1",
        dimension="data_quality",
        title="Revenue line",
        evidence=(
            IssuerPart(),
            ProsePart(text=" reports revenue "),
            EvidencePart(evidence_id="ev-revenue"),
        ),
        risk_mechanic=(ProsePart(text="A restated line moves leverage."),),
        credit_implication=(ProsePart(text="Leverage reads differently."),),
    )
    projection = project_narrative(book, _report((record,), (finding,)), "Acme [UK] {Holdings} Ltd")
    (claim,) = projection.claims
    assert "Acme (UK) (Holdings) Ltd reports revenue [" in claim.text
