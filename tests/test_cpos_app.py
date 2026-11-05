"""Offline CP-OS intake/transport regressions; no provider or analytical success claims."""

import hashlib
import importlib.util
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import o2_case
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

from deploy_vii.contracts import Fact, Module, View
from deploy_vii.preparation import load_pack
from deploy_workflow.cpos_handoffs import deliver, prompt_messages, retain, transport
from deploy_workflow.model.turn import Message
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
    provider.answer = lambda context: answer(context, routes)
    bridge.start(folder)
    assert tuple(call[0] for call in provider.calls) == COVENANT_MODULES
    assert {call[1] for call in provider.calls} == {"sol-medium"}
    status = status_of(folder)
    assert status["state"] == "complete" and Decimal(status["spent_usd"]) > 0
    assert "Automated checks only" in status["message"]
    report = next(run_dir.glob("deliveries/*/report.html"))
    assert ISSUER in report.read_text(encoding="utf-8")
    manifest = json.loads((report.parent / "delivery.json").read_text())
    assert {"report.html", "view.json", "CP-0.md"} <= set(manifest["files"])
    assert json.loads((run_dir / "progress.json").read_text())["module"] == COVENANT_MODULES[-1]
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


class RetainedStore:
    def __init__(self, run_dir, module):
        self.directory = run_dir / "execution"
        self.module = module

    def read(self):
        return SimpleNamespace(
            heads=[
                SimpleNamespace(
                    module_id=self.module.module_id, result_sha256=self.module.content_hash()
                )
            ]
        )

    def head_module(self, head):
        return self.module


def test_markdown_handoff_is_consumed_and_delivery_preserves_exact_values(tmp_path):
    _, run_dir = o2_case.stage(tmp_path / "case")
    pack = load_pack(run_dir / "pack")
    module = Module(
        run_id=pack.run.run_id,
        issuer_id=pack.run.issuer_id,
        as_of=pack.run.as_of,
        module_id="CP-1",
        status="accepted",
        facts=(
            Fact(
                fact_id="transport-check.zero",
                label="Zero amount",
                table_id="T4.4",
                row_id="zero",
                field="amount",
                amount=Decimal("0.00"),
                unit="currency",
                currency="USD",
                period="FY2024",
            ),
        ),
    )
    store = RetainedStore(run_dir, module)
    original = (Message(role="system", text="Existing instructions"),)
    binding = SimpleNamespace(
        module_id="CP-2",
        step_id="credit_synthesis",
        inputs=(SimpleNamespace(sha256=module.content_hash()),),
    )
    with transport():
        messages = prompt_messages(store, binding, original)
    assert messages[0] == original[0] and "0.00" in messages[-1].text
    files = retain(store)
    assert "## Sources" in files["CP-1"].read_text()
    deliver(store, run_dir / "delivery")
    view = View.model_validate_json((run_dir / "delivery/view.json").read_bytes())
    fact = next(m for m in view.modules if m.module_id == "CP-1").facts[0]
    assert str(fact.amount) == "0.00" and fact.currency == "USD" and fact.period == "FY2024"
    files["CP-1"].write_text("changed handoff")
    with pytest.raises(ValueError, match="handoff changed"):
        deliver(store, run_dir / "tampered")


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
