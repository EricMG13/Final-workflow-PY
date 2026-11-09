"""CP-8 orchestration regressions; synthetic answers are not model proof."""

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow import handoff_delivery
from deploy_workflow.owners import cpos

ROOT = Path(__file__).resolve().parents[1]
PRIOR = (
    ROOT
    / "runs/cpos-tdg-host-001/execution/deliveries/17e1d418be894f6aeff979f100e87460fc3f9d80ed4f22cb7114e4b1c5c8627d"
)
CURRENT = (
    ROOT
    / "runs/cpos-tdg-model-001/execution/deliveries/de1be08fb3a040d4e4f916cce017b1541b8eaaa8235b6fb50b7c4afb916a2bfc"
)
DIMENSIONS = (
    "Values",
    "Periods",
    "Assumptions",
    "Conclusions",
    "Sources",
    "Limitations",
    "Output scope",
)
RESPONSE = (
    "# Synthetic CP-8 infrastructure answer\n\n## Request\nSynthetic regression only.\n\n"
    "## Sources\nPinned test bundles.\n\n## Findings\n\n"
    "| Dimension | Prior deliverable | Current deliverable | Explanation |\n|---|---|---|---|\n"
    + "".join(
        f"| {d} | Synthetic prior observation | Synthetic current observation | Synthetic comparison |\n"
        for d in DIMENSIONS
    )
    + "\n## Calculations\nNone.\n\n## Gaps\nSynthetic only.\n\n## Next module\nDelivery.\n"
).encode()


def pin(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def job(tmp_path: Path, *, copies: bool = False) -> Path:
    prior, current = PRIOR, CURRENT
    if copies:
        prior, current = tmp_path / "prior", tmp_path / "current"
        shutil.copytree(PRIOR, prior)
        shutil.copytree(CURRENT, current)
    instructions = tmp_path / "instructions.md"
    instructions.write_text(
        "Compare prior/current deliverables across seven dimensions; no decision history."
    )
    data = {
        "run": {
            "run_id": "comparison-test",
            "issuer_id": "TDG",
            "issuer_name": "TransDigm Group Incorporated",
            "as_of": "2024-09-30",
            "case_kind": "public",
            "pathway": "credit_snapshot",
            "requested_modules": ["CP-8"],
        },
        "prior": pin(prior / "delivery.json"),
        "current": pin(current / "delivery.json"),
        "instructions": pin(instructions),
        "execution": "synthetic",
        "provider_cap_usd": 0,
    }
    path = tmp_path / "comparison.json"
    path.write_text(json.dumps(data))
    return path


def check(task, raw):
    return () if raw == RESPONSE else ("Synthetic response bytes differ.",)


def refresh_receipt(path: Path) -> None:
    data = json.loads(path.read_bytes())
    receipt = Path(data["current"]["path"])
    content = json.loads(receipt.read_bytes())
    for name in content["files"]:
        content["files"][name] = hashlib.sha256((receipt.parent / name).read_bytes()).hexdigest()
    receipt.write_text(json.dumps(content))
    data["current"] = pin(receipt)
    path.write_text(json.dumps(data))


def test_only_cp8_receives_complete_deliverables_then_publication_and_resume(tmp_path: Path):
    path = job(tmp_path)
    seen = []

    def execute(task):
        seen.append(task.module_id)
        assert not task.handoffs
        assert {k.split("/", 1)[0] for k in task.sources} == {"prior", "current"}
        assert task.sources["prior/report.html"] == (PRIOR / "report.html").read_bytes()
        assert task.sources["current/model.html"] == (CURRENT / "model.html").read_bytes()
        with pytest.raises(TypeError):
            task.sources["current/report.html"] = b"changed"
        return RESPONSE

    report = cpos.run_comparison(path, tmp_path / "state", execute=execute, check=check)
    assert seen == ["CP-8"]
    view = json.loads((report.parent / "report-view.json").read_bytes())
    assert [r["label"] for r in view["blocks"][0]["rows"]] == list(DIMENSIONS)
    assert (report.parent / "CP-8.md").read_bytes() == RESPONSE
    assert len(list((tmp_path / "state").glob("completed-*.json"))) == 1
    assert not list(report.parent.glob("*.xlsx"))

    def no_execute(task):
        pytest.fail("Resume repeated CP-8")

    assert cpos.run_comparison(path, tmp_path / "state", execute=no_execute, check=check) == report


@pytest.mark.parametrize(
    "fault", ["receipt", "file", "unlisted", "unsafe", "issuer", "as_of", "mode"]
)
def test_bad_comparison_inputs_refuse_before_dispatch(tmp_path: Path, fault: str):
    path = job(tmp_path, copies=True)
    data = json.loads(path.read_bytes())
    current = Path(data["current"]["path"]).parent
    if fault == "receipt":
        (current / "delivery.json").write_bytes(b"changed")
    elif fault == "file":
        (current / "CP-2.md").write_bytes(b"changed")
    elif fault == "unlisted":
        (current / "extra.md").write_bytes(b"unlisted")
    elif fault == "unsafe":
        receipt = json.loads((current / "delivery.json").read_bytes())
        receipt["files"]["../escape"] = "0" * 64
        (current / "delivery.json").write_text(json.dumps(receipt))
        data["current"] = pin(current / "delivery.json")
    elif fault == "issuer":
        data["run"]["issuer_id"] = "OTHER"
    elif fault == "as_of":
        data["run"]["as_of"] = "2025-09-30"
    else:
        data["execution"] = "paid-provider"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        cpos.run_comparison(
            path, tmp_path / "state", execute=lambda t: pytest.fail("dispatched"), check=check
        )
    assert not (tmp_path / "state").exists()


def test_same_delivery_as_prior_and_current_refuses_before_dispatch(tmp_path: Path):
    # S01-A03: before the fix the same delivery.json pinned as prior and current published a
    # "checked" self-comparison. A copy of it elsewhere has the same receipt bytes, so it is the
    # same delivery too. Expected, by hand: cp8_same_delivery, no dispatch, no state written.
    path = job(tmp_path, copies=True)
    data = json.loads(path.read_bytes())
    data["prior"] = pin(tmp_path / "current" / "delivery.json")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cp8_same_delivery"):
        cpos.run_comparison(
            path, tmp_path / "state", execute=lambda t: pytest.fail("dispatched"), check=check
        )
    assert not (tmp_path / "state").exists()


def test_prior_delivery_dated_after_the_current_one_refuses_before_dispatch(tmp_path: Path):
    # S01-A03: the prior bundle's View is re-dated 2025-03-31 (re-rendered and re-pinned, so it
    # is a consistent bundle), after the current bundle's 2024-09-30. Expected, by hand:
    # cp8_order, no dispatch, no state written.
    from datetime import date

    from deploy_vii.contracts import View
    from deploy_vii.render import render
    from deploy_vii.report_view import ReportView

    path = job(tmp_path, copies=True)
    folder = tmp_path / "prior"
    view = View.model_validate_json((folder / "view.json").read_bytes())
    later = {"as_of": date(2025, 3, 31)}
    view = view.model_copy(update={"run": view.run.model_copy(update=later)})
    report = ReportView.model_validate_json((folder / "report-view.json").read_bytes())
    (folder / "view.json").write_text(view.model_dump_json(indent=2))
    (folder / "report.html").write_text(render(view, report))
    receipt = json.loads((folder / "delivery.json").read_bytes())
    for name in receipt["files"]:
        receipt["files"][name] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
    (folder / "delivery.json").write_text(json.dumps(receipt))
    data = json.loads(path.read_bytes())
    data["prior"] = pin(folder / "delivery.json")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cp8_order"):
        cpos.run_comparison(
            path, tmp_path / "state", execute=lambda t: pytest.fail("dispatched"), check=check
        )
    assert not (tmp_path / "state").exists()


def test_forged_receipt_does_not_bind_foreign_html_to_views(tmp_path: Path):
    path = job(tmp_path, copies=True)
    (tmp_path / "current/report.html").write_bytes((PRIOR / "report.html").read_bytes())
    refresh_receipt(path)
    with pytest.raises(ValueError, match="cp8_bundle_binding"):
        cpos.run_comparison(path, tmp_path / "state", execute=lambda t: RESPONSE, check=check)


def test_declared_model_cannot_silently_omit_its_html(tmp_path: Path):
    path = job(tmp_path, copies=True)
    receipt_path = tmp_path / "current/delivery.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["cp_model_published"] is True
    del receipt["files"]["model.html"]
    receipt_path.write_text(json.dumps(receipt))
    (tmp_path / "current/model.html").unlink()
    refresh_receipt(path)
    with pytest.raises(ValueError, match="cp8_bundle_files"):
        cpos.run_comparison(path, tmp_path / "state", execute=lambda t: RESPONSE, check=check)


def test_foreign_model_cannot_be_attached_to_current_issuer_bundle(tmp_path: Path):
    from deploy_vii.contracts import View
    from deploy_vii.render import render
    from deploy_vii.report_view import ReportView

    path = job(tmp_path, copies=True)
    folder = tmp_path / "current"
    model = View.model_validate_json((folder / "model-view.json").read_bytes())
    model = model.model_copy(update={"run": model.run.model_copy(update={"issuer_id": "OTHER"})})
    report = ReportView.model_validate_json((folder / "model-report-view.json").read_bytes())
    (folder / "model-view.json").write_text(model.model_dump_json(indent=2))
    (folder / "model.html").write_text(render(model, report))
    refresh_receipt(path)
    with pytest.raises(ValueError, match="cp8_bundle_binding"):
        cpos.run_comparison(path, tmp_path / "state", execute=lambda t: RESPONSE, check=check)


def test_feedback_retry_and_failed_answer_never_reaches_delivery(tmp_path: Path):
    path = job(tmp_path)
    attempts = []

    def execute(task):
        attempts.append(task.attempt)
        if task.attempt == 1:
            assert not task.feedback
            return RESPONSE + b"\nObserved incorrect comparison.\n"
        assert task.feedback == ("Synthetic response bytes differ.",)
        return RESPONSE

    report = cpos.run_comparison(path, tmp_path / "state", execute=execute, check=check)
    assert attempts == [1, 2] and report.exists()
    assert len(list((tmp_path / "state").rglob("*.response.md"))) == 2


def test_missing_dimension_gets_targeted_bounded_feedback(tmp_path: Path):
    path = job(tmp_path)
    called = []

    def execute(task):
        called.append(task.attempt)
        if task.attempt == 1:
            return RESPONSE.replace(b"| Values |", b"| Periods |")
        assert len(task.feedback) == 1 and task.feedback[0].startswith("cp8_dimensions:")
        return RESPONSE

    assert cpos.run_comparison(path, tmp_path / "state", execute=execute, check=check).is_file()
    assert called == [1, 2]


def test_empty_duplicate_or_unexplained_dimension_cannot_publish(tmp_path: Path):
    path = job(tmp_path)
    run = cpos.ComparisonPlan.model_validate_json(path.read_bytes()).run
    for response in (
        RESPONSE.replace(b"| Values |", b"| Periods |"),
        RESPONSE.replace(b"| Synthetic prior observation |", b"|  |", 1),
        RESPONSE.replace(
            b"| Output scope | Synthetic prior observation | Synthetic current observation | Synthetic comparison |\n",
            b"",
        ),
    ):
        with pytest.raises(ValueError, match="cp8_dimensions"):
            handoff_delivery.comparison_files(run, response, {})


def test_partial_publication_does_not_complete_and_resume_needs_no_analysis(
    tmp_path: Path, monkeypatch
):
    path = job(tmp_path)
    original = cpos._put

    def interrupted(destination, raw):
        if "pending-deliveries" in destination.parts and destination.name == "report-view.json":
            raise OSError("interrupted publication")
        return original(destination, raw)

    monkeypatch.setattr(cpos, "_put", interrupted)
    with pytest.raises(OSError, match="interrupted publication"):
        cpos.run_comparison(path, tmp_path / "state", execute=lambda t: RESPONSE, check=check)
    assert not list((tmp_path / "state").glob("completed-*.json"))
    monkeypatch.setattr(cpos, "_put", original)
    report = cpos.run_comparison(
        path, tmp_path / "state", execute=lambda t: pytest.fail("repeated"), check=check
    )
    (report.parent / "CP-8.md").write_bytes(b"forged")
    with pytest.raises(ValueError, match="delivery_changed"):
        cpos.run_comparison(
            path, tmp_path / "state", execute=lambda t: pytest.fail("repeated"), check=check
        )


def test_dispatched_missing_response_never_repeats_automatically(tmp_path: Path):
    path = job(tmp_path)

    def interrupted(task):
        raise OSError("interrupted model exchange")

    with pytest.raises(OSError):
        cpos.run_comparison(path, tmp_path / "state", execute=interrupted, check=check)
    with pytest.raises(ValueError, match="cpos_interrupted"):
        cpos.run_comparison(
            path, tmp_path / "state", execute=lambda t: pytest.fail("repeated"), check=check
        )


@pytest.mark.parametrize(
    "mode,cap,attempts",
    [("live-provider", "0", 1), ("live-provider", "1", 2), ("synthetic", "1", 1)],
)
def test_comparison_execution_budget_refuses_invalid_combinations(tmp_path, mode, cap, attempts):
    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution=mode, provider_cap_usd=cap, max_attempts=attempts)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        cpos.run_comparison(
            path, tmp_path / "state", execute=lambda t: pytest.fail("dispatched"), check=check
        )
    assert not (tmp_path / "state").exists()


def test_live_comparison_repairs_dimensions_inside_loop_and_resumes(tmp_path, monkeypatch):
    """Fake transport checks wiring; retained real provider proof is separate."""
    from deploy_workflow.model.adapter import AdapterReply, LiveAdapter
    from deploy_workflow.model.turn import ToolCall, Turn, Usage

    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution="live-provider", provider_cap_usd="10", max_attempts=1)
    path.write_text(json.dumps(data))
    seen = []

    def complete(self, request, **kwargs):
        context = json.loads(request.messages[1].text)
        assert context["module_id"] == "CP-8" and not context["handoffs"]
        assert "current/model.html" in context["sources"]
        seen.append(request)
        response = RESPONSE
        if len(seen) == 1:
            response = response.replace(b"| Values |", b"| Periods |")
        else:
            assert any("cp8_dimensions:" in m.text for m in request.messages)
        answer = Turn(
            "",
            (ToolCall(str(len(seen)), "write_handoff", {"markdown": response.decode()}),),
            Usage(input_tokens=100, output_tokens=50),
            "tool_use",
            "gpt-6.1-sol",
            "fake",
            200,
        )
        return AdapterReply("ok", answer, None, 200, None, None, 1, 2, answer.usage)

    monkeypatch.setattr(LiveAdapter, "complete", complete)
    state = tmp_path / "state"
    kwargs = {
        "ruling": ROOT / "docs/rulings/2026-11-05-remaining-modules.md",
        "check": check,
        "environ": {},
    }
    report = cpos.run_live_comparison(path, state, **kwargs)
    assert len(seen) == 2 and (report.parent / "CP-8.md").read_bytes() == RESPONSE
    assert cpos.run_live_comparison(path, state, **kwargs) == report
    assert len(seen) == 2
    (completion,) = state.glob("completed-*.json")
    record = json.loads(completion.read_bytes())
    assert record["execution"] == "live-provider" and record["provider_cap_usd"] == "10"
    assert len(list(state.glob("requests/CP-8/*/1.response.md"))) == 1


@pytest.mark.parametrize("fault", ["callback", "mode", "cap", "state", "checker"])
def test_live_comparison_executor_binding_cannot_be_forged(tmp_path, fault):
    from decimal import Decimal

    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.model.handoff import HandoffExecutor
    from deploy_workflow.model.turn import ModelSpec

    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution="live-provider", provider_cap_usd="10", max_attempts=1)
    if fault == "mode":
        data.update(execution="host-session", provider_cap_usd=0)
    path.write_text(json.dumps(data))
    state = tmp_path / "state"
    adapter = LiveAdapter(
        ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium"),
        ROOT / "docs/rulings/2026-11-05-remaining-modules.md",
        environ={},
    )
    executor = HandoffExecutor(
        (tmp_path / "other" if fault == "state" else state) / "live",
        adapter=adapter,
        cap_usd=Decimal(9 if fault == "cap" else 10),
        check=(lambda *_: ()) if fault == "checker" else check,
    )
    with pytest.raises(ValueError, match="cpos_(execution_mode|live_binding):"):
        cpos.run_comparison(
            path,
            state,
            execute=(lambda _: pytest.fail("dispatched")) if fault == "callback" else executor,
            check=check,
        )
    assert not (state / "identity.json").exists()


def test_nonlive_comparison_preserves_legacy_zero_identity(tmp_path):
    path = job(tmp_path)
    state = tmp_path / "state"
    state.mkdir()
    legacy = json.loads(path.read_bytes())
    for key in ("prior", "current", "instructions"):
        del legacy[key]
    legacy["run"] = cpos.Run.model_validate_json(json.dumps(legacy["run"])).model_dump(mode="json")
    legacy["max_attempts"] = 2
    (state / "identity.json").write_text(json.dumps(legacy, sort_keys=True))
    assert cpos.run_comparison(path, state, execute=lambda _: RESPONSE, check=check).is_file()


def test_cli_comparison_replay_requires_explicit_mode_and_pinned_answer(
    tmp_path: Path, monkeypatch, capsys
):
    path = job(tmp_path)
    response = tmp_path / "answer.md"
    response.write_bytes(RESPONSE)
    responses = tmp_path / "responses.json"
    responses.write_text(json.dumps({"CP-8": pin(response)}))
    state = tmp_path / "state"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cpos",
            "--compare",
            "--manifest",
            str(path),
            "--state",
            str(state),
            "--replay-responses",
            str(responses),
        ],
    )
    with pytest.raises(ValueError, match="cp8_replay"):
        cpos.main()
    assert not state.exists()
    data = json.loads(path.read_bytes())
    data["execution"] = "retained-response-replay"
    path.write_text(json.dumps(data))
    cpos.main()
    assert Path(capsys.readouterr().out.strip()).is_file()
    (completion,) = state.glob("completed-*.json")
    assert json.loads(completion.read_bytes())["execution"] == "retained-response-replay"


def test_comparison_pair_rules_by_hand() -> None:
    """Review of S01-A03. Expected, by hand: two different deliveries dated the same day or prior
    earlier pass; the same receipt hash is cp8_same_delivery; a prior dated after the current is
    cp8_order; a foreign issuer is cp8_issuer before either; a current date other than the
    requested one is cp8_as_of."""
    from datetime import date
    from types import SimpleNamespace as NS

    def view(as_of: date, issuer: str = "tdg") -> Any:
        return NS(run=NS(issuer_id=issuer, issuer_name="TDG", as_of=as_of))

    def plan(prior: str, current: str) -> Any:
        return NS(
            run=NS(issuer_id="tdg", issuer_name="TDG", as_of=date(2024, 9, 30)),
            prior=NS(sha256=prior),
            current=NS(sha256=current),
        )

    day, earlier, later = date(2024, 9, 30), date(2024, 6, 30), date(2025, 3, 31)
    check_pair = cpos._check_comparison_pair
    assert check_pair(plan("a", "b"), view(day), view(day)) is None
    assert check_pair(plan("a", "b"), view(earlier), view(day)) is None
    with pytest.raises(ValueError, match="cp8_same_delivery"):
        check_pair(plan("a", "a"), view(day), view(day))
    with pytest.raises(ValueError, match="cp8_order"):
        check_pair(plan("a", "b"), view(later), view(day))
    with pytest.raises(ValueError, match="cp8_issuer"):
        check_pair(plan("a", "a"), view(day, "other"), view(day))
    with pytest.raises(ValueError, match="cp8_as_of"):
        check_pair(plan("a", "b"), view(earlier), view(earlier))
