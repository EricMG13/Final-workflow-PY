"""Offline CP-OS intake/transport regressions; no provider or analytical success claims."""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
import test_cpos_launch
from test_cpos_launch import (
    AS_OF,
    COVENANT_MODULES,
    COVENANT_ROUTES,
    ISSUER,
    answer,
    context_file,
    issuer_folder,
)

from deploy_workflow.model.adapter import LiveAdapter
from deploy_workflow.platform_io import read_at

provider = test_cpos_launch.provider  # The same fake provider fixture.
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "app_bridge", ROOT / "apps/issuer-library/engine/bridge.py"
)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
store_spec = importlib.util.spec_from_file_location(
    "app_store", ROOT / "apps/issuer-library/engine/store.py"
)
store = importlib.util.module_from_spec(store_spec)
store_spec.loader.exec_module(store)


def job(tmp_path, pathway="covenant_refinancing", **extra):
    """A web job as the server stages it: context.json plus sources/ under intake/<id>/."""
    root = tmp_path / "workspace"
    folder = root / "intake" / ("web-" + "a" * 32)
    folder.mkdir(parents=True)
    (root / "runs").mkdir()
    (folder / "context.json").write_bytes(context_file(tmp_path, pathway).read_bytes())
    sources = []
    for path in sorted(p for p in issuer_folder(tmp_path).rglob("*") if p.is_file()):
        relative = path.relative_to(tmp_path / "issuer").as_posix()
        target = folder / "sources" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        sources.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    value = {
        "id": folder.name,
        "workspace": str(root),
        "config": "sol-medium",
        "cap_usd": "50",
        "modules": [],
        "max_turns": 32,
        "sources": sources,
        **extra,
    }
    bridge.write_json(folder / "job.json", value)
    return folder, value


def status_of(folder):
    return json.loads((folder / "status.json").read_text())


def test_review_prepares_the_launch_offline_and_starts_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    folder, value = job(tmp_path)
    (folder / "sources" / "notes.xyz").write_text("unusable")
    (folder / "sources" / "_hold").mkdir()
    (folder / "sources" / "_hold" / "draft.txt").write_text("set aside")
    for name in ("notes.xyz", "_hold/draft.txt"):
        raw = (folder / "sources" / name).read_bytes()
        value["sources"].append({"path": name, "sha256": hashlib.sha256(raw).hexdigest()})
    bridge.write_json(folder / "job.json", value)
    result = bridge.review(folder)
    assert result["ok"] and result["issuer"] == ISSUER and result["as_of"] == AS_OF
    assert tuple(result["modules"]) == COVENANT_MODULES
    assert (result["provider"], result["model"], result["effort"]) == (
        "openai",
        "gpt-6.1-sol",
        "medium",
    )
    assert result["cap_usd"] == "50" and not result["provider_ready"]
    assert result["ignored"] == ["_hold/draft.txt", "chart.png", "notes.xyz"]
    # Hand key: the covenant pathway's report sections listed in test_cpos_launch.
    assert set(result["report_sections"]) == {route[0] for route in COVENANT_ROUTES}
    assert "not been independently reviewed" in result["scope"]
    assert Decimal(result["hold_usd"]) > 0
    assert not list((Path(value["workspace"]) / "runs").iterdir())
    assert not (folder / "start-authorization.md").exists()
    assert sorted(p.name for p in folder.iterdir()) == ["context.json", "job.json", "sources"]


def test_review_refuses_a_changed_source_and_a_bad_budget_offline(tmp_path):
    folder, value = job(tmp_path)
    changed = folder / "sources" / value["sources"][0]["path"]
    original = changed.read_bytes()
    changed.write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        bridge.review(folder)
    changed.write_bytes(original)
    for cap, reason in (("NaN", "positive"), ("0", "positive"), ("0.01", "holds up to")):
        value["cap_usd"] = cap
        bridge.write_json(folder / "job.json", value)
        with pytest.raises(ValueError, match=reason):
            bridge.review(folder)


def test_review_narrows_to_requested_modules_with_their_dependencies(tmp_path):
    folder, _ = job(tmp_path, modules=["CP-4"])
    # Same hand key as test_explicit_modules_narrow_the_run_and_keep_dependencies.
    assert bridge.review(folder)["modules"] == ["CP-0", "CP-1", "CP-4"]


def test_start_requires_same_review_and_configured_provider(tmp_path, monkeypatch):
    folder, value = job(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    bridge.write_json(folder / "review.json", bridge.review(folder))
    monkeypatch.setattr(bridge, "run_live_handoffs", lambda *a, **k: pytest.fail("ran"))
    value["cap_usd"] = "60"
    bridge.write_json(folder / "job.json", value)
    with pytest.raises(ValueError, match="stale"):
        bridge.start(folder)
    assert not (folder / "start-authorization.md").exists()
    value["cap_usd"] = "50"
    bridge.write_json(folder / "job.json", value)
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ValueError, match="not configured"):
        bridge.start(folder)
    assert not (folder / "start-authorization.md").exists()
    assert not (Path(value["workspace"]) / "runs" / value["id"]).exists()


def started(tmp_path, provider, **extra):
    folder, value = job(tmp_path, **extra)
    bridge.write_json(folder / "review.json", bridge.review(folder))
    return folder, Path(value["workspace"]) / "runs" / value["id"]


def test_start_runs_the_launcher_to_a_report_the_library_can_serve(tmp_path, provider):
    """A fake provider proves wiring only: order, retention, status, spend, report location."""
    folder, run_dir = started(tmp_path, provider)
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    seen: list[dict[str, str]] = []

    def recording(context):
        # Hand key: the event log's last module_started names the module being asked now.
        started = [
            e["module"]
            for e in map(json.loads, (run_dir / "events.jsonl").read_text().splitlines())
            if e["event"] == "module_started"
        ]
        seen.append(started[-1])
        return answer(context, routes)

    provider.answer = recording
    bridge.start(folder)
    assert tuple(call[0] for call in provider.calls) == COVENANT_MODULES
    assert tuple(seen) == COVENANT_MODULES
    assert not (run_dir / "progress.json").exists()
    assert {call[1] for call in provider.calls} == {"sol-medium"}
    status = status_of(folder)
    assert status["state"] == "complete" and Decimal(status["spent_usd"]) > 0
    assert "Automated checks only" in status["message"]
    report = next(run_dir.glob("deliveries/*/report.html"))
    assert ISSUER in report.read_text(encoding="utf-8")
    manifest = json.loads((report.parent / "delivery.json").read_text())
    assert {"report.html", "view.json", "CP-0.md"} <= set(manifest["files"])
    logged = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    accepted = [e["module"] for e in logged if e["event"] == "module_accepted"]
    assert accepted == list(COVENANT_MODULES)
    assert logged[-1]["event"] == "delivered" and "reason" not in status
    authorisation = (folder / "start-authorization.md").read_text()
    assert "configs: sol-medium" in authorisation and "by: user" in authorisation
    assert (
        f"review: {json.loads((folder / 'review.json').read_text())['review_id']}" in authorisation
    )
    calls = len(provider.calls)
    with pytest.raises(FileExistsError):
        bridge.start(folder)
    assert len(provider.calls) == calls


def test_a_rejected_module_stops_with_retained_work_and_no_report(tmp_path, provider):
    folder, run_dir = started(tmp_path, provider)
    provider.answer = lambda context: "# Not a handoff, and not-a-real-key leaked"
    bridge.start(folder)
    status = status_of(folder)
    assert status["state"] == "stopped" and "no automatic paid retry" in status["message"]
    assert "not-a-real-key" not in status["message"]
    assert status["reason"] == "checker"
    assert not list(run_dir.glob("deliveries/*/report.html"))
    assert (run_dir / "live").is_dir()


def test_an_open_workbook_lock_file_is_listed_not_fatal(tmp_path):
    """Windows and Office leave these beside a user's files; none is an issuer source."""
    folder, value = job(tmp_path)
    for name, raw in (
        ("~$Model.xlsx", b"\x05Owner" + b"\x00" * 150),
        ("Thumbs.db", b"\xd0\xcf\x11\xe0"),
        ("desktop.ini", b"[.ShellClassInfo]\r\n"),
    ):
        (folder / "sources" / name).write_bytes(raw)
        value["sources"].append({"path": name, "sha256": hashlib.sha256(raw).hexdigest()})
    bridge.write_json(folder / "job.json", value)
    assert {"~$Model.xlsx", "Thumbs.db", "desktop.ini"} <= set(bridge.review(folder)["ignored"])


def test_a_file_held_open_for_a_moment_does_not_fail_a_paid_run(tmp_path, provider, monkeypatch):
    """Windows refuses to replace or rename a file a scanner or a status read has open."""
    folder, run_dir = started(tmp_path, provider)
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    provider.answer = lambda context: answer(context, routes)
    held = set()

    def held_once(real):
        def call(source, target, **options):
            if str(target) not in held:
                held.add(str(target))
                raise PermissionError(13, "held open", str(target))
            return real(source, target, **options)

        return call

    monkeypatch.setattr(os, "replace", held_once(os.replace))
    monkeypatch.setattr(os, "rename", held_once(os.rename))
    monkeypatch.setattr(time, "sleep", lambda _: None)
    bridge.start(folder)
    assert status_of(folder)["state"] == "complete"
    assert held and next(run_dir.glob("deliveries/*/report.html"))


def test_review_refuses_a_workspace_too_deep_for_a_run(tmp_path, monkeypatch):
    folder, _ = job(tmp_path)
    # Longer than any file name, so the probe fails as a long path does on Windows.
    monkeypatch.setattr(bridge, "RUN_PATH_ROOM", 300)
    with pytest.raises(ValueError, match="shorter workspace folder"):
        bridge.review(folder)


def test_the_path_check_covers_the_longest_file_a_run_writes(tmp_path, provider):
    folder, run_dir = started(tmp_path, provider)
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    provider.answer = lambda context: answer(context, routes)
    bridge.start(folder)
    longest = max(len(str(path)) for path in run_dir.rglob("*"))
    assert len(str(folder / ("x" * bridge.RUN_PATH_ROOM))) >= longest
    # Also the transient temp every retained file is written through, in the deepest folders, and a
    # recheck's verdict revision (`<n>.review-<sha256>.json`) in a request folder.
    temp = ".pending-" + "0" * 32
    revision = "1.review-" + "0" * 64 + ".json"
    folders = [p for p in run_dir.rglob("*") if p.is_dir()]
    deepest = max(len(str(p / temp)) for p in folders)
    requests = [p for p in folders if p.parent.parent.name == "requests"]
    deepest = max([deepest, *(len(str(p / revision)) for p in requests)])
    assert len(str(folder / ("x" * bridge.RUN_PATH_ROOM))) >= deepest


def test_a_staged_file_that_cannot_be_read_is_named(tmp_path):
    folder, value = job(tmp_path)
    (folder / "sources" / value["sources"][0]["path"]).unlink()
    with pytest.raises(ValueError, match="shorter"):
        bridge.review(folder)


def library_of(run_dir):
    catalogue = {
        "issues": [],
        "real": [{"id": run_dir.name, "name": run_dir.name, "artifacts": []}],
    }
    return store.workspace_store(run_dir.parent.parent, catalogue)


def test_a_stopped_run_shows_what_it_accepted_and_not_what_it_rejected(tmp_path, provider):
    folder, run_dir = started(tmp_path, provider)
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    first, written = COVENANT_MODULES[0], []

    def reply(context):
        if context["module_id"] != first:
            return "# Not a handoff"
        written.append(answer(context, routes))
        return written[-1]

    provider.answer = reply
    bridge.start(folder)
    assert status_of(folder)["state"] == "stopped"
    library = library_of(run_dir)
    assert list(library["runs"][run_dir.name]["modules"]) == [first]
    output = library["outputs"][f"{run_dir.name}/{first}.md"]
    assert output["sha256"] == hashlib.sha256(written[-1].encode()).hexdigest()


def test_a_finished_run_lists_each_handoff_once(tmp_path, provider):
    folder, run_dir = started(tmp_path, provider)
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    provider.answer = lambda context: answer(context, routes)
    bridge.start(folder)
    modules = library_of(run_dir)["runs"][run_dir.name]["modules"]
    assert tuple(modules) == tuple(sorted(COVENANT_MODULES))
    assert all(len(module["outputs"]) == 1 for module in modules.values())


def test_max_turns_and_output_limit_reach_the_paid_entry_point(tmp_path, monkeypatch):
    folder, value = job(tmp_path, max_turns=7)
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    bridge.write_json(folder / "review.json", bridge.review(folder))
    seen = {}

    def fake(manifest, directory, **kwargs):
        seen.update(kwargs, directory=directory)
        report = directory / "deliveries" / "fake" / "report.html"
        report.parent.mkdir(parents=True)
        report.write_text("synthetic seam")
        return report

    monkeypatch.setattr(bridge, "run_live_handoffs", fake)
    bridge.start(folder)
    assert seen["max_turns"] == 7 and seen["config"] == "sol-medium"
    assert seen["max_output_tokens"] == bridge.MAX_OUTPUT_TOKENS
    assert seen["rulings_root"] == folder.resolve()
    assert seen["directory"] == (Path(value["workspace"]) / "runs" / value["id"]).resolve()


def test_read_at_keeps_append_position(tmp_path):
    import os

    path = tmp_path / "log"
    path.write_bytes(b"one\ntwo\n")
    fd = os.open(path, os.O_RDWR)
    try:
        os.lseek(fd, 3, os.SEEK_SET)
        assert read_at(fd, 1, 7) == b"\n"
        assert os.lseek(fd, 0, os.SEEK_CUR) == 3
    finally:
        os.close(fd)


def test_windows_crlf_start_authorisation_is_valid(tmp_path):
    from deploy_workflow.model.adapter import check_ruling

    path = tmp_path / "start.md"
    path.write_bytes(
        b"lifts: live-provider-pause\r\nby: user\r\ndate: 2026-11-04\r\nconfigs: sol-medium\r\n"
    )
    assert check_ruling("sol-medium", path, rulings_root=tmp_path).path == path.resolve()


def test_a_release_failure_after_a_finished_run_is_shown_in_the_complete_message(
    tmp_path, provider, monkeypatch
):
    import warnings

    folder, _ = started(tmp_path, provider)

    def finishes(*args, **kwargs):
        warnings.warn("adapter release failed: stop failed: OSError", RuntimeWarning)

    monkeypatch.setattr(bridge, "run_live_handoffs", finishes)
    bridge.start(folder)
    status = status_of(folder)
    assert status["state"] == "complete"
    assert "adapter release failed: stop failed: OSError" in status["message"]


def test_a_release_note_on_a_multi_argument_stop_reaches_the_failed_status(
    tmp_path, provider, monkeypatch, capsys
):
    folder, _ = started(tmp_path, provider)

    def stops(*args, **kwargs):
        error = PermissionError(13, "Permission denied")
        error.add_note("adapter release also failed: stop failed: OSError")
        raise error

    monkeypatch.setattr(bridge, "run_live_handoffs", stops)
    monkeypatch.setattr(bridge.sys, "argv", ["bridge.py", "start", str(folder)])
    with pytest.raises(SystemExit):
        bridge.main()
    assert "adapter release also failed: stop failed: OSError" in status_of(folder)["message"]
    assert "adapter release also failed" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("error", "state"),
    [
        (RuntimeError("provider refused"), "stopped"),
        (OSError(32, "sharing violation"), "failed"),
        (KeyError("handoff"), "failed"),
    ],
)
def test_any_failure_after_a_paid_call_records_the_spend_and_the_no_retry_note(
    tmp_path, provider, monkeypatch, error, state
):
    """Hand-derived: one call settled USD 7.42 before the failure, so status.json must say
    "7.42" whatever the exception type; the bridge no longer writes a progress.json."""
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    folder, run_dir = started(tmp_path, provider)
    settled = {"usd": Decimal(0)}

    class Ledger:
        def __init__(self, cap, path):
            pass

        @property
        def spent(self):
            return settled["usd"]

    def pays_then_fails(*args, **kwargs):
        settled["usd"] = Decimal("7.42")
        raise error

    monkeypatch.setattr(bridge, "Budget", Ledger)
    monkeypatch.setattr(bridge, "run_live_handoffs", pays_then_fails)
    monkeypatch.setattr(bridge.sys, "argv", ["bridge.py", "start", str(folder)])
    try:
        bridge.main()
    except SystemExit:
        pass  # a failure other than a stop exits non-zero after recording its status
    status = status_of(folder)
    assert (status["state"], status["spent_usd"]) == (state, "7.42")
    assert "no automatic paid retry was made" in status["message"]
    assert not (run_dir / "progress.json").exists()


def test_an_unreadable_spend_ledger_is_never_shown_as_zero_and_hides_no_error(
    tmp_path, provider, monkeypatch
):
    """Expected: the original failure text survives, status.json says spent_usd "unknown" (left
    out, the UI would fall back to progress.json's stale "0") and that it may be above zero."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-0123456789")
    folder, _ = started(tmp_path, provider)

    class Locked:
        def __init__(self, cap, path):
            pass

        @property
        def spent(self):
            raise OSError("ledger locked")

    def fails(*args, **kwargs):
        raise OSError(5, "write failed for sk-test-secret-0123456789")

    monkeypatch.setattr(bridge, "Budget", Locked)
    monkeypatch.setattr(bridge, "run_live_handoffs", fails)
    monkeypatch.setattr(bridge.sys, "argv", ["bridge.py", "start", str(folder)])
    try:
        bridge.main()
    except SystemExit:
        pass
    status = status_of(folder)
    assert (status["state"], status["spent_usd"]) == ("failed", "unknown")
    assert "write failed for [redacted]" in status["message"]
    assert "sk-test-secret" not in json.dumps(status)
    assert "no automatic paid retry was made" in status["message"]
    assert "spend could not be read and may be above zero" in status["message"]


def ledger_that_locks(monkeypatch, settled: dict) -> None:
    """A Budget stand-in: reads settled["usd"], or raises once settled["locked"] is set."""

    class Ledger:
        def __init__(self, cap, path):
            pass

        @property
        def spent(self):
            if settled.get("locked"):
                raise OSError("ledger locked")
            return settled["usd"]

    monkeypatch.setattr(bridge, "Budget", Ledger)


@pytest.mark.parametrize(
    "case", [(RuntimeError("refused"), "stopped", None), (TypeError("bad record"), "failed", 2)]
)
def test_the_worker_exit_code_is_unchanged_by_recording_the_spend(
    tmp_path, provider, monkeypatch, case
):
    """Hand-derived: a stop returns normally (no SystemExit), any other failure exits 2 after
    start's own status, which main keeps: the message is start's, with the note and USD 1.25."""
    error, state, code = case
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    folder, _ = started(tmp_path, provider)
    ledger_that_locks(monkeypatch, {"usd": Decimal("1.25")})

    def fails(*args, **kwargs):
        raise error

    monkeypatch.setattr(bridge, "run_live_handoffs", fails)
    monkeypatch.setattr(bridge.sys, "argv", ["bridge.py", "start", str(folder)])
    exit_code = None
    try:
        bridge.main()
    except SystemExit as stop:
        exit_code = stop.code
    status = status_of(folder)
    assert (exit_code, status["state"], status["spent_usd"]) == (code, state, "1.25")
    assert status["message"].endswith(bridge.RETAINED_NOTE)
    assert str(error) in status["message"]


def test_an_interrupt_is_not_recorded_as_a_failure_and_leaves_the_running_status(
    tmp_path, provider, monkeypatch
):
    """Expected: KeyboardInterrupt is not an Exception; the bridge writes nothing, so the
    server's own "running" status stays for its exit handler to mark interrupted."""
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    folder, _ = started(tmp_path, provider)
    bridge.write_json(folder / "status.json", {"state": "running", "message": "Working"})
    ledger_that_locks(monkeypatch, {"usd": Decimal("0.50")})

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(bridge, "run_live_handoffs", interrupted)
    monkeypatch.setattr(bridge.sys, "argv", ["bridge.py", "start", str(folder)])
    with pytest.raises(KeyboardInterrupt):
        bridge.main()
    assert status_of(folder) == {"state": "running", "message": "Working"}


def test_a_finished_run_whose_ledger_cannot_be_read_says_unknown_not_its_last_progress(
    tmp_path, provider, monkeypatch
):
    """Hand-derived: the ledger held "2.00" before the final call, then cannot be read. The run
    still completes (its report exists); status.json says spent_usd
    "unknown" with the may-be-above-zero note, never the lower "2.00"."""
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    folder, _ = started(tmp_path, provider)
    settled = {"usd": Decimal("2.00")}
    ledger_that_locks(monkeypatch, settled)

    def finishes(*args, **kwargs):
        settled["locked"] = True

    monkeypatch.setattr(bridge, "run_live_handoffs", finishes)
    monkeypatch.setattr(bridge.sys, "argv", ["bridge.py", "start", str(folder)])
    bridge.main()
    status = status_of(folder)
    assert (status["state"], status["spent_usd"]) == ("complete", "unknown")
    assert status["message"].endswith(bridge.UNKNOWN_SPEND_NOTE)


def test_a_budget_stop_reports_reason_budget(tmp_path, provider, monkeypatch):
    """Hand key: sol-medium holds USD 5.73 per call. Cap 6 clears the first call; once that call
    has really spent about USD 3 (20,000 output tokens), the next hold passes the cap and the
    run stops on the budget with the first module's work retained."""
    folder, run_dir = started(tmp_path, provider, cap_usd="6")
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    provider.answer = lambda context: answer(context, routes)
    cheap = LiveAdapter.complete

    def expensive(self, request, **kwargs):
        reply = cheap(self, request, **kwargs)
        usage = replace(reply.usage, output_tokens=20000)
        return replace(reply, usage=usage, turn=replace(reply.turn, usage=usage))

    monkeypatch.setattr(LiveAdapter, "complete", expensive)
    bridge.start(folder)
    status = status_of(folder)
    assert (status["state"], status["reason"]) == ("stopped", "budget")
    logged = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert logged[-1]["event"] == "stopped" and logged[-1]["reason"] == "budget"
    assert (run_dir / f"{COVENANT_MODULES[0]}.md").is_file()


def resumed(folder, value, **extra):
    """Job B as `/api/runs/resume` stages it: A's context and sources under a new intake id."""
    new = folder.parent / ("web-" + "b" * 32)
    shutil.copytree(folder / "sources", new / "sources")
    shutil.copy(folder / "context.json", new / "context.json")
    bridge.write_json(
        new / "job.json", {**value, "id": new.name, "resume_of": folder.name, **extra}
    )
    return new


def stopped_after_the_first_module(tmp_path, provider):
    folder, run_dir = started(tmp_path, provider)
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    first = COVENANT_MODULES[0]
    provider.answer = lambda context: (
        answer(context, routes) if context["module_id"] == first else "# Not a handoff"
    )
    bridge.start(folder)
    assert status_of(folder)["state"] == "stopped"
    return folder, run_dir, request, routes


def test_a_resume_replays_accepted_handoffs_and_calls_only_the_rest(tmp_path, provider):
    folder, _, request, routes = stopped_after_the_first_module(tmp_path, provider)
    before = len(provider.calls)
    second = resumed(folder, request, cap_usd="50")
    result = bridge.review(second)
    assert result["resume_of"] == folder.name and result["retained_modules"] == ["CP-0"]
    bridge.write_json(second / "review.json", result)
    provider.answer = lambda context: answer(context, routes)
    bridge.start(second)
    called = [module for module, _, _ in provider.calls[before:]]
    assert called == list(COVENANT_MODULES[1:])
    assert status_of(second)["state"] == "complete"
    new_run = Path(request["workspace"]) / "runs" / second.name
    record = next(new_run.glob("delivery-*.json"))
    assert json.loads(record.read_text())["module_execution"]["CP-0"] == "retained-response-replay"


def stopped_after(tmp_path, provider, kept):
    """A covenant run whose provider answers `kept` modules and rejects the rest."""
    folder, _ = started(tmp_path, provider)
    request = json.loads((folder / "job.json").read_text())
    routes = bridge.launch(request, folder, tmp_path / "preview").layout.routes
    provider.answer = lambda context: (
        answer(context, routes) if context["module_id"] in kept else "# Not a handoff"
    )
    bridge.start(folder)
    assert status_of(folder)["state"] == "stopped"
    return folder, request, routes


def resume_calls(folder, request, routes, provider):
    """Review and Start a resume; the modules it called, its review and its Start status."""
    second = resumed(folder, request, cap_usd="50")
    result = bridge.review(second)
    bridge.write_json(second / "review.json", result)
    seen = {}

    def record(context):
        seen[context["module_id"]] = sorted(context["handoffs"])
        return answer(context, routes)

    provider.answer = record
    before = len(provider.calls)
    bridge.start(second)
    return [m for m, _, _ in provider.calls[before:]], result, status_of(second), seen


def test_a_resume_after_cp2_calls_the_rest_in_the_fresh_order_and_completes(tmp_path, provider):
    # Hand key: COVENANT order is CP-0, CP-1, CP-1A, CP-2, CP-4, CP-2D, CP-3C, CP-5.
    kept = {"CP-0", "CP-1", "CP-1A", "CP-2"}
    folder, request, routes = stopped_after(tmp_path, provider, kept)
    called, result, status, _ = resume_calls(folder, request, routes, provider)
    assert result["retained_modules"] == ["CP-0", "CP-1", "CP-1A", "CP-2"]
    assert called == ["CP-4", "CP-2D", "CP-3C", "CP-5"]
    assert status["state"] == "complete"


def test_a_resume_after_cp1a_runs_in_the_reviewed_order_and_cp4_sees_cp2(tmp_path, provider):
    folder, request, routes = stopped_after(tmp_path, provider, {"CP-0", "CP-1", "CP-1A"})
    called, result, status, seen = resume_calls(folder, request, routes, provider)
    assert called == ["CP-2", "CP-4", "CP-2D", "CP-3C", "CP-5"]
    assert result["modules"] == ["CP-0", "CP-1", "CP-1A", *called]
    assert "CP-2" in seen["CP-4"]
    assert status["state"] == "complete"


def accepted_response(run_dir, module="CP-0"):
    """CP-OS's record of the accepted answer: the response whose review has no issues."""
    (path,) = run_dir.glob(f"requests/{module}/*/1.response.md")
    return path


def test_a_changed_retained_handoff_is_refused_at_start(tmp_path, provider):
    folder, run_dir, request, _ = stopped_after_the_first_module(tmp_path, provider)
    second = resumed(folder, request)
    approved = bridge.review(second)
    assert approved["retained_modules"] == ["CP-0"]
    bridge.write_json(second / "review.json", approved)
    with accepted_response(run_dir).open("ab") as stream:
        stream.write(b"\n")
    before = len(provider.calls)
    with pytest.raises(ValueError, match="review is stale"):
        bridge.start(second)
    assert len(provider.calls) == before
    assert not (second / "start-authorization.md").exists()
    assert not (Path(request["workspace"]) / "runs" / second.name).exists()


def test_an_edited_copy_of_the_accepted_answer_neither_blocks_start_nor_is_replayed(
    tmp_path, provider
):
    folder, run_dir, request, routes = stopped_after_the_first_module(tmp_path, provider)
    recorded = accepted_response(run_dir).read_bytes()
    (run_dir / "CP-0.md").write_bytes(recorded.replace(b"One item", b"Two items"))
    second = resumed(folder, request)
    approved = bridge.review(second)
    assert approved["retained_modules"] == ["CP-0"]
    bridge.write_json(second / "review.json", approved)
    provider.answer = lambda context: answer(context, routes)
    before = len(provider.calls)
    bridge.start(second)
    assert status_of(second)["state"] == "complete"
    assert [m for m, _, _ in provider.calls[before:]] == list(COVENANT_MODULES[1:])
    new_run = Path(request["workspace"]) / "runs" / second.name
    assert (new_run / "retained" / "CP-0.md").read_bytes() == recorded


@pytest.mark.parametrize("verdict", [b"{not json", b"[]"])
def test_a_corrupt_verdict_is_not_offered_and_says_so(tmp_path, provider, verdict):
    folder, run_dir, request, _ = stopped_after_the_first_module(tmp_path, provider)
    (fp,) = (run_dir / "requests" / "CP-0").iterdir()
    (fp / "1.review.json").write_bytes(verdict)
    result = bridge.review(resumed(folder, request))
    assert result["retained_modules"] == []
    assert result["retained_note"] == (
        "Retained work stops before Source readiness: its record in the stopped run could not "
        "be read."
    )


@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0, reason="needs a mode-000 file to be unreadable"
)
def test_an_unreadable_verdict_is_not_offered_and_says_so(tmp_path, provider):
    folder, run_dir, request, _ = stopped_after_the_first_module(tmp_path, provider)
    (fp,) = (run_dir / "requests" / "CP-0").iterdir()
    verdict = fp / "1.review.json"
    verdict.chmod(0)
    try:
        result = bridge.review(resumed(folder, request))
    finally:
        verdict.chmod(0o644)
    assert result["retained_modules"] == []
    assert result["retained_note"] == (
        "Retained work stops before Source readiness: its record in the stopped run could not "
        "be read."
    )


def test_a_module_the_stopped_run_never_reached_says_so(tmp_path, provider):
    folder, _, request, _ = stopped_after_the_first_module(tmp_path, provider)
    result = bridge.review(resumed(folder, request))
    assert result["retained_modules"] == ["CP-0"]
    assert result["retained_note"] == (
        "Retained work stops before Canonical data foundation: the stopped run did not reach it."
    )


def test_a_source_added_after_the_stop_ends_the_retained_work_and_says_why(tmp_path, provider):
    folder, _, request, _ = stopped_after_the_first_module(tmp_path, provider)
    (folder / "sources" / "late.txt").write_text("Debt was 900 after the stop.")
    result = bridge.review(resumed(folder, request))
    assert result["retained_modules"] == []
    assert result["retained_note"] == (
        "Retained work stops before Source readiness: its sources or context changed since the "
        "stopped run."
    )


def test_a_changed_context_ends_the_retained_work(tmp_path, provider):
    folder, _, request, _ = stopped_after_the_first_module(tmp_path, provider)
    context = json.loads((folder / "context.json").read_text())
    context["run"]["reporting_currency"] = "EUR"
    (folder / "context.json").write_text(json.dumps(context))
    assert bridge.review(resumed(folder, request))["retained_modules"] == []


def test_a_method_change_since_the_stop_ends_the_retained_work(tmp_path, provider, monkeypatch):
    folder, _, request, _ = stopped_after_the_first_module(tmp_path, provider)
    original = test_cpos_launch.cpos_launch._instructions
    monkeypatch.setattr(
        test_cpos_launch.cpos_launch,
        "_instructions",
        lambda run, module, routes, **kw: (
            original(run, module, routes, **kw) + b"\nMethod revision 2.\n"
        ),
    )
    result = bridge.review(resumed(folder, request))
    assert result["retained_modules"] == []
    assert result["retained_note"].endswith("its instructions changed since the stopped run.")


def test_a_different_model_since_the_stop_ends_the_retained_work(tmp_path, provider):
    folder, _, request, _ = stopped_after_the_first_module(tmp_path, provider)
    reviewed = json.loads((folder / "review.json").read_text())
    reviewed["model"] = "another-model"
    (folder / "review.json").write_text(json.dumps(reviewed))
    result = bridge.review(resumed(folder, request))
    assert result["retained_modules"] == []
    assert result["retained_note"].endswith("the stopped run used a different model setting.")


@pytest.mark.parametrize("raw", [None, b"{not json", b"[]"])
def test_an_unreadable_model_setting_of_the_stopped_run_ends_the_retained_work(
    tmp_path, provider, raw
):
    folder, _, request, _ = stopped_after_the_first_module(tmp_path, provider)
    if raw is None:
        (folder / "review.json").unlink()
    else:
        (folder / "review.json").write_bytes(raw)
    result = bridge.review(resumed(folder, request))
    assert result["retained_modules"] == []
    assert result["retained_note"] == (
        "Retained work stops before Source readiness: the stopped run's model setting could "
        "not be read."
    )


def test_a_source_changed_inside_start_is_refused_before_any_call(tmp_path, provider, monkeypatch):
    folder, _ = started(tmp_path, provider)
    calls = []
    real = bridge.read_job

    def edit_after_the_check(directory):
        calls.append(directory)
        result = real(directory)
        if len(calls) == 2:
            (folder / "sources" / "annual.txt").write_text("Net sales were 900.")
        return result

    monkeypatch.setattr(bridge, "read_job", edit_after_the_check)
    with pytest.raises(ValueError, match="review is stale"):
        bridge.start(folder)
    assert provider.calls == [] and not (folder / "start-authorization.md").exists()


@pytest.mark.parametrize("bad", ["../intake/web-" + "a" * 32, "web-" + "A" * 32, "tdg-003", 7])
def test_a_malformed_resume_of_is_refused(tmp_path, bad):
    folder, _ = job(tmp_path, resume_of=bad)
    with pytest.raises(ValueError, match="resume_of"):
        bridge.review(folder)


def test_a_resume_with_nothing_accepted_retains_nothing(tmp_path, provider):
    folder, _ = started(tmp_path, provider)
    provider.answer = lambda context: "# Not a handoff"
    bridge.start(folder)
    request = json.loads((folder / "job.json").read_text())
    result = bridge.review(resumed(folder, request))
    assert result["ok"] and result["retained_modules"] == []


def test_a_resume_whose_run_folder_is_gone_is_refused(tmp_path, provider):
    folder, run_dir, request, _ = stopped_after_the_first_module(tmp_path, provider)
    second = resumed(folder, request)
    shutil.rmtree(run_dir)
    with pytest.raises(ValueError, match="has no retained work in the workspace"):
        bridge.review(second)


EXPECTATION_KEYS = {"issue_classification", "documents", "expectations", "counted", "without"}


def test_review_adds_the_expectations_to_its_unchanged_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    folder, _ = job(tmp_path)
    result = bridge.review(folder)
    assert EXPECTATION_KEYS <= set(result)
    assert result["issue_classification"] == ""  # The fixture context does not state one.
    assert {d["source"] for d in result["documents"]} == {"annual.txt", "filings/notes.md"}
    ids = [item["id"] for item in result["expectations"]]
    assert len(ids) == len(set(ids))
    assert result["counted"] == [i["id"] for i in result["expectations"] if i["counted"]]
    assert result["without"] == {}  # Legal documents are declared executed: nothing will refuse.


def test_review_offers_run_without_for_a_declared_none(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    folder, _ = job(tmp_path)
    context = json.loads((folder / "context.json").read_text())
    context["attachments"]["legal_documents"] = "none"
    context["identity"]["issue_classification"] = "investment_grade"
    (folder / "context.json").write_text(json.dumps(context))
    result = bridge.review(folder)
    assert result["issue_classification"] == "investment_grade"
    assert result["without"] == {"CP-4": ["CP-4"]}
    assert "CP-4:cp4-declared-none" in result["counted"]
    assert not (folder / "start-authorization.md").exists()


def test_review_id_does_not_cover_the_expectations(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    folder, value = job(tmp_path)
    first = bridge.review(folder)
    prepared = bridge.launch(value, folder, tmp_path / "again")
    assert prepared.expectations and prepared.documents
    bare = replace(prepared, expectations=(), documents=())
    assert bridge.review_id(value, first["engine_revision"], bare) == first["review_id"]


def test_the_fake_engine_bridge_returns_the_same_review_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    folder, _ = job(tmp_path)
    real = bridge.review(folder)
    fake = subprocess.run(
        [
            sys.executable,
            str(ROOT / "apps/issuer-library/designs/fake_engine/bridge.py"),
            "review",
            str(folder),
        ],
        env={**os.environ, "CHECK_ROOT": str(ROOT)},
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert fake.returncode == 0, fake.stderr
    review = json.loads(fake.stdout)
    assert set(review) == set(real) and EXPECTATION_KEYS <= set(review)
    assert review["expectations"] == real["expectations"]
