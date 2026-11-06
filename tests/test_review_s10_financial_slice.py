"""S10 review: audit records stay sealable across failures. Causal component probes over the
independent quarter-only financial case (genuine API states, patched failures); not participant
or model evidence."""

from __future__ import annotations

import importlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.execution import Execution
from deploy_workflow import financial_workflow as fin
from deploy_workflow import owner_workflow as owner
from deploy_workflow.workflow import WorkflowError

fw: Any = importlib.import_module("test_financial_workflow")
AUDIT = "financial-slice-audit"


@pytest.fixture(scope="module")
def quality_case(tmp_path_factory: pytest.TempPathFactory) -> Any:
    return fw.quality_ready_case(tmp_path_factory.mktemp("s10-quality"))


@pytest.fixture(scope="module")
def promoted(quality_case: Any, tmp_path_factory: pytest.TempPathFactory) -> Any:
    template, review, _ = quality_case
    workflow = fw.clone_workflow(template, tmp_path_factory.mktemp("s10-promoted"))
    assert workflow.submit_review(json.dumps(deepcopy(review)))["status"] == "valid"
    return workflow


def _names(root: Path, kind: str) -> set[str]:
    folder = root / "store" / AUDIT / kind
    return {p.name for p in folder.iterdir()} if folder.is_dir() else set()


def test_a_submit_that_raises_before_journaling_leaves_no_binding(
    quality_case: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    template, review, _ = quality_case
    workflow = fw.clone_workflow(template, tmp_path)
    before = _names(tmp_path, "bindings")

    def unknown_kind(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("probe: unknown marked kind")

    with monkeypatch.context() as patch:
        patch.setattr(fin, "_filled", unknown_kind)
        with pytest.raises(ValueError, match="^probe: unknown marked kind$"):
            workflow.submit_review(json.dumps(deepcopy(review)))
    assert _names(tmp_path, "bindings") == before
    assert workflow.submit_review(json.dumps(deepcopy(review)))["status"] == "valid"
    # `_verify`'s rule: the bindings collection is exactly the submissions' bindings.
    assert _names(tmp_path, "bindings") == {s.binding.content_hash() for s in workflow._submissions}


def test_write_receipt_writes_the_receipt_before_the_seal(tmp_path: Path) -> None:
    """At a refused CP-1 (the sealable negative outcome, no Model to publish)."""
    workflow, pack = fw.start(tmp_path, gap=True)
    fw.read_sources(workflow, gap=True)
    assert workflow.submit_review(fw.readiness(pack, gap=True))["refusal"] == "cp1_not_authorized"
    assert workflow.publish_model()["error_code"] == "cp1_not_authorized"
    (tmp_path / "receipt.json").write_bytes(b"another run's receipt")
    with pytest.raises(WorkflowError) as caught:
        workflow.write_receipt(tmp_path / "receipt.json")
    assert caught.value.code == "identity_mismatch"
    assert not (tmp_path / "store" / AUDIT / "receipt.sha256").exists()
    (tmp_path / "receipt.json").unlink()
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    fin.verify_financial_slice_receipt(Execution(tmp_path / "store"), receipt, model_directory=None)


def _failing_publisher(store: Any, *, output: Path) -> Any:
    raise OSError("probe: the output's parent cannot be created")


def test_a_refusal_the_verifier_rejects_ends_publication(
    promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Otherwise a retry would publish a Model that no receipt can bind."""
    workflow = fw.clone_workflow(promoted, tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(fin, "publish_cp_model", _failing_publisher)
        assert workflow.publish_model()["status"] == "refused"
    with pytest.raises(WorkflowError) as caught:
        workflow.publish_model()
    assert caught.value.code == "not_permitted"
    assert not (tmp_path / "model").exists()
    with pytest.raises(WorkflowError) as caught:
        workflow.write_receipt(tmp_path / "receipt.json")
    assert caught.value.code == "not_permitted"


def test_an_existing_output_refusal_stays_retryable(promoted: Any, tmp_path: Path) -> None:
    """The one refusal `_verify` accepts before a publication keeps the run publishable."""
    workflow = fw.clone_workflow(promoted, tmp_path)
    (tmp_path / "model").mkdir()
    refused = workflow.publish_model()
    assert refused["status"] == "refused"
    assert workflow._publications[-1].reason == (
        f"Output {tmp_path / 'model'} already exists; publish into a new directory"
    )
    assert workflow._phase == "promoted"


def test_a_failure_at_a_refused_cp1_ends_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verifier accepts exactly one publication at a refused CP-1: the publisher's refusal."""
    workflow, pack = fw.start(tmp_path, gap=True)
    fw.read_sources(workflow, gap=True)
    assert workflow.submit_review(fw.readiness(pack, gap=True))["refusal"] == "cp1_not_authorized"
    with monkeypatch.context() as patch:
        patch.setattr(fin, "publish_cp_model", _failing_publisher)
        assert workflow.publish_model()["status"] == "refused"
    with pytest.raises(WorkflowError) as caught:
        workflow.publish_model()
    assert caught.value.code == "not_permitted"


@pytest.mark.parametrize("workflow_kind", ["financial", "owner"])
def test_an_output_directory_that_contains_the_store_is_refused(
    workflow_kind: str, tmp_path: Path
) -> None:
    """Creating the store would create the output, so publication could never succeed."""
    output, store = tmp_path / "out", tmp_path / "out" / "run"
    with pytest.raises(WorkflowError) as caught:
        if workflow_kind == "financial":
            fin.FinancialWorkflow.create(store, fw.make_pack(), model_directory=output)
        else:
            owner.OwnerWorkflow.create(store, fw.make_pack(), publication_directory=output)
    assert caught.value.code == "not_permitted"
    assert not output.exists()


def test_an_owner_fill_that_raises_leaves_no_stray_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stray binding with no journal step is torn audit at `open()`; none is written now."""
    pack = fw.make_pack()
    workflow = owner.OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    fw.read_sources(workflow)

    def unknown_kind(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("probe: unknown marked kind")

    monkeypatch.setattr(owner, "_fill", unknown_kind)
    with pytest.raises(ValueError, match="^probe: unknown marked kind$"):
        workflow.submit_review(fw.readiness(pack))
    assert not (tmp_path / "store" / owner.AUDIT / "bindings").exists()
    monkeypatch.undo()
    del workflow
    resumed = owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert resumed.submit_review(fw.readiness(pack))["status"] == "valid"
