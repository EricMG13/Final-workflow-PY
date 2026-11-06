"""Review S12 (CP-2A): shocks admit ASCII digits only, and scenario names and threshold labels
that differ only by surrounding spaces are duplicates."""

import copy
import json
from typing import Any

import pytest
import test_method_cp2a as stage1
from pydantic import ValidationError

from deploy_vii.readiness import shape_issues
from deploy_workflow.owners import cp2a


def _payload() -> tuple[Any, Any]:
    facts = stage1.cp1_facts("positive")
    payload = stage1.bind_payload(
        stage1.SUBMISSIONS["positive"]["downside_pathway"], stage1.fig_ids(facts)
    )
    return copy.deepcopy(payload), facts


@pytest.mark.parametrize("field", ["ebitda_decline", "interest_increase"])
@pytest.mark.parametrize("text", ["0.٢٥", "0.１", "１", "0.\U0001d7d0"])
def test_shock_with_non_ascii_digits_is_a_shape_issue(field: str, text: str) -> None:
    payload, _ = _payload()
    payload["scenarios"][0][field] = text
    with pytest.raises(ValidationError) as error:
        cp2a.DownsideSubmission.model_validate_json(json.dumps(payload))
    # The same issue text as any other shock the pinned pattern refuses (oracle `v` refusals).
    assert list(shape_issues(error.value)) == [
        f"scenarios.0.{field}: String should match pattern '^(0|1|0\\.\\d{{1,4}}|1\\.0{{1,4}})$'"
    ]


def test_ascii_shock_still_composes() -> None:
    payload, facts = _payload()
    payload["scenarios"][0]["ebitda_decline"] = "0.25"
    assert cp2a.validate(stage1.inputs_for("positive", payload, facts)) == ()


def test_scenario_names_equal_after_strip_are_duplicates() -> None:
    payload, facts = _payload()
    payload["scenarios"][1]["name"] = payload["scenarios"][0]["name"] + " "
    issues = cp2a.validate(stage1.inputs_for("positive", payload, facts))
    assert issues == ("scenarios[1].name: duplicate scenario name: Moderate downturn ",)


def test_threshold_labels_equal_after_strip_are_duplicates() -> None:
    payload, facts = _payload()
    payload["thresholds"][1]["label"] = " " + payload["thresholds"][0]["label"]
    issues = cp2a.validate(stage1.inputs_for("positive", payload, facts))
    assert issues == ("thresholds: Total leverage watch level appears more than once",)
