"""Unavailable values carry no readiness tag (S15 A02).

`_evidence_tags` decides which dependency groups a cited catalogue line can satisfy. Before the
fix only kpi, statement_* and observation lines with a null amount lost their tags, so a
`computation` with operation "unavailable" (amount null) still met `calculation_register` and
the computation group of `fcf_build`. The rows here are written by hand in each kind's shape.
"""

import json

import pytest

from deploy_vii.downstream_readiness import _EVIDENCE_GROUPS, _evidence_tags
from deploy_vii.narrative import EvidenceRecord

H = "0" * 64


def _value(amount: str | None) -> dict[str, object]:
    return {
        "amount": amount,
        "stated_amount": amount,
        "value_class": "calculated",
        "calculation_status": "Calculated" if amount is not None else "Not Available",
        "reason": None if amount is not None else "missing input",
        "note": None,
        "observation_ids": [],
        "issuance_facility_ids": [],
        "citations": [],
    }


def _record(kind: str, amount: str | None) -> EvidenceRecord:
    rows: dict[str, dict[str, object]] = {
        "computation": {"computation_id": "c1", "operation": "unavailable", "operands": []},
        "historical_value": {"value_id": "h1", "construction_id": "k1", "series_key": "revenue"},
        "canonical_value": {"value_id": "v1", "basis_id": "b1", "key": "revenue"},
        "kpi": {"calculation_id": "f1", "key": "fcf"},
    }
    data = {**rows[kind], "value": _value(amount)}
    return EvidenceRecord(
        evidence_id="e1",
        kind=kind,
        reference="r",
        artifact_sha256=H,
        record_sha256=H,
        record_json=json.dumps(data),
        citations=(),
    )


@pytest.mark.parametrize("kind", ["computation", "historical_value", "canonical_value", "kpi"])
def test_a_null_amount_has_no_tag(kind: str) -> None:
    assert _evidence_tags(_record(kind, None)) == set()


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("computation", {"computation"}),
        ("historical_value", {"historical_value"}),
        ("canonical_value", {"canonical_value"}),
        ("kpi", {"kpi", "kpi:fcf"}),
    ],
)
def test_a_zero_amount_is_available_and_keeps_its_tags(kind: str, expected: set[str]) -> None:
    # zero is a value, not a missing one: it keeps the kind tag (and kpi:<key> for a kpi)
    assert _evidence_tags(_record(kind, "0")) == expected


def test_an_unavailable_computation_no_longer_meets_the_calculation_register() -> None:
    tags = _evidence_tags(_record("computation", None))
    (group,) = _EVIDENCE_GROUPS["calculation_register"]
    assert tags.isdisjoint(group)
    # fcf_build needs kpi:fcf and computation: an available FCF KPI with an unavailable
    # computation leaves the computation group unmet
    both = _evidence_tags(_record("kpi", "12.5")) | tags
    assert any(both.isdisjoint(g) for g in _EVIDENCE_GROUPS["fcf_build"])
