"""live_check: refusals happen before anything exists, and live_evidence follows the answer key."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
from contextlib import nullcontext
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESIGNS = ROOT / "apps/issuer-library/designs"
sys.path.insert(0, str(DESIGNS))
spec = importlib.util.spec_from_file_location("live_check", DESIGNS / "live_check.py")
live_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_check)
from faults import Faults

KEY_NAMES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "COPILOT_GITHUB_TOKEN")
NOT_PROVIDER = ("GH_TOKEN", "GITHUB_TOKEN")


def test_provider_keys_are_the_adapters_key_variables() -> None:
    from deploy_workflow.model.adapter import KEY_VARIABLES

    assert set(live_check.PROVIDER_KEYS) == set(KEY_VARIABLES.values())


WITH_KEY = {"OPENAI_API_KEY": "sk-test-not-a-real-key"}


def refuse(
    tmp_path: Path, *args: str, extra: dict[str, str] = WITH_KEY, keep: bool = False
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in KEY_NAMES + NOT_PROVIDER}
    env |= {"FW_PYTHON": sys.executable, "ISSUER_LIBRARY_BINARY": str(tmp_path / "missing-binary")}
    env |= extra
    out = tmp_path / "out"
    done = subprocess.run(
        [sys.executable, str(DESIGNS / "live_check.py"), *args, "--out", str(out)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert keep or not out.exists()
    assert "sk-test-not-a-real-key" not in done.stdout + done.stderr
    return done


BAD_CAPS = [(("--cap", c), WITH_KEY, "--cap") for c in ("0", "-1", "nan", "inf", "-inf", "abc")]


@pytest.mark.parametrize(
    ("args", "extra", "word"),
    [
        ((), WITH_KEY, "--cap"),
        *BAD_CAPS,
        (("--cap", "5"), {}, "provider key"),
        (("--cap", "5"), {"GH_TOKEN": "gh-test-token-123"}, "provider key"),
        (("--cap", "5", "--minutes", "0.5"), WITH_KEY, "--minutes"),
        (("--rehearse",), {}, "--cap"),  # a rehearsal needs no key, but a cap
    ],
)
def test_refuses_with_one_line_before_anything_exists(
    tmp_path: Path, args: tuple[str, ...], extra: dict[str, str], word: str
) -> None:
    done = refuse(tmp_path, *args, extra=extra)
    assert done.returncode == 2 and word in done.stderr and len(done.stderr.splitlines()) == 1


@pytest.mark.parametrize(
    "make", [lambda p: p.write_text("1"), lambda p: (p.mkdir(), (p / "x").write_text("1"))]
)
def test_refuses_an_out_that_is_a_file_or_a_used_folder(tmp_path: Path, make) -> None:
    make(tmp_path / "out")
    done = refuse(tmp_path, "--cap", "5", keep=True)
    assert done.returncode == 2 and "--out" in done.stderr and (tmp_path / "out").exists()
    out = tmp_path / "out"
    assert (out if out.is_file() else out / "x").read_text() == "1"


def test_stop_group_kills_the_whole_group() -> None:
    server = subprocess.Popen(["sh", "-c", "sleep 60 & sleep 60 & wait"], start_new_session=True)
    assert live_check.group_alive(server)
    assert live_check.stop_group(server) is None
    assert not live_check.group_alive(server)


def test_spend_of_sums_the_ledger_and_counts_unknown_cost_and_torn_rows(tmp_path: Path) -> None:
    intake = tmp_path / "intake/web-1"
    intake.mkdir(parents=True)
    (intake / "status.json").write_text(json.dumps({"spent_usd": "0.25"}))
    live = tmp_path / "runs/web-1/live"
    live.mkdir(parents=True)
    rows = [{"settled_usd": "0.10"}, {"settled_usd": "0.20"}]
    (live / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert live_check.spend_of(tmp_path) == ("0.25", Decimal("0.30"), 0)
    rows = [{"settled_usd": "0.05"}, {"settled_usd": None, "cost_status": "unknown"}]
    (live / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + '{"settled_u')
    assert live_check.spend_of(tmp_path) == ("0.25", Decimal("0.05"), 2)


def test_check_run_and_spend_of_read_the_same_intake_status(tmp_path: Path) -> None:
    for name, spent in (("web-1", "1"), ("web-2", "2")):
        (tmp_path / "intake" / name).mkdir(parents=True)
        (tmp_path / "intake" / name / "status.json").write_text(json.dumps({"spent_usd": spent}))
    last = live_check.intake_status(tmp_path)
    assert last and last.parent.name == "web-2" and live_check.spend_of(tmp_path)[0] == "2"


def test_stop_group_names_a_server_that_does_not_lead_its_group() -> None:
    child = subprocess.Popen(["sleep", "30"])
    message = live_check.stop_group(child)
    assert child.poll() is not None and message and "lead" in message


def test_watchdog_stops_the_group_when_its_pipe_closes() -> None:
    server = subprocess.Popen(["sh", "-c", "sleep 60 & sleep 60 & wait"], start_new_session=True)
    dog = live_check.arm_watchdog(server)
    assert dog.stdin and live_check.group_alive(server)
    dog.stdin.close()  # what the kernel does when live_check dies by any means
    for _ in range(100):
        if not live_check.group_alive(server):
            break
        time.sleep(0.1)
    assert not live_check.group_alive(server)
    dog.kill()
    dog.wait()


def review(modules: str, ids: list[str]) -> list[str]:
    args = argparse.Namespace(config="sol-medium", cap=Decimal(10), modules=modules)
    rows = {"Model": "openai gpt-6.1-sol · medium", "Maximum spend": "USD 10"}
    page = SimpleNamespace(evaluate=lambda _script: {"rows": rows, "ids": ids})
    return live_check.check_review(page, args)


def test_review_for_the_answer_key_case_must_list_exactly_its_modules() -> None:
    assert review("CP-1 CP-1A", ["CP-0", "CP-1", "CP-1A"]) == []
    assert review("CP-1 CP-1A", ["CP-0", "CP-1", "CP-1A", "CP-2"])
    assert review("CP-1 CP-1A", ["CP-0", "CP-1"])
    assert review("CP-1", ["CP-0", "CP-1", "CP-2"]) == []  # other cases: every requested module
    assert review("CP-1 CP-3", ["CP-0", "CP-1"])


def test_answer_key_case_follows_the_request_not_the_run() -> None:
    assert live_check.is_key_case(argparse.Namespace(config="sol-medium", modules="CP-1  CP-1A"))
    assert not live_check.is_key_case(argparse.Namespace(config="sol-high", modules="CP-1 CP-1A"))
    assert not live_check.is_key_case(argparse.Namespace(config="sol-medium", modules="CP-1"))


def test_answer_key_env_never_optimises_asserts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONOPTIMIZE", "1")
    assert "PYTHONOPTIMIZE" not in live_check.key_env()


CP0 = "CP-0 body\n"
MODS = {"CP-0", "CP-1", "CP-1A"}


def make_run(
    tmp_path: Path,
    rows: list[dict[str, str]],
    cp1: str | None = None,
    execution: str = "live-provider",
) -> Path:
    run = tmp_path / "run"
    (run / "live").mkdir(parents=True)
    (run / "live/calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    d0 = hashlib.sha256(CP0.encode()).hexdigest()
    cp1 = cp1 if cp1 is not None else f"Net sales 7,940 and cash 6,261. {d0}\n"
    d1 = hashlib.sha256(cp1.encode()).hexdigest()
    (run / "CP-0.md").write_text(CP0)
    (run / "CP-1.md").write_text(cp1)
    (run / "CP-1A.md").write_text(f"{d0} {d1}\n")
    (run / "completed-x.json").write_text(
        json.dumps({"execution": execution, "module_execution": dict.fromkeys(MODS, execution)})
    )
    return run


def row(module: str = "CP-1", **changes: str) -> dict[str, str]:
    base = {
        "module_id": module,
        "requested_model": "gpt-6.1-sol",
        "reported_model": "gpt-6.1-sol",
        "config_id": "sol-medium",
        "request_id": "resp_1",
        "settled_usd": "0.50",
    }
    return base | changes


def rows3(**changes: str) -> list[dict[str, str]]:
    return [row(m, **({"settled_usd": "0.30"} | changes)) for m in sorted(MODS)]


def evidence(run: Path, cap: str = "5", spent: str = "0.90", modules=frozenset(MODS), config=""):
    return live_check.live_evidence(run, Decimal(cap), spent, set(modules), config)


def test_live_evidence_clean(tmp_path: Path) -> None:
    run = make_run(tmp_path, rows3())
    assert evidence(run) == []
    assert evidence(run, spent="0.9000", config="sol-medium") == []


@pytest.mark.parametrize(
    ("rows", "kwargs", "word"),
    [
        (rows3(reported_model="other"), {}, "reported"),
        (rows3(requested_model="cheap", reported_model="cheap"), {}, "model"),
        (rows3(config_id="sol-high"), {"config": "sol-medium"}, "config"),
        ([row(m, request_id="", settled_usd="0.30") for m in sorted(MODS)], {}, "request_id"),
        (rows3(), {"cap": "0.89"}, "cap"),
        (rows3(settled_usd="0"), {"spent": "0"}, "spend"),
        (rows3(), {"spent": "0.99"}, "status"),
        (rows3(), {"modules": MODS | {"CP-2"}}, "modules"),
    ],
)
def test_live_evidence_faults(tmp_path: Path, rows, kwargs, word: str) -> None:
    found = evidence(make_run(tmp_path, rows), **kwargs)
    assert found and any(word in f for f in found)


def test_live_evidence_requires_live_execution_and_upstream_digests(tmp_path: Path) -> None:
    replay = evidence(make_run(tmp_path, rows3(), execution="offline-replay"))
    assert any("execution" in f for f in replay)
    run = tmp_path / "b"
    run.mkdir()
    unchained = evidence(make_run(run, rows3(), cp1="Net sales 7,940 and cash 6,261.\n"))
    assert any("CP-0" in f for f in unchained)


def test_live_evidence_requires_filed_literals(tmp_path: Path) -> None:
    d0 = hashlib.sha256(CP0.encode()).hexdigest()
    run = make_run(tmp_path, rows3(), cp1=f"Net sales 7,940 only. {d0}\n")
    found = evidence(run)
    assert len(found) == 1 and "6,261" in found[0]


def test_unknown_cost_row_is_a_fault_not_a_crash(tmp_path: Path) -> None:
    rows = [*rows3()[:2], row("CP-1A", settled_usd=None, cost_status="unknown")]
    found = evidence(make_run(tmp_path, rows), spent="0.60")
    assert any("unknown" in f for f in found)


def test_module_execution_must_name_exactly_the_accepted_modules(tmp_path: Path) -> None:
    run = make_run(tmp_path, rows3())
    record = next(run.glob("completed-*.json"))
    record.write_text(
        json.dumps({"execution": "live-provider", "module_execution": {"CP-0": "live-provider"}})
    )
    assert any("module_execution" in f for f in evidence(run))


def test_answer_key_names_the_return_code_of_a_runner_with_no_stderr(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FW_PYTHON", sys.executable)
    killed = subprocess.CompletedProcess([], -9, "", "")
    monkeypatch.setattr(live_check.subprocess, "run", lambda *a, **k: killed)
    found = live_check.answer_key(tmp_path, Decimal(5))
    assert len(found) == 1 and "-9" in found[0]


def test_a_failure_before_the_signal_keeps_its_kind(monkeypatch, tmp_path) -> None:
    bc = SimpleNamespace(FAULTS=Faults(), results=[], secrets=list, scan_server_logs=lambda: None)

    def walk_then_signal(bc, args, out, summary, held) -> None:
        bc.FAULTS.add("live", "exception", "TimeoutError: before the signal")
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(1)

    saved = {s: signal.getsignal(s) for s in live_check.HALTING}
    monkeypatch.setitem(sys.modules, "browser_check", bc)
    monkeypatch.setattr(live_check, "run_walk", walk_then_signal)
    monkeypatch.setattr(os, "environ", {"FW_PYTHON": "x", "ISSUER_LIBRARY_BINARY": __file__})
    try:
        live_check.main(["--cap", "1", "--rehearse", "--out", str(tmp_path / "o")])
    finally:
        for sig, handler in saved.items():
            signal.signal(sig, handler)
    assert [f.kind for f in bc.FAULTS.items] == ["exception", "interrupted"]


A_LIVE = ROOT / "cases/live-tdg-fy2024/a-live"


# R-SB2-7 ruling 5 retired the Stage 2 refusal of --accept-limitations; see the parse test below.


def test_case_defaults_come_from_the_frozen_case_and_missing_files_refuse(tmp_path: Path) -> None:
    case = live_check.load_case(str(A_LIVE))
    assert case["case"]["cap_usd"] == "25" and len(case["files"]) == 5
    done = refuse(tmp_path, "--case", str(tmp_path / "nope"), "--rehearse")
    assert done.returncode == 2 and "case.json" in done.stderr


def test_forecast_against_outcome_reports_every_disagreement(tmp_path: Path) -> None:
    (tmp_path / "CP-0.md").write_text(
        "| CP-0 — source | READY |\n| CP-1 — figures | READY_WITH_LIMITATIONS |\n"
    )
    (tmp_path / "CP-1.md").write_text("# CP-1\n")
    (tmp_path / "CP-2.md").write_text("# CP-2\n")  # accepted, states no status
    forecast = {"CP-0": "ready", "CP-1": "ready", "CP-2": "will_refuse", "CP-4": "will_refuse"}
    found, did = live_check.outcome_faults(forecast, tmp_path)
    assert found == [
        "CP-1: forecast ready, run did limited (READY_WITH_LIMITATIONS in CP-0 handoff)",
        "CP-2: forecast will_refuse, run did unconfirmed (accepted, no status stated)",
        "CP-4: forecast will_refuse, run did not_reached (no handoff)",
    ]
    assert did["CP-4"] == "not_reached (no handoff)"


def test_forecast_takes_the_worst_item_per_module() -> None:
    items = [{"scope": "CP-4", "outcome": "limited"}, {"scope": "CP-4", "outcome": "will_refuse"}]
    assert live_check.forecast_of(items, ["CP-0", "CP-4"]) == {
        "CP-0": "ready",
        "CP-4": "will_refuse",
    }


def test_a_module_that_never_ran_or_states_no_status_never_agrees(tmp_path: Path) -> None:
    (tmp_path / "CP-0.md").write_text("# CP-0\n")
    (tmp_path / "CP-3C.md").write_text("# CP-3C\nNo status line.\n")
    found, did = live_check.outcome_faults({"CP-4": "will_refuse", "CP-3C": "limited"}, tmp_path)
    assert [f.split(":")[0] for f in found] == ["CP-4", "CP-3C"]
    assert did["CP-4"].startswith("not_reached") and did["CP-3C"].startswith("unconfirmed")
    refused, _ = live_check.outcome_faults({"CP-4": "will_refuse"}, tmp_path, refused="CP-4")
    assert refused == []  # the module the run stopped at did refuse
    (tmp_path / "CP-4.md").write_text("| CP-4 — legal | BLOCKED |\n")
    assert live_check.outcome_faults({"CP-4": "will_refuse"}, tmp_path)[0] == []


def test_the_status_table_is_the_back_tests() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    import expectations_backtest as backtest

    assert live_check.handoff_outcome["STATUS"] is not None
    assert backtest.verdict("ready", "unconfirmed") == "not testable"
    assert backtest.verdict("will_refuse", "not_reached") == "not testable"


def test_shown_spend_matches_exactly() -> None:
    ok = live_check.spend_line_ok
    assert ok("Recorded spend: USD 1.2 of a USD 25 cap", "1.2")
    assert ok("Recorded spend: USD 1.2", "1.2")
    assert not ok("Recorded spend: USD 1.23 of a USD 25 cap", "1.2")
    assert not ok("Recorded spend: USD 1.2 of a USD 25 cap and more", "1.2")


def test_case_literals_are_checked_with_their_sources() -> None:
    literals = [{"text": "7,940", "source": "10-K p. 26"}, {"text": "9,999", "source": "10-K p. 1"}]
    assert live_check.literal_faults("net sales 7,940", literals) == [
        "report lacks frozen literal 9,999 (10-K p. 1)"
    ]


def _workspace(tmp_path: Path, *, delivered: bytes = b"# CP-0\n") -> tuple[Path, Path, dict]:
    ws = tmp_path / "ws"
    intake, run = ws / "intake/web-1", ws / "runs/web-1"
    (run / "instructions").mkdir(parents=True)
    (run / "deliveries/d1").mkdir(parents=True)
    intake.mkdir(parents=True)
    (intake / "status.json").write_text("{}")
    (intake / "start-authorization.md").write_text("by: user\n")
    (run / "workflow.json").write_text("{}")
    (run / "instructions/CP-0.md").write_text("x")
    (run / "CP-0.md").write_text("# CP-0\n")
    (run / "completed-1.json").write_text("{}")
    for name in live_check.BUNDLE:
        (run / "deliveries/d1" / name).write_text("x")
    (run / "deliveries/d1/CP-0.md").write_bytes(delivered)
    review = {
        "modules": ["CP-0"],
        "review_id": "r1",
        "issue_classification": "high_yield",
        "documents": [],
        "expectations": [],
        "counted": [],
        "without": {},
    }
    return ws, run, review


def _args(tmp_path: Path) -> SimpleNamespace:
    context = tmp_path / "context.json"
    context.write_text("{}")
    return SimpleNamespace(case_data={"context_path": context})


def test_required_outputs_pass_and_say_stage_2_records_are_not_applicable(tmp_path, capsys) -> None:
    ws, run, review = _workspace(tmp_path)
    assert live_check.required_outputs(_args(tmp_path), ws, run, review, "") == []
    out = capsys.readouterr().out
    assert "expectations.json: not applicable before Stage 2" in out
    assert "context.json: not applicable before Stage 2" in out
    assert "start receipt accepted ids: not applicable before Stage 2" in out


def test_required_outputs_find_a_changed_delivered_handoff_and_stage_2_mismatches(tmp_path) -> None:
    ws, run, review = _workspace(tmp_path, delivered=b"# changed\n")
    (run / "context.json").write_text("{other}")
    (run / "expectations.json").write_text(json.dumps({"review_id": "r1"}))
    found = live_check.required_outputs(_args(tmp_path), ws, run, review, "")
    assert "delivered CP-0.md differs from the accepted handoff" in found
    assert "run context.json is not byte-identical to the case context" in found
    assert "expectations.json differs from the approved review" in found


def test_a_stopped_run_still_has_its_folder_checked(tmp_path, capsys) -> None:
    ws, run, review = _workspace(tmp_path)
    for path in [*(run / "deliveries/d1").iterdir(), run / "completed-1.json"]:
        path.unlink()
    (run / "deliveries/d1").rmdir()
    (run / "instructions/CP-0.md").unlink()
    found = live_check.required_outputs(_args(tmp_path), ws, run, review, "Stopped: CP-2")
    assert found == ["instructions/CP-0.md missing"]
    assert "expectations.json: not applicable before Stage 2" in capsys.readouterr().out


class _Bc:
    def __init__(self) -> None:
        self.notes: list[tuple[bool, str]] = []

    def note(self, ok: bool, what: str, fault: bool = True, kind: str = "check") -> None:
        self.notes.append((ok, what))


def _case_args(tmp_path: Path, counted: int) -> SimpleNamespace:
    expected = {"ordered_modules": ["CP-0"], "modules": {}, "counted_total": counted}
    return SimpleNamespace(case_data={"expected-outcomes": expected})


def test_case_outcomes_names_a_missing_review_and_a_counted_total_mismatch(tmp_path) -> None:
    ws, _, review = _workspace(tmp_path)
    bc, summary = _Bc(), {}
    live_check.case_outcomes(bc, _case_args(tmp_path, 0), ws, summary)
    assert any("no review.json" in what for ok, what in bc.notes if not ok)
    (ws / "intake/web-1/review.json").write_text(json.dumps(review | {"counted": ["a"]}))
    bc = _Bc()
    live_check.case_outcomes(bc, _case_args(tmp_path, 0), ws, summary)
    assert any("review counts 1 items, frozen 0" in what for ok, what in bc.notes if not ok)


def _bc(calls: list) -> SimpleNamespace:
    def attempt(name, browser, action) -> None:
        calls.append(name)
        action()

    return SimpleNamespace(
        NOT_APPLICABLE="not applicable: repo-store key",
        FAULTS=SimpleNamespace(add=lambda *a, **k: None, items=[]),
        NOT_EXERCISABLE=["chromium: Run activity events: not exercisable on this fixture: x"],
        engine_options=lambda: {"chromium": {}, "firefox": {"executable_path": "f"}},
        SignedBrowser=lambda raw: SimpleNamespace(close=lambda: calls.append("closed")),
        attempt=attempt,
        single_run_walk=lambda browser, name, port, ws: calls.append(f"walk {name} {port}"),
        note=lambda ok, what, fault=True, kind="check": calls.append(f"note {ok} {what}"),
    )


def test_a_case_run_is_followed_by_the_single_run_walk_in_each_engine(tmp_path: Path) -> None:
    calls: list = []
    launched = []
    driver = SimpleNamespace(
        chromium=SimpleNamespace(launch=lambda **o: launched.append(("chromium", o))),
        firefox=SimpleNamespace(launch=lambda **o: launched.append(("firefox", o))),
    )
    summary: dict = {"run_id": "web-1"}
    live_check.single_run_walks(_bc(calls), driver, tmp_path, summary, 41234)
    assert calls == [
        "chromium-single-run",
        "walk chromium 41234",
        "closed",
        "firefox-single-run",
        "walk firefox 41234",
        "closed",
    ]
    assert launched == [("chromium", {}), ("firefox", {"executable_path": "f"})]
    walk = summary["real_workspace_walk"]
    assert walk["repo_store_counts"] == "not applicable: repo-store key"
    assert "not exercisable on this fixture" in walk["not_exercisable"][0]


def test_an_incomplete_run_records_the_walk_as_not_run(tmp_path: Path) -> None:
    calls: list = []
    summary: dict = {"run_id": None}
    live_check.single_run_walks(_bc(calls), SimpleNamespace(), tmp_path, summary, 41234)
    assert calls == [] and summary["real_workspace_walk"] == "not run: the run did not complete"


def test_a_walk_that_could_not_exercise_a_check_is_a_fault_outside_the_fixture(tmp_path) -> None:
    calls: list = []
    bc = _bc(calls)
    faults: list = []
    bc.FAULTS = SimpleNamespace(add=lambda *a, **k: faults.append(a), items=faults)
    live_check.single_run_walks(
        bc,
        SimpleNamespace(
            chromium=SimpleNamespace(launch=lambda **o: None),
            firefox=SimpleNamespace(launch=lambda **o: None),
        ),
        tmp_path,
        {"run_id": "web-1"},
        41234,
    )
    assert faults and faults[0][1] == "missing" and "not exercisable" in faults[0][2]


def test_a_launch_failure_is_recorded_and_the_other_engine_still_walks(tmp_path: Path) -> None:
    calls: list = []
    bc, faults = _bc(calls), []
    bc.FAULTS = SimpleNamespace(add=lambda *a, **k: faults.append(a), items=faults)

    def missing(**options) -> None:
        raise RuntimeError("Executable doesn't exist at /nowhere")

    driver = SimpleNamespace(
        chromium=SimpleNamespace(launch=missing),
        firefox=SimpleNamespace(launch=lambda **o: None),
    )
    summary: dict = {"run_id": "web-1"}
    live_check.single_run_walks(bc, driver, tmp_path, summary, 41234)
    failed = [f for f in faults if f[0] == "chromium-single-run"]
    assert len(failed) == 1 and failed[0][1] == "exception"
    assert "RuntimeError" in failed[0][2] and "Executable doesn't exist" in failed[0][2]
    assert any(c.startswith("note False chromium-single-run") for c in calls)
    assert "walk firefox 41234" in calls and "walk chromium 41234" not in calls
    assert summary["real_workspace_walk"]["engines"] == ["chromium", "firefox"]


def test_the_server_is_started_on_a_free_port_not_a_fixed_one(monkeypatch, tmp_path) -> None:
    walked = []
    process = SimpleNamespace(pid=0)
    bc = SimpleNamespace(
        serve=lambda *a, **k: pytest.fail("a fixed port was passed to bc.serve"),
        serve_free=lambda ws, engine, key=None, extra=None: (process, 41234),
        engine_options=lambda: {"chromium": {}},
        SignedBrowser=lambda raw: SimpleNamespace(close=lambda: None),
        attempt=lambda name, browser, action: action(),
        FAULTS=SimpleNamespace(add=lambda *a, **k: None),
    )

    driver = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **o: None))
    playwright = SimpleNamespace(sync_playwright=lambda: nullcontext(driver))
    monkeypatch.setattr(live_check.importlib, "import_module", lambda name: playwright)
    monkeypatch.setattr(
        live_check, "arm_watchdog", lambda server: SimpleNamespace(kill=bool, wait=bool)
    )
    monkeypatch.setattr(live_check, "stop_group", lambda server: None)
    monkeypatch.setattr(live_check, "report_spend", lambda *a: None)
    monkeypatch.setattr(live_check, "ignore_signals", lambda: None)
    monkeypatch.setattr(
        live_check, "walk", lambda bc, browser, args, ws, summary: walked.append(args.port)
    )
    args = SimpleNamespace(rehearse=True, case_data=None)
    live_check.run_walk(bc, args, tmp_path, {}, {})
    assert walked == [41234] and not hasattr(live_check, "PORT")


# PR1 answer key (R-SB2-7 ruling 5): --accept-limitations is accepted at argument parsing and the
# walk ticks the acceptance box when the Review step shows one. Without the flag and with N > 0
# the walk refuses before Start, naming the flag and N; it never ticks the box by itself.
# There is no seam for the walk besides `walk` itself, so it runs on a real page holding only the
# contract's ids (#run-confirm, #run-accept inside a label, #start-run, #progress-step, #open-run).
def review_page(browser: Any, items: int) -> Any:
    """Start is enabled by both ticks (the box only exists when items are counted)."""
    box = (
        f'<label><input id="run-accept" type="checkbox">I accept these {items} items</label>'
        if items
        else ""
    )
    page = browser.new_page()
    page.set_default_timeout(3000)
    page.set_content(
        f"""<section id="review-step"><label><input id="run-confirm" type="checkbox">approve
        </label>{box}<button id="start-run" disabled>Start run</button></section>
        <section id="progress-step" hidden><div id="run-progress">Complete: done</div>
        <button id="open-run" hidden>Open</button></section>
        <script>window.__starts=0;
        const sync=()=>{{const a=document.getElementById('run-accept');
          document.getElementById('start-run').disabled=
            !document.getElementById('run-confirm').checked||(a!==null&&!a.checked);}};
        document.addEventListener('change',sync);
        document.getElementById('start-run').addEventListener('click',()=>{{window.__starts++;
          document.getElementById('progress-step').hidden=false;
          document.getElementById('open-run').hidden=false;}});</script>"""
    )
    return page


def walk_on(
    monkeypatch: pytest.MonkeyPatch, page: Any, flag: bool, frozen: int | None = None
) -> None:
    for name in ("fill_form", "check_run"):
        monkeypatch.setattr(live_check, name, lambda *a, **k: None)
    monkeypatch.setattr(live_check, "check_review", lambda *a, **k: [])
    bc = SimpleNamespace(errors_of=lambda page: [], note=lambda *a, **k: None)
    case = None if frozen is None else {"expected-outcomes": {"counted_total": frozen}}
    args = SimpleNamespace(accept_limitations=flag, minutes=1, case_data=case)
    browser = SimpleNamespace(new_page=lambda **options: page)
    live_check.walk(bc, browser, args, Path("."), {})


def test_accept_limitations_parses_without_the_not_available_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FW_PYTHON", sys.executable)
    args = live_check.parse(["--cap", "5", "--accept-limitations", "--rehearse"])
    assert args.accept_limitations is True
    done = refuse(tmp_path, "--cap", "5", "--accept-limitations", "--rehearse", keep=True)
    assert "not available" not in done.stderr and "Stage 2" not in done.stderr


@pytest.mark.browser
def test_the_walk_ticks_the_acceptance_box_when_the_flag_is_given(
    browser: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = review_page(browser, 4)
    walk_on(monkeypatch, page, True)
    assert page.evaluate("document.getElementById('run-accept').checked")
    assert page.evaluate("window.__starts") == 1


@pytest.mark.browser
def test_the_walk_refuses_before_start_without_the_flag_naming_the_flag_and_n(
    browser: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = review_page(browser, 4)
    with pytest.raises(Exception, match=r"--accept-limitations") as raised:
        walk_on(monkeypatch, page, False)
    assert "4" in str(raised.value) and "Timeout" not in type(raised.value).__name__
    assert page.evaluate("window.__starts") == 0
    assert not page.evaluate("document.getElementById('run-accept').checked"), "ticked on its own"


@pytest.mark.browser
@pytest.mark.parametrize("flag", [False, True])
def test_the_walk_needs_no_flag_when_nothing_is_counted(
    browser: Any, monkeypatch: pytest.MonkeyPatch, flag: bool
) -> None:
    page = review_page(browser, 0)
    walk_on(monkeypatch, page, flag)
    assert page.evaluate("window.__starts") == 1


# PR2 answer key (lead review of #74): the flag accepts exactly the N the case froze, and the walk
# says which N it accepts. A different N is a Refusal before Start (the box stays unticked).
@pytest.mark.browser
def test_the_flag_accepts_the_frozen_number_and_prints_it(
    browser: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    page = review_page(browser, 4)
    walk_on(monkeypatch, page, True, frozen=4)
    assert page.evaluate("document.getElementById('run-accept').checked")
    assert page.evaluate("window.__starts") == 1
    assert re.search(r"\b4\b", capsys.readouterr().out), "the accepted N was not printed"


@pytest.mark.browser
@pytest.mark.parametrize(("items", "frozen"), [(4, 3), (4, 5), (0, 2)])
def test_the_flag_refuses_before_start_when_n_differs_from_the_frozen_count(
    browser: Any, monkeypatch: pytest.MonkeyPatch, items: int, frozen: int
) -> None:
    page = review_page(browser, items)
    with pytest.raises(live_check.Refusal) as raised:
        walk_on(monkeypatch, page, True, frozen=frozen)
    assert str(items) in str(raised.value) and str(frozen) in str(raised.value)
    assert page.evaluate("window.__starts") == 0, "Start was clicked"
    assert not page.evaluate("!!document.getElementById('run-accept')?.checked"), "ticked"


@pytest.mark.browser
def test_the_flag_with_nothing_counted_proceeds_and_says_so(
    browser: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    page = review_page(browser, 0)
    walk_on(monkeypatch, page, True, frozen=0)
    assert page.evaluate("window.__starts") == 1
    out = capsys.readouterr().out.lower()
    assert "nothing" in out and "counted" in out, out


@pytest.mark.browser
def test_an_n_mismatch_refusal_ends_the_run_with_exit_2_not_a_recorded_fault(
    browser: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Lead: REFUSE means no Start and exit 2. `walk` runs inside the real `attempt`, which turns
    any exception into a fault and exit 1; a Refusal must get past it."""
    import browser_check as bc

    for name in live_check.KEYS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FW_PYTHON", sys.executable)
    for name, value in {
        "FAULTS": Faults(),
        "results": [],
        "S": tmp_path,
        "WALK": "",
        "PY": "",
        "NEW_SESSION": False,
        "scan_server_logs": lambda: None,
        "secrets": list,
    }.items():
        monkeypatch.setattr(bc, name, value)
    for name in ("fill_form", "check_run"):
        monkeypatch.setattr(live_check, name, lambda *a, **k: None)
    monkeypatch.setattr(live_check, "check_review", lambda *a, **k: [])
    page = review_page(browser, 4)
    stand_in = SimpleNamespace(new_page=lambda **options: page, pages=[])

    def run_walk(bc: Any, args: Any, out: Path, summary: dict[str, Any], held: Any) -> None:
        args.case_data = {
            "case": {"label": "stand-in"},
            "expected-outcomes": {"counted_total": 3},  # the page shows 4
        }
        bc.attempt("live", stand_in, lambda: live_check.walk(bc, stand_in, args, out, summary))

    monkeypatch.setattr(live_check, "run_walk", run_walk)
    saved = {s: signal.getsignal(s) for s in live_check.HALTING}
    try:
        code = live_check.main(
            ["--cap", "1", "--rehearse", "--accept-limitations", "--out", str(tmp_path / "o")]
        )
    finally:
        for sig, handler in saved.items():
            signal.signal(sig, handler)
    assert code == 2, f"exit status {code}"
    assert page.evaluate("window.__starts") == 0, "Start was clicked"
    assert [f.kind for f in bc.FAULTS.items] == [], "the refusal was recorded as a fault"


# PR2 ruling: --accept-limitations needs a frozen count to check N against, which only --case
# supplies. A paid run without one is refused at argument parsing; a rehearsal (no spend) is not.
def test_a_paid_accept_limitations_run_without_a_case_is_refused_at_parse(tmp_path: Path) -> None:
    done = refuse(tmp_path, "--cap", "1", "--accept-limitations")
    assert done.returncode == 2, (done.returncode, done.stderr[-300:])
    assert "--case" in done.stderr and len(done.stderr.splitlines()) == 1, done.stderr
    assert not (tmp_path / "out").exists(), "something was launched"


def test_a_rehearsed_accept_limitations_run_without_a_case_is_not_refused_at_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FW_PYTHON", sys.executable)
    args = live_check.parse(["--cap", "1", "--accept-limitations", "--rehearse"])
    assert args.accept_limitations is True and args.case_data is None
