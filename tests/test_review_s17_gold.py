"""S17 review regressions: financial_gold status/value validation (cr S17 cases.py:334)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.model_testing.cases import CaseError, financial_gold_facts

FIXTURE = Path(__file__).parent / "fixtures" / "model_testing" / "financial_gold_small.json"
CFO = "TDG:CFO:FY2024Q2"  # known, "229" in the fixture
PRINCIPAL = "TDG:principal:FY2024Q2"  # missing, null in the fixture


def _gold(fin_id: str, **change: Any) -> dict[str, Any]:
    gold: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for fact in gold["facts"]:
        if fact.get("fact_id", fact.get("stable_fact_id")) == fin_id:
            fact.update(change)
            return gold
    raise AssertionError(fin_id)


def test_fixture_still_loads_with_its_exact_strings() -> None:
    facts = financial_gold_facts(_gold(CFO))
    assert facts[f"CP-1.fin.{CFO}"]["value"] == "229"
    assert facts[f"CP-1.fin.{PRINCIPAL}"]["value"] is None


@pytest.mark.parametrize(
    ("value", "why"),
    [
        (None, "decimal string"),
        (0.1, "decimal string"),
        (229, "decimal string"),
        (True, "decimal string"),
        ("NaN", "not a finite number"),
        ("Infinity", "not a finite number"),
        ("2 29", "not a finite number"),
    ],
)
def test_known_needs_a_finite_decimal_string(value: Any, why: str) -> None:
    with pytest.raises(CaseError, match=f"{CFO}.*{why}"):
        financial_gold_facts(_gold(CFO, value=value))


def test_missing_must_not_carry_a_value() -> None:
    with pytest.raises(CaseError, match=f"{PRINCIPAL}: a missing fact needs a null value"):
        financial_gold_facts(_gold(PRINCIPAL, value="5"))


def test_unknown_status_refused() -> None:
    with pytest.raises(CaseError, match=f"{CFO}: status 'estimated' is not one of"):
        financial_gold_facts(_gold(CFO, status="estimated"))
