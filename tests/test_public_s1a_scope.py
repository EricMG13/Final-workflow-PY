"""The bounded public TDG S1a delivery route; offline argument and renderer checks."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import PATHWAY_MODULES, Run
from deploy_vii.execution import Execution
from deploy_vii.preparation import load_pack
from deploy_vii.registry import plan
from deploy_workflow import run_pathway as run_pathway_module
from deploy_workflow.model.adapter import RecordedAdapter
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.model_testing.records import read_run
from deploy_workflow.owner_rendering import PUBLIC_DELIVERY_SCOPES, _scope_of
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.replay import ReplayPackChanged, check_same_pack
from deploy_workflow.run_inputs import (
    CaseSource,
    DeliveryScopeRefused,
    check_arguments,
    stage_sources,
)
from deploy_workflow.run_pathway import ResumeMismatch, ResumeRefused, _create_cap
from deploy_workflow.run_scopes import PUBLIC_S1A_MODULES, PUBLIC_S1A_SCOPE

ROOT = Path(__file__).resolve().parents[1]
MODEL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")


@pytest.fixture
def args(tmp_path: Path) -> dict[str, Any]:
    source = tmp_path / "source.txt"
    source.write_text("issuer source\n", encoding="utf-8")
    return {
        "case_id": "tdg-public",
        "sources": [CaseSource("issuer", source, "text/plain")],
        "context": ROOT / "cases/context/research-minimal.json",
        "pathway": "credit_snapshot",
        "model": MODEL,
        "adapter": RecordedAdapter(MODEL, {}),
        "cap_usd": Decimal(1),
        "run_dir": tmp_path / "run",
        "run_id": "tdg-public-s1a",
    }


def _context_copy(tmp_path: Path, *, kind: str | None = None, pathway: str | None = None) -> Path:
    raw = json.loads((ROOT / "cases/context/research-minimal.json").read_text())
    if kind is not None:
        raw["run"]["case_kind"] = kind
    if pathway is not None:
        raw["run"]["pathway"] = pathway
    path = tmp_path / "changed-context.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def _tree_snapshot(root: Path) -> dict[Path, bytes | None]:
    return {
        path.relative_to(root): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def _start_partial_execution(args: dict[str, Any], scope: str | None) -> None:
    checked = check_arguments(**args, **({} if scope is None else {"delivery_scope": scope}))
    stage_sources(checked, args["run_dir"])
    _create_cap(args["run_dir"], args["cap_usd"], "offline")
    pack = load_pack(args["run_dir"] / "pack")
    OwnerWorkflow.create(
        args["run_dir"] / "execution",
        pack,
        publication_directory=args["run_dir"] / "publication",
    )


def _forge_outer_requested_modules(run_dir: Path, requested_modules: tuple[str, ...]) -> None:
    pack_dir = run_dir / "pack"
    pack = load_pack(pack_dir)
    forged = pack.model_copy(
        update={"run": pack.run.model_copy(update={"requested_modules": requested_modules})}
    )
    (pack_dir / "pack.json").write_text(forged.model_dump_json(indent=2) + "\n")
    (pack_dir / "complete.json").write_text(
        json.dumps({"pack_sha256": forged.content_hash()}), encoding="utf-8"
    )


def test_default_keeps_the_existing_preset_request(args: dict[str, Any]) -> None:
    checked = check_arguments(**args)
    assert checked.request.run.requested_modules == PATHWAY_MODULES["credit_snapshot"]
    assert checked.delivery_scope is None
    assert not args["run_dir"].exists()


def test_named_scope_selects_exact_tuple_before_pack_preparation(args: dict[str, Any]) -> None:
    checked = check_arguments(**args, delivery_scope=PUBLIC_S1A_SCOPE)
    assert checked.request.run.requested_modules == PUBLIC_S1A_MODULES
    assert plan(checked.request.run.requested_modules)[0] == "CP-0"
    assert checked.delivery_scope == PUBLIC_S1A_SCOPE
    assert not args["run_dir"].exists()


@pytest.mark.parametrize("scope", ["other", "credit_snapshot", ""])
def test_unknown_scope_refuses_before_writes(args: dict[str, Any], scope: str) -> None:
    with pytest.raises(DeliveryScopeRefused, match="delivery_scope: unknown named scope"):
        check_arguments(**args, delivery_scope=scope)  # type: ignore[arg-type]
    assert not args["run_dir"].exists()


def test_public_scope_refuses_a_synthetic_context_before_writes(
    args: dict[str, Any], tmp_path: Path
) -> None:
    with pytest.raises(DeliveryScopeRefused, match="requires a public case"):
        check_arguments(
            **{**args, "context": _context_copy(tmp_path, kind="synthetic")},
            delivery_scope=PUBLIC_S1A_SCOPE,
        )
    assert not args["run_dir"].exists()


def test_public_scope_refuses_cp_dr_expansion_before_writes(args: dict[str, Any]) -> None:
    with pytest.raises(DeliveryScopeRefused, match="CP-DR is outside"):
        check_arguments(**args, cp_dr=True, delivery_scope=PUBLIC_S1A_SCOPE)
    assert not args["run_dir"].exists()


def test_public_scope_refuses_a_different_pathway_before_writes(
    args: dict[str, Any], tmp_path: Path
) -> None:
    context = _context_copy(tmp_path, pathway="distressed_restructuring")
    with pytest.raises(DeliveryScopeRefused, match="requires the credit_snapshot pathway"):
        check_arguments(
            **{**args, "context": context, "pathway": "distressed_restructuring"},
            delivery_scope=PUBLIC_S1A_SCOPE,
        )
    assert not args["run_dir"].exists()


def test_named_resume_requires_explicit_same_scope_and_pack_tuple(args: dict[str, Any]) -> None:
    named = check_arguments(**args, delivery_scope=PUBLIC_S1A_SCOPE)
    stage_sources(named, args["run_dir"])
    omitted = check_arguments(**args, resume=True)
    with pytest.raises(ResumeMismatch, match="requested modules"):
        run_pathway_module._check_identity(omitted, args["run_dir"], Redactor())
    repeated = check_arguments(**args, resume=True, delivery_scope=PUBLIC_S1A_SCOPE)
    assert repeated.request.run.requested_modules == named.request.run.requested_modules


@pytest.mark.parametrize(
    ("inner_scope", "outer_modules", "invocation_scope"),
    [
        (PUBLIC_S1A_SCOPE, PATHWAY_MODULES["credit_snapshot"], None),
        (None, PUBLIC_S1A_MODULES, PUBLIC_S1A_SCOPE),
    ],
    ids=("forged-outer-default-inner-named", "forged-outer-named-inner-default"),
)
def test_resume_refuses_disagreement_between_outer_and_execution_packs(
    args: dict[str, Any],
    inner_scope: str | None,
    outer_modules: tuple[str, ...],
    invocation_scope: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _start_partial_execution(args, inner_scope)
    _forge_outer_requested_modules(args["run_dir"], outer_modules)
    before = _tree_snapshot(args["run_dir"])
    opened: list[Path] = []
    original_open = OwnerWorkflow.open.__func__

    def observe_open(cls: type[OwnerWorkflow], directory: Path, **kwargs: Any) -> OwnerWorkflow:
        opened.append(directory)
        return original_open(cls, directory, **kwargs)

    monkeypatch.setattr(OwnerWorkflow, "open", classmethod(observe_open))

    kwargs = {} if invocation_scope is None else {"delivery_scope": invocation_scope}
    with pytest.raises(ResumeMismatch, match="retained execution pack"):
        run_pathway_module.run_pathway(**args, resume=True, **kwargs)
    assert _tree_snapshot(args["run_dir"]) == before
    assert not (args["run_dir"] / "calls.jsonl").exists()
    assert not (args["run_dir"] / "run.json").exists()
    assert opened == []


def test_intact_named_packs_pass_resume_identity(args: dict[str, Any]) -> None:
    _start_partial_execution(args, PUBLIC_S1A_SCOPE)
    checked = check_arguments(**args, resume=True, delivery_scope=PUBLIC_S1A_SCOPE)
    run_pathway_module._check_identity(checked, args["run_dir"], Redactor())


@pytest.mark.parametrize(
    "corruption", ["missing", "corrupt"], ids=("missing-inner", "corrupt-inner")
)
def test_unreadable_retained_execution_pack_refuses_before_resume_writes(
    args: dict[str, Any], corruption: str
) -> None:
    _start_partial_execution(args, PUBLIC_S1A_SCOPE)
    execution = Execution(args["run_dir"] / "execution")
    snapshot = execution.read()
    pack_blob = args["run_dir"] / "execution" / "blobs" / snapshot.pack_sha256
    if corruption == "missing":
        pack_blob.unlink()
    else:
        pack_blob.write_bytes(b"corrupt inner prepared pack")
    before = _tree_snapshot(args["run_dir"])
    checked = check_arguments(**args, resume=True, delivery_scope=PUBLIC_S1A_SCOPE)

    with pytest.raises(ResumeRefused, match="retained execution pack is missing or unreadable"):
        run_pathway_module._check_identity(checked, args["run_dir"], Redactor())
    assert _tree_snapshot(args["run_dir"]) == before


def test_public_run_pathway_resume_requires_the_explicit_scope(args: dict[str, Any]) -> None:
    _start_partial_execution(args, PUBLIC_S1A_SCOPE)
    before = {
        path.relative_to(args["run_dir"]): path.read_bytes()
        for path in args["run_dir"].rglob("*")
        if path.is_file()
    }

    with pytest.raises(ResumeMismatch, match="requested modules"):
        run_pathway_module.run_pathway(**args, resume=True)
    assert before == {
        path.relative_to(args["run_dir"]): path.read_bytes()
        for path in args["run_dir"].rglob("*")
        if path.is_file()
    }

    # Repeating the scope passes the full read-only resume identity check. Do not enter the
    # workflow here: the test has no purpose in issuing model calls.
    repeated = check_arguments(**args, resume=True, delivery_scope=PUBLIC_S1A_SCOPE)
    run_pathway_module._check_identity(repeated, args["run_dir"], Redactor())


def test_replay_pack_identity_rejects_an_omitted_scope(args: dict[str, Any]) -> None:
    named = check_arguments(**args, delivery_scope=PUBLIC_S1A_SCOPE)
    stage_sources(named, args["run_dir"])
    default_dir = args["run_dir"].parent / "default-run"
    default = check_arguments(
        **{
            **args,
            "run_id": "tdg-public-default",
            "run_dir": default_dir,
        }
    )
    stage_sources(default, default_dir)
    named_pack = load_pack(args["run_dir"] / "pack")
    default_pack = load_pack(default_dir / "pack")
    with pytest.raises(ReplayPackChanged, match="sources or the run differ"):
        check_same_pack(named_pack, default_pack)


def test_public_renderer_scope_is_distinct_and_exact() -> None:
    assert tuple(PUBLIC_DELIVERY_SCOPES) == (PUBLIC_S1A_SCOPE,)
    run = Run(
        run_id="tdg-public-s1a",
        issuer_id="tdg",
        issuer_name="TD Group",
        as_of=date(2026, 11, 3),
        case_kind="public",
        pathway="credit_snapshot",
        requested_modules=PUBLIC_S1A_MODULES,
    )
    scope = _scope_of(run)
    assert scope.scope_id == PUBLIC_S1A_SCOPE
    assert scope.case_kind == "public"
    assert scope.sections == (
        "key-findings",
        "company-operating-model",
        "strengths-weaknesses",
        "company-profile",
        "transaction-summary",
    )
    assert (
        "Integrity review and remaining analytical owners remain unqualified."
        in scope.banner["complete"]
    )
    synthetic = run.model_copy(update={"case_kind": "synthetic"})
    assert _scope_of(synthetic).scope_id == "s1a-credit-snapshot"


def test_named_run_metadata_is_added_only_for_named_scope(args: dict[str, Any]) -> None:
    outcome = run_pathway_module.run_pathway(**args, delivery_scope=PUBLIC_S1A_SCOPE)
    assert outcome.outcome == "stopped"  # no recording; this checks route metadata, not completion
    metadata = json.loads((args["run_dir"] / "run.json").read_text())
    assert metadata["delivery_scope"] == PUBLIC_S1A_SCOPE
    assert metadata["requested_modules"] == list(PUBLIC_S1A_MODULES)
    run_meta, _ = read_run(args["run_dir"])
    assert run_meta.delivery_scope == PUBLIC_S1A_SCOPE
    assert run_meta.requested_modules == PUBLIC_S1A_MODULES


def test_default_run_metadata_omits_new_scope_fields(args: dict[str, Any]) -> None:
    outcome = run_pathway_module.run_pathway(**args)
    assert outcome.outcome == "stopped"
    metadata = json.loads((args["run_dir"] / "run.json").read_text())
    assert "delivery_scope" not in metadata
    assert "requested_modules" not in metadata
