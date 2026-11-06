"""Review S02 (source context): a blank scope dimension is an unresolved-scope gap, and the
split validator keeps every issue in its documented order."""

import copy
import importlib
import json
from typing import Any

import pytest

from deploy_vii.source_context import SourceContextReview, source_context, validate_source_context

fw = importlib.import_module("test_financial_workflow")

pack = fw.make_pack()
CONTEXT = json.loads(fw.context(pack))


def _review(doc: dict[str, Any]) -> SourceContextReview:
    return SourceContextReview.model_validate_json(json.dumps(doc))


def _forecast_with(field: str, value: str) -> dict[str, Any]:
    doc = copy.deepcopy(CONTEXT)
    scope = doc["sources"][1]["scopes"][1]
    assert scope["scope_id"] == "q1-2025"
    scope["period_kind"] = "forecast"
    scope[field] = value
    return doc


@pytest.mark.parametrize("blank", [" ", "\u200b"])
@pytest.mark.parametrize("field", ["entity_perimeter", "accounting_basis"])
def test_a_blank_forecast_scope_dimension_is_an_unresolved_scope_gap(
    field: str, blank: str
) -> None:
    doc = _forecast_with(field, blank)
    assert validate_source_context(pack, _review(doc)) == ()
    report = source_context(pack, _review(doc))
    assert [(g.reference, g.description) for g in report.gaps if g.category == "scope"] == [
        ("identity", "Source has no located entity/period scope"),
        ("q1-2025", f"Unresolved scope: {field}"),
    ]
    assert report.status == "restricted"


def test_a_stated_forecast_scope_dimension_is_no_gap() -> None:
    doc = _forecast_with("entity_perimeter", "consolidated group")
    report = source_context(pack, _review(doc))
    assert [g.reference for g in report.gaps if g.category == "scope"] == ["identity"]


def test_issue_order_follows_inventory_entities_sources_events() -> None:
    doc = copy.deepcopy(CONTEXT)
    doc["entities"][0]["roles"] = ["issuer", "issuer"]
    financial = doc["sources"][1]
    financial["published_on"] = "2099-01-01"
    financial["event_scan_explanation"] = " "
    financial["scopes"][2]["start_date"] = "2026-01-01"
    doc["events"] = [
        {
            "event_id": "ev-1",
            "reporting_scope_id": "fy-2025",
            "event_date": "2025-06-30",
            "known_on": "2025-07-01",
            "status": "announced",
            "description": "Refinancing announced",
            "effect": "None on reported figures",
            "citations": financial["citations"],
        }
    ]
    doc["limitations"] = [" "]
    issues = validate_source_context(pack, _review(doc))
    assert issues == (
        "Duplicate entity role: issuer",
        "Source publication is after as-of date: financial",
        "Reversed reporting dates: q2-2025",
        "Empty event scan explanation: financial",
        "Event is not after reporting period: ev-1",
        "Subsequent event is absent from source scans: ev-1",
        "Event evidence omitted by source scan: financial ev-1",
        "Empty limitation text: review",
    )
