"""CP-OS infrastructure regressions using retained answers, not new model proof."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.handoff_delivery import verify_delivery
from deploy_workflow.owners.cpos import HandoffTask, replay_handoffs, run_handoffs
from deploy_workflow.run_pathway import RunDirBusy, _single_writer

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["CP-0", "CP-1", "CP-1A", "CP-2"]
RESPONSES = {
    "CP-0": (ROOT / "runs/tdg-001/CP-0.md").read_bytes(),
    "CP-1": (ROOT / "runs/tdg-002/CP-1-attempt-2.md").read_bytes(),
    # Layout delivery needs each handoff title or Request to name the issuer; the retained CP-1A
    # does not, so this synthetic infrastructure test uses it with the issuer added to its title.
    "CP-1A": (ROOT / "runs/tdg-002/CP-1A-attempt-3.md")
    .read_bytes()
    .replace(b"# CP-1A \xe2\x80\x94 ", b"# CP-1A TransDigm Group Incorporated \xe2\x80\x94 ", 1),
    "CP-2": (ROOT / "runs/tdg-002/CP-2-attempt-2.md").read_bytes(),
}


def test_explicit_repair_draft_participates_in_resume_identity(tmp_path):
    from dataclasses import replace

    from deploy_workflow.owners.cpos import HandoffPlan, _handoff

    run = HandoffPlan.model_validate_json(job(tmp_path).read_bytes()).run
    task = HandoffTask(run, "CP-0", b"repair", {}, {}, 1, (), b"first")
    seen = []

    def execute(current):
        seen.append(current.draft)
        return RESPONSES["CP-0"]

    for draft in (b"first", b"second", b"second"):
        _handoff(replace(task, draft=draft), tmp_path / "state", execute, checked, 1)
    assert seen == [b"first", b"second"]


def test_campaign_recipient_check_uses_role_not_label_separator():
    """Reproduce the live CP-2 false rejection without another provider call."""
    import re
    import runpy

    from deploy_vii.contracts import Run

    case = ROOT / "runs/cpos-sol-medium-20261105"
    campaign = runpy.run_path(str(case / "run.py"))
    inputs = campaign["inputs"]
    current = HandoffTask(
        Run.model_validate_json(json.dumps(inputs["run"])),
        "CP-2",
        b"",
        {},
        {m: (case / inputs["handoffs"].get(m, m + ".md")).read_bytes() for m in ("CP-1", "CP-1A")},
        1,
        (),
    )
    raw = (case / "CP-2-v2.md").read_text()
    for separator in (" / role", " — role", ""):
        variant = re.sub(
            r"^\| (CP-3C|CP-4|CP-6) /[^|]+", r"| \1" + separator + " ", raw, flags=re.MULTILINE
        )
        # Keep role text in the next cell, as the actual fresh answer does.
        for m, role in {
            "CP-3C": "Refinancing",
            "CP-4": "Legal and covenant",
            "CP-6": "Committee debate and challenge",
        }.items():
            variant = variant.replace(
                "| " + m + separator + " |", "| " + m + separator + " | " + role + ":", 1
            )
        assert not campaign["check"](current, variant.encode())
    bad = re.sub(
        r"^\| CP-4[^\n]+",
        "| CP-4 | Portfolio monitoring | No legal role supplied |",
        variant,
        flags=re.MULTILINE,
    )
    assert any("CP-4" in x for x in campaign["check"](current, bad.encode()))


def test_explicit_live_loop_drives_existing_planner_delivery_and_resume(tmp_path, monkeypatch):
    """Fake transport proves wiring only; this is not a provider/module proof."""
    from decimal import Decimal

    from deploy_workflow.model.adapter import AdapterReply, LiveAdapter
    from deploy_workflow.model.handoff import HandoffExecutor
    from deploy_workflow.model.turn import ModelSpec, ToolCall, Turn, Usage

    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution="live-provider", provider_cap_usd="10", max_attempts=1)
    with_live_layout(data)
    path.write_text(json.dumps(data))
    adapter = LiveAdapter(
        ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium"),
        ROOT / "docs/rulings/2026-11-05-live-loop-tests.md",
        environ={},
    )
    seen = []

    def complete(request, **kwargs):
        context = json.loads(request.messages[1].text)
        module = context["module_id"]
        assert list(context["handoffs"]) == seen
        seen.append(module)
        answer = Turn(
            "",
            (ToolCall(str(len(seen)), "write_handoff", {"markdown": RESPONSES[module].decode()}),),
            Usage(input_tokens=100, output_tokens=50),
            "tool_use",
            "gpt-6.1-sol",
            "fake",
            200,
        )
        return AdapterReply("ok", answer, None, 200, None, None, 1, 2, answer.usage)

    monkeypatch.setattr(adapter, "complete", complete)
    state = tmp_path / "state"
    executor = HandoffExecutor(state / "live", adapter=adapter, cap_usd=Decimal(10), check=checked)
    report = run_handoffs(path, state, execute=executor, check=checked)
    assert seen == ORDER
    assert verify_delivery(next(state.glob("delivery-*.json")), report.parent) == report
    assert run_handoffs(path, state, execute=executor, check=checked) == report
    assert seen == ORDER


@pytest.mark.parametrize(
    "changes",
    [
        {"execution": "live-provider", "provider_cap_usd": "0", "max_attempts": 1},
        {"execution": "live-provider", "provider_cap_usd": "10", "max_attempts": 2},
        {"execution": "synthetic", "provider_cap_usd": "10"},
    ],
)
def test_live_configuration_fails_before_dispatch(tmp_path, changes):
    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(changes)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        run_handoffs(
            path, tmp_path / "state", execute=lambda _: pytest.fail("dispatched"), check=checked
        )


def test_live_mode_rejects_unbounded_callback(tmp_path):
    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution="live-provider", provider_cap_usd="10", max_attempts=1)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cpos_execution_mode"):
        run_handoffs(path, tmp_path / "state", execute=replay, check=checked)


# A live run needs a delivery layout: one CP-1A table of the retained handoff in one block.
LIVE_LAYOUT = {
    "blocks": ["company-profile"],
    "scope": "synthetic live-wiring regression; one retained CP-1A table",
    "routes": [
        {
            "module_id": "CP-1A",
            "heading": "Company, business and revenue model",
            "kind": "table",
            "table_header": "Area",
            "block_id": "company-profile",
        }
    ],
}


def with_live_layout(data: dict) -> None:
    """Layout delivery routes selected analytical modules only, so CP-MODEL is not requested."""
    data["layout"] = LIVE_LAYOUT
    data["run"]["requested_modules"] = ["CP-1", "CP-1A", "CP-2"]


def job(tmp_path: Path) -> Path:
    manifest = json.loads((ROOT / "runs/tdg-002/snapshot-inputs.json").read_text())
    manifest.pop("handoffs")
    manifest.update(execution="retained-response-replay", sources={}, instructions={})
    for key, raw in {"source": b"Synthetic input for an infrastructure regression only."}.items():
        path = tmp_path / key
        path.write_bytes(raw)
        manifest["sources"][key] = {"path": key, "sha256": hashlib.sha256(raw).hexdigest()}
    for module in ORDER:
        path = tmp_path / f"{module}.instructions.md"
        raw = f"Infrastructure replay for {module}; compare with retained expected bytes.".encode()
        path.write_bytes(raw)
        manifest["instructions"][module] = {
            "path": path.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(manifest))
    return path


def checked(task: HandoffTask, response: bytes) -> tuple[str, ...]:
    return () if response == RESPONSES[task.module_id] else ("Retained expected bytes differ.",)


def replay(task: HandoffTask) -> bytes:
    return RESPONSES[task.module_id]


def test_order_current_handoffs_populated_delivery_and_resume(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    seen = []

    def execute(task: HandoffTask) -> bytes:
        assert list(task.handoffs) == ORDER[: len(seen)]
        assert dict(task.handoffs) == {m: RESPONSES[m] for m in ORDER[: len(seen)]}
        assert list(task.sources) == ["source"]
        with pytest.raises(TypeError):
            task.handoffs["CP-0"] = b"mutated"  # type: ignore[index]
        seen.append(task.module_id)
        return replay(task)

    report = run_handoffs(path, directory, execute=execute, check=checked)
    assert seen == ORDER
    assert report.exists()
    manifest = next(directory.glob("delivery-*.json"))
    assert verify_delivery(manifest, report.parent) == report
    assert len(json.loads((report.parent / "report-view.json").read_bytes())["blocks"]) == 5
    checks = []

    def recheck(task: HandoffTask, raw: bytes) -> tuple[str, ...]:
        checks.append(task.module_id)
        return checked(task, raw)

    def no_execution(task: HandoffTask) -> bytes:
        pytest.fail(f"Resume repeated {task.module_id}")

    assert run_handoffs(path, directory, execute=no_execution, check=recheck) == report
    assert checks == ORDER
    assert len(list(directory.glob("completed-*.json"))) == 1
    assert not list(directory.rglob("*.xlsx"))


def test_instruction_change_reuses_cp0_and_invalidates_actual_consumers(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    old_report = run_handoffs(path, directory, execute=replay, check=checked)
    old = old_report.read_bytes()
    manifest = json.loads(path.read_bytes())
    spec = manifest["instructions"]["CP-1"]
    updated = b"Changed CP-1 instruction revision. Retain the same checked source amounts."
    (tmp_path / spec["path"]).write_bytes(updated)
    spec["sha256"] = hashlib.sha256(updated).hexdigest()
    path.write_text(json.dumps(manifest))
    seen = []

    def execute(task: HandoffTask) -> bytes:
        seen.append(task.module_id)
        if task.module_id == "CP-1":
            return replay(task) + b"\nNew instruction revision was considered.\n"
        return replay(task)

    def check(task: HandoffTask, response: bytes) -> tuple[str, ...]:
        if task.module_id == "CP-1":
            assert task.instructions == updated
            assert response.startswith(RESPONSES["CP-1"])
            return ()
        return checked(task, response)

    new_report = run_handoffs(path, directory, execute=execute, check=check)
    assert seen == ["CP-1", "CP-1A", "CP-2"]
    assert new_report != old_report
    assert old_report.read_bytes() == old
    assert len(list(directory.glob("completed-*.json"))) == 2


def test_observed_failure_is_retained_repaired_and_not_passed_on(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    seen = []

    def execute(task: HandoffTask) -> bytes:
        seen.append((task.module_id, task.attempt))
        if task.module_id == "CP-1" and task.attempt == 1:
            return RESPONSES["CP-1"].replace(b"1,880", b"1,881")
        if task.module_id == "CP-1" and task.attempt == 2:
            assert task.feedback == ("Retained expected bytes differ.",)
        if task.module_id == "CP-1A":
            assert task.handoffs["CP-1"] == RESPONSES["CP-1"]
        return replay(task)

    run_handoffs(path, directory, execute=execute, check=checked)
    assert seen == [("CP-0", 1), ("CP-1", 1), ("CP-1", 2), ("CP-1A", 1), ("CP-2", 1)]
    failed = next(directory.glob("requests/CP-1/*/1.review.json"))
    assert json.loads(failed.read_bytes())["issues"] == ["Retained expected bytes differ."]
    assert failed.with_name("1.response.md").read_bytes() != RESPONSES["CP-1"]


def test_retry_ceiling_stops_before_consumers_or_delivery(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    seen = []

    def execute(task: HandoffTask) -> bytes:
        seen.append(task.module_id)
        return b"A malformed answer"

    with pytest.raises(ValueError, match="cpos_module_failed: CP-0"):
        run_handoffs(path, directory, execute=execute, check=checked)
    assert seen == ["CP-0", "CP-0"]
    assert not list(directory.glob("completed-*"))
    assert not (directory / "deliveries").exists()


def test_interrupted_dispatch_never_repeats_and_retained_response_can_resume(
    tmp_path: Path,
) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"

    def interrupted(task: HandoffTask) -> bytes:
        if task.module_id == "CP-1":
            raise RuntimeError("host exchange interrupted")
        return replay(task)

    with pytest.raises(RuntimeError, match="host exchange"):
        run_handoffs(path, directory, execute=interrupted, check=checked)
    with pytest.raises(ValueError, match="cpos_interrupted: response not retained for CP-1"):
        run_handoffs(path, directory, execute=replay, check=checked)
    pending = next(directory.glob("requests/CP-1/*/1.request.json"))
    pending.with_name("1.response.md").write_bytes(RESPONSES["CP-1"])
    assert run_handoffs(path, directory, execute=replay, check=checked).exists()


def test_changed_input_refuses_before_state_or_callbacks(tmp_path: Path) -> None:
    path = job(tmp_path)
    (tmp_path / "source").write_bytes(b"changed after pinning")
    directory = tmp_path / "state"
    with pytest.raises(ValueError, match="cpos_input_changed"):
        run_handoffs(path, directory, execute=replay, check=checked)
    assert not directory.exists()


def test_changed_cached_answer_refuses_even_when_markdown_still_valid(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    run_handoffs(path, directory, execute=replay, check=checked)
    response = next(directory.glob("requests/CP-1/*/1.response.md"))
    response.write_bytes(response.read_bytes().replace(b"1,880", b"1,881"))
    with pytest.raises(ValueError, match="cpos_response_changed: CP-1"):
        run_handoffs(path, directory, execute=replay, check=checked)


def test_changed_publication_and_forged_hash_record_do_not_complete(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    report = run_handoffs(path, directory, execute=replay, check=checked)
    # Simulate interruption after publication but before the CP-OS completion write.
    for completion in directory.glob("completed-*.json"):
        completion.unlink()
    report.write_bytes(report.read_bytes() + b"tampered")
    receipt_path = report.parent / "delivery.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt["files"]["report.html"] = hashlib.sha256(report.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    with pytest.raises(ValueError, match="delivery_changed: report.html"):
        run_handoffs(path, directory, execute=replay, check=checked)


def test_verifier_exception_rechecks_retained_bytes_without_execution(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"

    def broken_check(task: HandoffTask, raw: bytes) -> tuple[str, ...]:
        raise RuntimeError("check interrupted")

    with pytest.raises(RuntimeError, match="check interrupted"):
        run_handoffs(path, directory, execute=replay, check=broken_check)
    assert len(list(directory.rglob("*.response.md"))) == 1
    assert not list(directory.rglob("*.review.json"))
    assert run_handoffs(path, directory, execute=replay, check=checked).exists()


def test_one_writer_and_identity_are_enforced(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    directory.mkdir()
    with _single_writer(directory), pytest.raises(RunDirBusy):
        run_handoffs(path, directory, execute=replay, check=checked)
    run_handoffs(path, directory, execute=replay, check=checked)
    data = json.loads(path.read_bytes())
    data["execution"] = "host-session"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity_mismatch"):
        run_handoffs(path, directory, execute=replay, check=checked)


@pytest.mark.parametrize("change", ["provider_cap_usd", "instructions", "run"])
def test_unsupported_scope_or_paid_mode_cannot_dispatch(tmp_path: Path, change: str) -> None:
    path = job(tmp_path)
    value = json.loads(path.read_bytes())
    if change == "provider_cap_usd":
        value[change] = 5
    elif change == "instructions":
        value[change].pop("CP-1A")
    else:
        value[change]["pathway"] = "monitoring"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        run_handoffs(path, tmp_path / "state", execute=replay, check=checked)
    assert not (tmp_path / "state").exists()


def test_checker_must_supply_a_real_verdict_contract(tmp_path: Path) -> None:
    path = job(tmp_path)
    with pytest.raises(ValueError, match="cpos_check"):
        run_handoffs(path, tmp_path / "state", execute=replay, check=lambda *_: None)  # type: ignore[arg-type]


def test_delivery_cannot_be_replaced_with_an_empty_existing_directory(tmp_path: Path) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    report = run_handoffs(path, directory, execute=replay, check=checked)
    (report.parent / "CP-1.md").unlink()
    with pytest.raises(ValueError, match="delivery_files"):
        run_handoffs(path, directory, execute=replay, check=checked)


def test_interrupted_publication_resumes_without_repeating_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = job(tmp_path)
    directory = tmp_path / "state"
    original = Path.write_bytes

    def fail_report(path: Path, content: bytes) -> int:
        if path.name == "report.html":
            raise OSError("interrupted report write")
        return original(path, content)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_bytes", fail_report)
        with pytest.raises(OSError, match="interrupted report"):
            run_handoffs(path, directory, execute=replay, check=checked)
    assert not (directory / "deliveries").exists()
    assert not list(directory.glob("completed-*"))
    pending = list(directory.glob("pending-deliveries/*"))
    assert len(pending) == 1 and not (pending[0] / "delivery.json").exists()

    def no_execute(task: HandoffTask) -> bytes:
        pytest.fail(f"Publication repair repeated {task.module_id}")

    assert run_handoffs(path, directory, execute=no_execute, check=checked).exists()
    assert pending[0].exists()


def test_renderer_revision_creates_new_delivery_without_model_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from deploy_workflow import handoff_delivery

    path = job(tmp_path)
    directory = tmp_path / "state"
    before = run_handoffs(path, directory, execute=replay, check=checked)
    raw_before = before.read_bytes()
    original = handoff_delivery.render
    monkeypatch.setattr(
        handoff_delivery, "render", lambda *args: original(*args) + "\n<!-- revision -->"
    )

    def no_execute(task: HandoffTask) -> bytes:
        pytest.fail(f"Renderer revision repeated {task.module_id}")

    after = run_handoffs(path, directory, execute=no_execute, check=checked)
    assert after != before
    assert before.read_bytes() == raw_before
    assert after.read_bytes().endswith(b"<!-- revision -->")
    assert len(list(directory.glob("completed-*"))) == 2


def test_invalid_utf8_answer_gets_a_bounded_repair(tmp_path: Path) -> None:
    path = job(tmp_path)

    def execute(task: HandoffTask) -> bytes:
        if task.module_id == "CP-0" and task.attempt == 1:
            return b"\xff"
        if task.module_id == "CP-0":
            assert task.feedback == ("The response must be UTF-8 Markdown.",)
        return replay(task)

    assert run_handoffs(path, tmp_path / "state", execute=execute, check=checked).exists()


def test_replay_entry_point_requires_mode_and_pinned_responses(tmp_path: Path) -> None:
    path = job(tmp_path)
    entries = {}
    for module, raw in RESPONSES.items():
        response = tmp_path / f"{module}.md"
        response.write_bytes(raw)
        entries[module] = {"path": response.name, "sha256": hashlib.sha256(raw).hexdigest()}
    responses = tmp_path / "responses.json"
    responses.write_text(json.dumps(entries))
    assert replay_handoffs(path, tmp_path / "state", responses).exists()
    (tmp_path / "CP-1.md").write_bytes(b"changed response")
    with pytest.raises(ValueError, match="cpos_input_changed: CP-1"):
        replay_handoffs(path, tmp_path / "other", responses)
    assert not (tmp_path / "other").exists()
    manifest = json.loads(path.read_bytes())
    manifest["execution"] = "host-session"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="cpos_replay_mode"):
        replay_handoffs(path, tmp_path / "other", responses)


def retained_job(tmp_path: Path, modules: list[str] | None = None) -> Path:
    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data["execution"] = "host-session"
    data["retained_handoffs"] = {}
    for module in modules if modules is not None else ORDER[:3]:
        raw = RESPONSES[module]
        (tmp_path / f"{module}.retained.md").write_bytes(raw)
        data["retained_handoffs"][module] = {
            "path": f"{module}.retained.md",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_hashes": {k: v["sha256"] for k, v in data["sources"].items()},
            "upstream": {
                m: hashlib.sha256(RESPONSES[m]).hexdigest() for m in ORDER[: ORDER.index(module)]
            },
        }
    path.write_text(json.dumps(data))
    return path


def test_retained_upstreams_are_checked_without_executor_and_origins_are_recorded(
    tmp_path: Path,
) -> None:
    path = retained_job(tmp_path)
    directory = tmp_path / "state"
    executed = []
    verified = []

    def execute(task: HandoffTask) -> bytes:
        executed.append(task.module_id)
        assert task.module_id == "CP-2"
        assert dict(task.handoffs) == {m: RESPONSES[m] for m in ORDER[:3]}
        return replay(task)

    def check(task: HandoffTask, raw: bytes) -> tuple[str, ...]:
        verified.append(task.module_id)
        return checked(task, raw)

    report = run_handoffs(path, directory, execute=execute, check=check)
    assert report.exists() and executed == ["CP-2"] and verified == ORDER
    record = json.loads(next(directory.glob("completed-*.json")).read_bytes())
    assert record["module_execution"] == {
        "CP-0": "retained-response-replay",
        "CP-1": "retained-response-replay",
        "CP-1A": "retained-response-replay",
        "CP-2": "host-session",
    }
    for module in ORDER:
        request = json.loads(
            next(directory.glob(f"requests/{module}/*/1.request.json")).read_bytes()
        )
        assert request["retained_response_sha256"] == (
            hashlib.sha256(RESPONSES[module]).hexdigest() if module != "CP-2" else None
        )


def test_changed_retained_source_bytes_refuse_before_state(tmp_path: Path) -> None:
    path = retained_job(tmp_path)
    (tmp_path / "CP-1.retained.md").write_bytes(b"changed")
    with pytest.raises(ValueError, match="cpos_input_changed: CP-1"):
        run_handoffs(path, tmp_path / "state", execute=replay, check=checked)
    assert not (tmp_path / "state").exists()


def test_changed_source_pack_cannot_silently_rebind_retained_analysis(tmp_path: Path) -> None:
    path = retained_job(tmp_path)
    data = json.loads(path.read_bytes())
    (tmp_path / "source").write_bytes(b"Different source pack")
    data["sources"]["source"]["sha256"] = hashlib.sha256(b"Different source pack").hexdigest()
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cpos_retained_sources: CP-0"):
        run_handoffs(path, tmp_path / "state", execute=replay, check=checked)
    assert not (tmp_path / "state").exists()


def test_changed_upstream_cannot_silently_rebind_retained_consumer(tmp_path: Path) -> None:
    path = retained_job(tmp_path)
    directory = tmp_path / "state"
    data = json.loads(path.read_bytes())
    raw = RESPONSES["CP-1"] + b"\nChanged upstream conclusion.\n"
    (tmp_path / "CP-1.retained.md").write_bytes(raw)
    data["retained_handoffs"]["CP-1"]["sha256"] = hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(data))

    def check(task: HandoffTask, answer: bytes) -> tuple[str, ...]:
        return () if task.module_id == "CP-1" else checked(task, answer)

    with pytest.raises(ValueError, match="cpos_retained_stale: CP-1A"):
        run_handoffs(path, directory, execute=replay, check=check)
    assert not (directory / "requests" / "CP-1A").exists()
    assert not list(directory.glob("completed-*"))


def test_rejected_retained_analysis_is_not_reexecuted_or_consumed(tmp_path: Path) -> None:
    path = retained_job(tmp_path)
    directory = tmp_path / "state"

    def no_execute(task: HandoffTask) -> bytes:
        pytest.fail("A retained answer must never be reexecuted")

    with pytest.raises(ValueError, match="cpos_retained_rejected: CP-0"):
        run_handoffs(
            path, directory, execute=no_execute, check=lambda *_: ("Source review rejected",)
        )
    assert len(list(directory.glob("requests/CP-0/*/*.response.md"))) == 1
    assert not (directory / "requests" / "CP-1").exists()


def test_retained_response_without_review_cannot_be_swapped(tmp_path: Path) -> None:
    path = retained_job(tmp_path)
    directory = tmp_path / "state"

    def interrupted_check(task: HandoffTask, raw: bytes) -> tuple[str, ...]:
        raise RuntimeError("review interrupted")

    with pytest.raises(RuntimeError, match="review interrupted"):
        run_handoffs(path, directory, execute=replay, check=interrupted_check)
    response = next(directory.glob("requests/CP-0/*/*.response.md"))
    response.write_bytes(RESPONSES["CP-0"] + b"\nchanged\n")
    with pytest.raises(ValueError, match="cpos_response_changed: CP-0"):
        run_handoffs(path, directory, execute=replay, check=lambda *_: ())


def test_retained_mode_change_does_not_relabel_cached_execution(tmp_path: Path) -> None:
    path = retained_job(tmp_path)
    directory = tmp_path / "state"
    run_handoffs(path, directory, execute=replay, check=checked)
    data = json.loads(path.read_bytes())
    data["retained_handoffs"].pop("CP-1A")
    path.write_text(json.dumps(data))
    executed = []

    def execute(task: HandoffTask) -> bytes:
        executed.append(task.module_id)
        return replay(task)

    run_handoffs(path, directory, execute=execute, check=checked)
    assert executed == ["CP-1A"]
    records = [json.loads(p.read_bytes()) for p in directory.glob("completed-*.json")]
    assert len(records) == 2
    assert {r["module_execution"]["CP-1A"] for r in records} == {
        "retained-response-replay",
        "host-session",
    }


@pytest.mark.parametrize("raw", [b"", b"\xff"])
def test_empty_or_invalid_retained_answer_refuses_without_calling_executor(
    tmp_path: Path,
    raw: bytes,
) -> None:
    path = retained_job(tmp_path)
    data = json.loads(path.read_bytes())
    (tmp_path / "CP-0.retained.md").write_bytes(raw)
    data["retained_handoffs"]["CP-0"]["sha256"] = hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(data))

    def no_execute(task: HandoffTask) -> bytes:
        pytest.fail("An empty pinned answer is not a request for a new execution")

    with pytest.raises(ValueError, match="cpos_retained_rejected: CP-0"):
        run_handoffs(path, tmp_path / "state", execute=no_execute, check=checked)
    assert len(list((tmp_path / "state").rglob("*.response.md"))) == 1


def test_a_retained_pin_the_order_contradicts_is_refused_before_any_call(
    tmp_path: Path,
) -> None:
    path = retained_job(tmp_path, ["CP-0", "CP-2"])
    data = json.loads(path.read_bytes())
    del data["retained_handoffs"]["CP-2"]["upstream"]["CP-1"]
    path.write_text(json.dumps(data))

    def no_execute(task: HandoffTask) -> bytes:
        pytest.fail(f"{task.module_id} was called before a stale refusal the pins decide")

    with pytest.raises(ValueError, match="cpos_retained_stale: CP-2"):
        run_handoffs(path, tmp_path / "state", execute=no_execute, check=checked)


def test_a_wrong_pin_of_a_replayed_module_is_refused_before_the_module_between_is_called(
    tmp_path: Path,
) -> None:
    path = retained_job(tmp_path, ["CP-0", "CP-1A"])
    data = json.loads(path.read_bytes())
    data["retained_handoffs"]["CP-1A"]["upstream"]["CP-0"] = "0" * 64
    path.write_text(json.dumps(data))

    def no_execute(task: HandoffTask) -> bytes:
        pytest.fail(f"{task.module_id} was called before the stale refusal the replay decides")

    with pytest.raises(ValueError, match="cpos_retained_stale: CP-1A"):
        run_handoffs(path, tmp_path / "state", execute=no_execute, check=checked)


def test_every_pathway_resumes_in_the_fresh_order_for_every_kept_prefix() -> None:
    from deploy_vii.contracts import PATHWAY_MODULES
    from deploy_vii.registry import plan
    from deploy_workflow.owners.cpos_launch import NOT_ANALYTICAL

    for modules in PATHWAY_MODULES.values():
        requested = tuple(m for m in modules if m not in NOT_ANALYTICAL)
        fresh = plan(requested)
        for kept in range(1, len(fresh) + 1):
            pins = {m: fresh[:i] for i, m in enumerate(fresh[:kept])}
            assert plan(requested, retained=pins) == fresh


def test_replay_needs_no_duplicate_response_map_when_all_inputs_are_retained(
    tmp_path: Path,
) -> None:
    path = retained_job(tmp_path, ORDER)
    data = json.loads(path.read_bytes())
    data["execution"] = "retained-response-replay"
    path.write_text(json.dumps(data))
    assert replay_handoffs(path, tmp_path / "state").exists()


def test_replay_without_response_map_refuses_incomplete_retained_inputs(tmp_path: Path) -> None:
    path = retained_job(tmp_path)
    data = json.loads(path.read_bytes())
    data["execution"] = "retained-response-replay"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="cpos_replay_inputs"):
        replay_handoffs(path, tmp_path / "state")
    assert not (tmp_path / "state").exists()


def test_observer_stops_after_durable_handoff_and_resumes_without_duplicate_dispatch(tmp_path):
    manifest = job(tmp_path)
    state = tmp_path / "state"
    sent = []

    def execute(task):
        sent.append(task.module_id)
        return RESPONSES[task.module_id]

    def observe(task, raw):
        assert raw == RESPONSES[task.module_id]
        assert list(state.glob("requests/" + task.module_id + "/*/*.review.json"))
        raise RuntimeError("host evidence review")

    with pytest.raises(RuntimeError, match="host evidence review"):
        run_handoffs(manifest, state, execute=execute, check=checked, on_handoff=observe)
    assert sent == ["CP-0"]
    assert not list(state.glob("requests/CP-1/*/*.request.json"))
    assert not list(state.glob("completed-*.json"))
    report = run_handoffs(manifest, state, execute=execute, check=checked)
    assert sent == ORDER
    assert verify_delivery(next(state.glob("delivery-*.json")), report.parent) == report


COPILOT_RULING = (
    "lifts: live-provider-pause\nby: user\ndate: 2026-11-01\nconfigs: copilot-opus-medium\n"
)


def live_job(tmp_path: Path) -> Path:
    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution="live-provider", provider_cap_usd="10", max_attempts=1)
    with_live_layout(data)
    path.write_text(json.dumps(data))
    return path


def copilot_rig(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "rulings"
    root.mkdir()
    ruling = root / "copilot.md"
    ruling.write_text(COPILOT_RULING, encoding="utf-8")
    return root, ruling


def test_copilot_config_selects_the_copilot_adapter(tmp_path, monkeypatch):
    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.model.handoff import HandoffExecutor
    from deploy_workflow.owners import cpos

    root, ruling = copilot_rig(tmp_path)
    built, closed = [], []
    real_close = CopilotAdapter.close

    def close(self):
        closed.append(self)
        real_close(self)

    def fake_run(manifest, directory, **kwargs):
        execute = kwargs["execute"]
        assert isinstance(execute, HandoffExecutor) and not closed
        built.append(execute.adapter)
        return directory / "report.html"

    monkeypatch.setattr(CopilotAdapter, "close", close)
    monkeypatch.setattr(cpos, "run_handoffs", fake_run)
    cpos.run_live_handoffs(
        live_job(tmp_path),
        tmp_path / "state",
        ruling=ruling,
        check=checked,
        environ={},
        config="copilot-opus-medium",
        rulings_root=root,
    )
    (adapter,) = built
    assert isinstance(adapter, CopilotAdapter) and adapter.config_id == "copilot-opus-medium"
    assert closed == [adapter]  # released after the executor finished
    assert adapter._loop is None  # no runtime was started: no complete ran


def test_copilot_adapter_is_closed_when_the_run_fails(tmp_path, monkeypatch):
    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.owners import cpos

    root, ruling = copilot_rig(tmp_path)
    closed = []
    real_close = CopilotAdapter.close

    def close(self):
        closed.append(self)
        real_close(self)

    def failing(*args, **kwargs):
        raise RuntimeError("executor failed")

    monkeypatch.setattr(CopilotAdapter, "close", close)
    monkeypatch.setattr(cpos, "run_handoffs", failing)
    with pytest.raises(RuntimeError, match="executor failed"):
        cpos.run_live_handoffs(
            live_job(tmp_path),
            tmp_path / "state",
            ruling=ruling,
            check=checked,
            environ={},
            config="copilot-opus-medium",
            rulings_root=root,
        )
    assert len(closed) == 1


def test_live_mode_check_accepts_copilot_adapter(tmp_path):
    from decimal import Decimal

    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.model.handoff import HandoffExecutor
    from deploy_workflow.model.turn import ModelSpec

    root, ruling = copilot_rig(tmp_path)
    spec = ModelSpec("copilot-opus-medium", "copilot", "claude-opus-5.5", "medium")
    adapter = CopilotAdapter(spec, ruling, environ={}, rulings_root=root)
    try:
        # A cap that differs from the manifest's passes the adapter-type guard and stops at the
        # next one: the executor must share this run's cap.
        executor = HandoffExecutor(
            tmp_path / "state" / "live", adapter=adapter, cap_usd=Decimal(5), check=checked
        )
        with pytest.raises(ValueError, match="cpos_live_binding"):
            run_handoffs(live_job(tmp_path), tmp_path / "state", execute=executor, check=checked)
        # The same executor is still refused for a manifest that is not live.
        other = tmp_path / "other"
        other.mkdir()
        with pytest.raises(ValueError, match="cpos_execution_mode"):
            run_handoffs(job(other), tmp_path / "state", execute=executor, check=checked)
    finally:
        adapter.close()


def test_release_failure_does_not_mask_the_runs_own_stop(tmp_path, monkeypatch):
    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.model.turn import ModelSpec
    from deploy_workflow.owners import cpos
    from tests.model.test_copilot_adapter import FakeClient, FakeSession

    class SendFails(FakeSession):
        async def send(self, text, /):
            raise RuntimeError("runtime went away")

    class Client(FakeClient):
        async def create_session(self, **options):
            session = SendFails(self.script, options)
            self.sessions.append(session)
            return session

        async def stop(self):
            raise RuntimeError("pipe closed")

    root, ruling = copilot_rig(tmp_path)
    ruling.write_text(COPILOT_RULING.replace("opus", "sol"), encoding="utf-8")
    runtime = tmp_path / "copilot-runtime"
    runtime.write_text("#!/bin/sh\n")
    environ = {"COPILOT_GITHUB_TOKEN": "ghp_" + "A" * 36, "COPILOT_CLI_PATH": str(runtime)}
    monkeypatch.chdir(tmp_path)  # the adapter's per-call home is created under the cwd

    def adapter_for(selected, ruling_, environment, rulings_root):
        spec = ModelSpec(selected.config_id, selected.provider, selected.model, selected.effort)
        return CopilotAdapter(
            spec,
            ruling_,
            environ=environment,
            rulings_root=rulings_root,
            client_factory=lambda options: Client([]),
        )

    monkeypatch.setattr(cpos, "live_adapter_for", adapter_for)
    with pytest.raises(RuntimeError, match="cpos_live_stopped: sent_unknown") as stopped:
        cpos.run_live_handoffs(
            live_job(tmp_path),
            tmp_path / "state",
            ruling=ruling,
            check=checked,
            environ=environ,
            config="copilot-sol-medium",
            rulings_root=root,
        )
    assert any("RuntimeError" in note for note in stopped.value.__notes__)


def test_release_failure_after_a_successful_run_keeps_the_result_and_warns(tmp_path, monkeypatch):
    from deploy_workflow.owners import cpos

    root, ruling = copilot_rig(tmp_path)

    def release(adapter):
        raise OSError("stop failed: OSError")

    monkeypatch.setattr(cpos, "run_handoffs", lambda *a, **k: tmp_path / "report.html")
    monkeypatch.setattr(cpos, "_release", release)
    with pytest.warns(RuntimeWarning, match="adapter release failed: stop failed: OSError"):
        report = cpos.run_live_handoffs(
            live_job(tmp_path),
            tmp_path / "state",
            ruling=ruling,
            check=checked,
            environ={},
            config="copilot-opus-medium",
            rulings_root=root,
        )
    assert report == tmp_path / "report.html"


def test_failed_response_write_leaves_no_torn_answer_and_never_redispatches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S01-A02/C02: a response write that fails (EIO/ENOSPC on sync) must leave no final
    `1.response.md`. Before the fix `_put` wrote in place, so resume read the torn bytes as the
    retained answer, skipped the executor and delivered them. Expected, by hand: CP-1's final
    response is absent, no `.pending-*` temp remains, resume refuses with `cpos_interrupted`
    without a single executor call, and no completion record exists."""
    path = job(tmp_path)
    directory = tmp_path / "state"
    real_open = Path.open
    armed = []

    class HalfWrite:  # the disk fills after half the bytes of the next created file
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *exc: object) -> None:
            self.stream.close()

        def write(self, raw: bytes) -> int:
            self.stream.write(raw[: len(raw) // 2])
            self.stream.flush()
            raise OSError(28, "No space left on device")

    def opening(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        stream = real_open(self, mode, *args, **kwargs)
        if mode == "xb" and armed:
            armed.clear()
            return HalfWrite(stream)
        return stream

    def execute(task: HandoffTask) -> bytes:
        if task.module_id == "CP-1":
            armed.append(True)  # the next created file is CP-1's response
        return replay(task)

    monkeypatch.setattr(Path, "open", opening)
    with pytest.raises(OSError, match="No space left"):
        run_handoffs(path, directory, execute=execute, check=checked)
    monkeypatch.setattr(Path, "open", real_open)
    folder = next(directory.glob("requests/CP-1/*"))
    assert sorted(p.name for p in folder.iterdir()) == ["1.request.json"]
    calls: list[str] = []
    with pytest.raises(ValueError, match="cpos_interrupted: response not retained for CP-1"):
        run_handoffs(
            path, directory, execute=lambda t: calls.append(t.module_id) or b"", check=checked
        )
    assert calls == []
    assert not list(directory.glob("completed-*"))


def test_put_publishes_whole_bytes_once_beside_a_stale_temp_file(tmp_path: Path) -> None:
    """A temp file a killed writer left behind is neither read nor reused. Expected, by hand: the
    target holds exactly b"complete answer\\n", the stale `.pending-` file is untouched (it is not
    `_put`'s to remove), an identical rewrite is a no-op, a different one is `identity_mismatch`,
    and no new temp file remains after either."""
    from deploy_workflow.workflow import WorkflowError, _put

    stale = tmp_path / ".pending-0123456789abcdef0123456789abcdef"
    stale.write_bytes(b"compl")
    target = tmp_path / "1.response.md"
    _put(target, b"complete answer\n")
    _put(target, b"complete answer\n")
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        _put(target, b"complete answer\nplus more\n")
    assert target.read_bytes() == b"complete answer\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == [stale.name, target.name]


def test_fixed_checker_accepts_a_falsely_rejected_retained_answer_without_execution(
    tmp_path: Path,
) -> None:
    """S01-C05: one attempt (as in live mode); a buggy checker falsely rejects CP-1's correct
    answer. Before the fix, rerunning the same directory with the fixed checker died with
    `identity_mismatch` (the new verdict could not be written over `1.review.json`). Expected, by
    hand: the rerun completes with no executor call for CP-0 or CP-1 (both retained), the false
    verdict stays in `1.review.json` and the new one, {"issues": [], "response_sha256":
    sha256(CP-1 answer)}, is kept beside it as `1.review-<its sha256>.json`."""
    path = job(tmp_path)
    data = json.loads(path.read_text())
    data["max_attempts"] = 1
    path.write_text(json.dumps(data))
    directory = tmp_path / "state"

    def buggy(task: HandoffTask, response: bytes) -> tuple[str, ...]:
        return ("false rejection",) if task.module_id == "CP-1" else checked(task, response)

    with pytest.raises(ValueError, match="cpos_module_failed: CP-1: false rejection"):
        run_handoffs(path, directory, execute=replay, check=buggy)
    seen: list[str] = []

    def execute(task: HandoffTask) -> bytes:
        seen.append(task.module_id)
        return replay(task)

    assert run_handoffs(path, directory, execute=execute, check=checked).exists()
    assert seen == ["CP-1A", "CP-2"]
    folder = next(directory.glob("requests/CP-1/*"))
    first = json.loads((folder / "1.review.json").read_bytes())
    assert first["issues"] == ["false rejection"]
    expected = {"issues": [], "response_sha256": hashlib.sha256(RESPONSES["CP-1"]).hexdigest()}
    raw = json.dumps(expected, sort_keys=True, indent=2).encode()
    assert (folder / f"1.review-{hashlib.sha256(raw).hexdigest()}.json").read_bytes() == raw
    # A second rerun with the same checker adds nothing.
    assert run_handoffs(path, directory, execute=execute, check=checked).exists()
    assert seen == ["CP-1A", "CP-2"]
    assert len(list(folder.glob("1.review*.json"))) == 2


def test_a_changed_recheck_verdict_cannot_reuse_the_next_attempts_answer(tmp_path: Path) -> None:
    """Two attempts: CP-1's first answer was rejected with issue A and attempt 2 answered A. A
    checker that now rejects attempt 1 with issue B would send attempt 2 other feedback, so the
    retained attempt-2 answer cannot stand for it. Expected, by hand: `cpos_feedback_changed:
    CP-1`, no executor call, no completion record."""
    path = job(tmp_path)
    directory = tmp_path / "state"

    def first_attempt_rejected(issue: str) -> Any:
        def check(task: HandoffTask, response: bytes) -> tuple[str, ...]:
            if task.module_id == "CP-1" and task.attempt == 1:
                return (issue,)
            return checked(task, response)

        return check

    run_handoffs(path, directory, execute=replay, check=first_attempt_rejected("issue A"))
    calls: list[str] = []
    with pytest.raises(ValueError, match="cpos_feedback_changed: CP-1"):
        run_handoffs(
            path,
            directory,
            execute=lambda t: calls.append(t.module_id) or b"",
            check=first_attempt_rejected("issue B"),
        )
    assert calls == []
    assert len(list(directory.glob("completed-*.json"))) == 1  # the first run's only


def test_put_failures_leave_a_complete_target_or_none_and_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review of S01-A02/C02. Expected, by hand: a filesystem without hard links (`os.link` refused)
    publishes nothing and leaves no temp file; a directory sync that fails after the link leaves the
    complete target, no temp file, and an identical retry succeeds."""
    from deploy_workflow import workflow

    target = tmp_path / "a" / "1.response.md"
    with monkeypatch.context() as patch:
        patch.setattr(workflow.os, "link", lambda *_: (_ for _ in ()).throw(OSError(1, "no links")))
        with pytest.raises(OSError, match="no links"):
            workflow._put(target, b"whole\n")
    assert list(target.parent.iterdir()) == []
    with monkeypatch.context() as patch:
        patch.setattr(
            workflow, "fsync_directory", lambda *_: (_ for _ in ()).throw(OSError(5, "EIO"))
        )
        with pytest.raises(OSError, match="EIO"):
            workflow._put(target, b"whole\n")
    assert [p.name for p in target.parent.iterdir()] == [target.name]
    assert target.read_bytes() == b"whole\n"
    workflow._put(target, b"whole\n")
    assert [p.name for p in target.parent.iterdir()] == [target.name]


def test_review_revisions_are_kept_once_per_distinct_verdict(tmp_path: Path) -> None:
    """Review of S01-C05. Verdicts A, B, A, C, B arrive for one attempt. Expected, by hand: the
    first stays in `1.review.json`; B and C are each kept once as
    `1.review-<sha256 of its bytes>.json`; returning to A or B writes nothing: three files, the
    original unchanged."""
    from deploy_workflow.owners.cpos import _retain_review

    def verdict(issue: str) -> bytes:
        return json.dumps({"issues": [issue], "response_sha256": "r"}, sort_keys=True).encode()

    base = tmp_path / "1.review.json"
    for issue in ("A", "B", "A", "C", "B"):
        _retain_review(base, verdict(issue))
    names = sorted(p.name for p in tmp_path.iterdir())
    expected = sorted(
        ["1.review.json"]
        + [f"1.review-{hashlib.sha256(verdict(i)).hexdigest()}.json" for i in ("B", "C")]
    )
    assert names == expected
    assert base.read_bytes() == verdict("A")


def test_a_fixed_checker_accepting_the_first_attempt_selects_it_without_execution(
    tmp_path: Path,
) -> None:
    """Review of S01-C05, two attempts. A checker falsely rejects CP-1 attempt 1; attempt 2 is
    accepted. Rerun with a checker accepting attempt 1. Expected, by hand: no executor call (the
    request for attempt 2 is never reached), CP-1's selected response is `1.response.md`, and the
    retained verdict for attempt 2 stays untouched."""
    path = job(tmp_path)
    directory = tmp_path / "state"

    def buggy(task: HandoffTask, response: bytes) -> tuple[str, ...]:
        if task.module_id == "CP-1" and task.attempt == 1:
            return ("false rejection",)
        return checked(task, response)

    run_handoffs(path, directory, execute=replay, check=buggy)
    folder = next(directory.glob("requests/CP-1/*"))
    second = (folder / "2.review.json").read_bytes()
    calls: list[str] = []
    run_handoffs(path, directory, execute=lambda t: calls.append(t.module_id) or b"", check=checked)
    assert calls == []
    assert (folder / "2.review.json").read_bytes() == second
    modules = [json.loads(p.read_bytes())["modules"]["CP-1"] for p in directory.glob("completed-*")]
    assert sorted(m.rsplit("/", 1)[1] for m in modules) == ["1.response.md", "2.response.md"]


def test_live_run_events_cover_modules_and_delivery(tmp_path, monkeypatch):
    """Fake transport proves the event wiring only; this is not a provider/module proof."""
    from deploy_workflow.model.adapter import AdapterReply, LiveAdapter
    from deploy_workflow.model.turn import ToolCall, Turn, Usage
    from deploy_workflow.owners import cpos
    from deploy_workflow.run_events import EVENTS, read_events

    def complete(self, request, **kwargs):
        module = json.loads(request.messages[1].text)["module_id"]
        answer = Turn(
            "",
            (ToolCall(module, "write_handoff", {"markdown": RESPONSES[module].decode()}),),
            Usage(input_tokens=100, output_tokens=50),
            "tool_use",
            "gpt-6.1-sol",
            "fake",
            200,
        )
        return AdapterReply("ok", answer, None, 200, None, None, 1, 2, answer.usage)

    monkeypatch.setattr(LiveAdapter, "complete", complete)
    state = tmp_path / "state"
    cpos.run_live_handoffs(
        live_job(tmp_path),
        state,
        ruling=ROOT / "docs/rulings/2026-11-05-live-loop-tests.md",
        check=checked,
        environ={},
    )
    events = read_events(state / EVENTS)
    assert [e["event"] for e in events if e["event"] != "turn"] == [
        "module_started",
        "module_accepted",
        "module_started",
        "module_accepted",
        "module_started",
        "module_accepted",
        "module_started",
        "module_accepted",
        "delivery_started",
        "delivered",
    ]
    assert [e["module"] for e in events if e["event"] == "module_started"] == ORDER
    assert [e["module"] for e in events if e["event"] == "turn"] == ORDER


def test_a_live_run_that_fails_logs_its_stop_reason(tmp_path, monkeypatch):
    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.owners import cpos
    from deploy_workflow.run_events import EVENTS, read_events

    def refuses(*args, **kwargs):
        raise ValueError("cpos_module_failed: CP-0: bad")

    monkeypatch.setattr(cpos, "run_handoffs", refuses)
    monkeypatch.setattr(LiveAdapter, "complete", lambda *a, **k: pytest.fail("called"))
    with pytest.raises(ValueError, match="cpos_module_failed"):
        cpos.run_live_handoffs(
            live_job(tmp_path),
            tmp_path / "state",
            ruling=ROOT / "docs/rulings/2026-11-05-live-loop-tests.md",
            check=checked,
            environ={},
        )
    (event,) = read_events(tmp_path / "state" / EVENTS)
    assert (event["event"], event["reason"]) == ("stopped", "checker")


def test_a_second_invocation_refused_as_busy_logs_no_stop(tmp_path, monkeypatch):
    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.owners import cpos
    from deploy_workflow.run_events import EVENTS, append_event, read_events

    monkeypatch.setattr(LiveAdapter, "complete", lambda *a, **k: pytest.fail("called"))
    state = tmp_path / "state"
    state.mkdir()
    with _single_writer(state):  # run A holds the folder and has logged its first module
        append_event(state, "module_started", module="CP-0")
        with pytest.raises(RunDirBusy):
            cpos.run_live_handoffs(
                live_job(tmp_path),
                state,
                ruling=ROOT / "docs/rulings/2026-11-05-live-loop-tests.md",
                check=checked,
                environ={},
            )
    assert [e["event"] for e in read_events(state / EVENTS)] == ["module_started"]


def test_a_run_without_an_events_folder_writes_no_events(tmp_path):
    path = job(tmp_path)
    state = tmp_path / "state"
    run_handoffs(path, state, execute=replay, check=checked)
    assert not list(state.rglob("events.jsonl"))


def test_a_delivered_event_that_cannot_be_written_leaves_the_run_completed(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from deploy_workflow import run_events

    real = run_events.os.fsync

    def fsync_unless_delivered(fd):
        if (tmp_path / "state" / "events.jsonl").read_bytes().endswith(b'"delivered"}\n'):
            raise OSError(28, "No space left on device")
        real(fd)

    monkeypatch.setattr(run_events, "os", SimpleNamespace(fsync=fsync_unless_delivered))
    path = job(tmp_path)
    state = tmp_path / "state"
    with pytest.warns(RuntimeWarning, match="run event not recorded") as caught:
        report = run_handoffs(path, state, execute=replay, check=checked, events=state)
    assert any("delivered" in str(w.message) for w in caught)
    assert verify_delivery(next(state.glob("delivery-*.json")), report.parent) == report
    assert list(state.glob("completed-*.json"))


def test_a_live_run_without_a_layout_is_refused_before_any_call(tmp_path, monkeypatch):
    from decimal import Decimal

    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.model.handoff import HandoffExecutor
    from deploy_workflow.model.turn import ModelSpec

    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    data.update(execution="live-provider", provider_cap_usd="10", max_attempts=1)
    assert "layout" not in data
    path.write_text(json.dumps(data))
    adapter = LiveAdapter(
        ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium"),
        ROOT / "docs/rulings/2026-11-05-live-loop-tests.md",
        environ={},
    )
    calls = []
    monkeypatch.setattr(adapter, "complete", lambda request, **kwargs: calls.append(request))
    state = tmp_path / "state"
    executor = HandoffExecutor(state / "live", adapter=adapter, cap_usd=Decimal(10), check=checked)
    with pytest.raises(
        ValueError, match="cpos_layout: a live-provider run needs a delivery layout"
    ):
        run_handoffs(path, state, execute=executor, check=checked)
    assert calls == []


def test_a_front_route_naming_an_unselected_module_is_refused_before_any_call(tmp_path):
    path = job(tmp_path)
    data = json.loads(path.read_bytes())
    with_live_layout(data)
    front = {**LIVE_LAYOUT["routes"][0], "module_id": "CP-6", "block_id": "front"}
    data["layout"] = {**LIVE_LAYOUT, "front": [front]}
    path.write_text(json.dumps(data))
    calls = []
    with pytest.raises(ValueError, match="cpos_layout: route selected modules"):
        run_handoffs(
            path, tmp_path / "state", execute=lambda task: calls.append(task), check=checked
        )
    assert calls == []
