"""Review S03: the CP-1 journal boundary (retained-payload parse, envelope bytes, QA status).

The workflow runs are the synthetic financial case of `test_financial_workflow` (a deterministic
retained-data case, not a model run). Expected values are literal.
"""

import hashlib
import importlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.cp1_quality import _module_status
from deploy_vii.cp1_workflow import EnvelopeRefused, read_cp1_envelope, write_cp1_envelope
from deploy_vii.execution import Execution
from deploy_vii.narrative import NarrativeReport

fw: Any = importlib.import_module("test_financial_workflow")

AMOUNT = re.compile(r'"amount": "(-?[0-9]+(?:\.[0-9]+)?)"')


def test_financial_stage_keeps_the_printed_digits_of_json_number_amounts(tmp_path: Path) -> None:
    """cp1_workflow.py:126: every amount sent as an unquoted JSON number with a trailing zero
    (45 sent as 45.0) reaches the retained stage output as 45.0, not as the float's 45."""
    workflow, pack = fw.before_financials(tmp_path)
    fw.financial_reads(workflow)
    text = AMOUNT.sub(
        lambda m: '"amount": ' + m.group(1) + ("" if "." in m.group(1) else ".0"),
        json.dumps(fw.financials(pack)),
    )
    assert '"amount": 45.0' in text
    outcome = workflow.submit_review(text)
    assert outcome["status"] == "valid", outcome
    store = Execution(tmp_path / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    output_sha256 = attempt.steps[1].output_sha256
    assert output_sha256 is not None
    output = store.step_output(output_sha256)
    assert '"amount":"45.0"' in output
    assert '"amount":"45"' not in output


@pytest.fixture(scope="module")
def promoted_store(tmp_path_factory: pytest.TempPathFactory) -> Execution:
    root = tmp_path_factory.mktemp("s03-promoted")
    fw.promoted_case(root)
    return Execution(root / "store")


def test_exported_envelope_bytes_are_the_bytes_its_receipt_hashes(
    promoted_store: Execution, tmp_path: Path
) -> None:
    """cp1_workflow.py:582: the files on disk hash exactly as complete.json records."""
    destination = tmp_path / "cp1"
    write_cp1_envelope(promoted_store, destination)
    receipt = json.loads((destination / "complete.json").read_bytes())
    assert set(receipt["files"]) == {"envelope.md", "envelope.json"}
    for name, recorded in receipt["files"].items():
        raw = (destination / name).read_bytes()
        assert b"\r\n" not in raw
        assert hashlib.sha256(raw).hexdigest() == recorded
    assert read_cp1_envelope(promoted_store, destination).module.module_id == "CP-1"


def test_a_crlf_rewritten_envelope_no_longer_matches_its_receipt(
    promoted_store: Execution, tmp_path: Path
) -> None:
    """The reader compares exact bytes: a CRLF copy (what text mode writes on Windows) differs
    from the hashed LF bytes, so it is refused rather than silently read back as LF."""
    destination = tmp_path / "cp1"
    write_cp1_envelope(promoted_store, destination)
    markdown = destination / "envelope.md"
    markdown.write_bytes(markdown.read_bytes().replace(b"\n", b"\r\n"))
    with pytest.raises(EnvelopeRefused) as refused:
        read_cp1_envelope(promoted_store, destination)
    assert refused.value.issues == ("envelope.md differs from the receipt's hash",)


def test_a_candidate_narrative_with_its_fixed_limitations_is_a_complete_module() -> None:
    """cp1_quality.py:69: the four method-scope limitations every narrative carries are not
    findings, so a candidate narrative (no gap) leaves the module complete."""
    fixed = (
        (
            "Structural evidence binding cannot prove issuer-specific meaning, materiality or "
            "reasoning quality"
        ),
        "All numeric evidence is supplied by prior registers; prose still requires semantic review",
        (
            "Funding classification is an analyst synthesis over prior balance-sheet rows, not "
            "new extraction"
        ),
        "No consumer readiness, analytical qualification or completed Module acceptance is inferred",
    )
    candidate = NarrativeReport.model_construct(status="candidate", limitations=fixed, gaps=())
    assert _module_status(candidate) == "complete"
    restricted = candidate.model_copy(update={"status": "restricted"})
    assert _module_status(restricted) == "restricted"
    blocked = candidate.model_copy(update={"status": "blocked"})
    assert _module_status(blocked) == "blocked"
