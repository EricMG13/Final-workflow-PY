"""Review S04: CP-1 narrative review validation (`deploy_vii.narrative`).

Synthetic workflow fixture (`test_financial_workflow`): the model-side narrative review is the
fixture's own literal with one coverage entry removed.
"""

import json
from pathlib import Path

import test_financial_workflow as fixture


def test_a_dimension_with_findings_needs_its_coverage_entry(tmp_path: Path) -> None:
    workflow, pack = fixture.before_financials(tmp_path)
    fixture.financial_reads(workflow)
    outcome = workflow.submit_review(json.dumps(fixture.financials(pack)))
    assert outcome["status"] == "valid", outcome
    literal = fixture.narrative(workflow.read_inputs())
    literal["coverage"] = [c for c in literal["coverage"] if c["dimension"] != "leverage"]
    assert any(f["dimension"] == "leverage" for f in literal["findings"])
    outcome = workflow.submit_review(json.dumps(literal))
    assert outcome["status"] == "invalid", outcome
    assert "Dimension findings lack coverage: leverage" in json.dumps(outcome)
