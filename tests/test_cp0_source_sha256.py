"""CP1H-R15: Python fills CP-0's `Citation.source_sha256`; the offered schema cannot carry it."""

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.execution import Execution
from deploy_workflow.owner_workflow import OwnerWorkflow, verify_owner_run_receipt

fw: Any = importlib.import_module("test_financial_workflow")

UNAVAILABLE = "Unavailable or changed source: "
UNREAD = "Cited page not read through read_pages"


def strip(node: Any, key: str) -> None:
    if isinstance(node, dict):
        node.pop(key, None)
        for value in node.values():
            strip(value, key)
    elif isinstance(node, list):
        for value in node:
            strip(value, key)


def start(tmp_path: Path, gap: bool = False) -> tuple[Any, Any]:
    pack = fw.make_pack(gap)
    workflow = OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    fw.read_sources(workflow, gap=gap)
    return workflow, pack


def hashless(pack: Any, gap: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(fw.readiness(pack, gap=gap))
    strip(payload, "source_sha256")
    return payload


def test_a_a_review_without_source_sha256_is_valid(tmp_path: Path) -> None:
    """The live stop: the offered schema drops the field, so no model sends it."""
    workflow, pack = start(tmp_path)
    outcome = workflow.submit_review(json.dumps(hashless(pack)))
    assert outcome["status"] == "valid", outcome["issues"]
    assert outcome["prefilled"]
    assert all(path.endswith("source_sha256") for path in outcome["prefilled"])


def test_b_a_review_holding_the_right_hashes_is_stored_byte_for_byte(tmp_path: Path) -> None:
    workflow, pack = start(tmp_path)
    payload = fw.readiness(pack)
    outcome = workflow.submit_review(payload)
    assert outcome["status"] == "valid", outcome["issues"]
    assert outcome["prefilled"] == []
    assert outcome["stored_payload_sha256"] == hashlib.sha256(payload.encode()).hexdigest()


def cited(pack: Any, source_id: str, locator: str) -> str:
    payload = hashless(pack, gap=True)
    payload["analysis"][0]["citations"].append(
        {"source_id": source_id, "locator": locator, "quote": "x"}
    )
    return json.dumps(payload)


# (source cited, locator, whether the unread-page rule refuses it, whether the new rule does).
# `read_pages` refuses a source that is not ready, so a not-ready source is never read: a page
# locator is caught by the unread-page rule, and only a non-page locator reaches the new one.
CASES = [
    ("nope", "page:1", True, False),  # unknown id, page locator: refused as unread
    ("financial", "page:1", True, False),  # not ready (missing in the gap pack), page locator
    ("nope", "line:1", False, True),  # unknown id, non-page locator: never read-checked
    ("financial", "line:1", False, True),  # not ready, non-page locator
]


@pytest.mark.parametrize("source_id,locator,unread,unavailable", CASES)
def test_c_a_citation_of_a_source_the_pack_cannot_serve_is_refused(
    tmp_path: Path, source_id: str, locator: str, unread: bool, unavailable: bool
) -> None:
    workflow, pack = start(tmp_path, gap=True)
    before = Execution(tmp_path / "store").read().content_hash()
    outcome = workflow.submit_review(cited(pack, source_id, locator))
    assert outcome["status"] == "refused", outcome
    issues = outcome["issues"]
    assert any(i.startswith(UNREAD) for i in issues) is unread, issues
    assert (f"{UNAVAILABLE}{source_id}" in issues) is unavailable, issues
    assert Execution(tmp_path / "store").read().content_hash() == before  # nothing journaled


def test_e_the_verifier_accepts_a_filled_cp0_submission(tmp_path: Path) -> None:
    workflow, pack = start(tmp_path, gap=True)
    outcome = workflow.submit_review(json.dumps(hashless(pack, gap=True)))
    assert outcome["status"] == "valid", outcome["issues"]
    assert workflow.publish()["status"] == "refused"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    (submission,) = receipt.submissions
    assert submission.prefilled
    assert submission.prefilled_kinds == ("source",) * len(submission.prefilled)
    verify_owner_run_receipt(Execution(tmp_path / "store"), receipt, publication_directory=None)
