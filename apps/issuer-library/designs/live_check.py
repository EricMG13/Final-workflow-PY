"""Paid walk through the app: TDG, the real engine, a spend cap. Run explicitly; never by a gate.

    <playwright python> live_check.py --cap USD [--config sol-medium] [--modules "CP-1 CP-1A"]
        [--minutes 60] [--out DIR] [--rehearse] [--case DIR [--accept-limitations]]

--case DIR runs a frozen case (cases/live-tdg-fy2024/<case>: case.json, context.json,
expected-outcomes.json, answer-key.json) through the app and checks every required output that
exists at this stage; --cap, --config and --modules default to the case's. Records only Stage 2
creates are reported "not applicable before Stage 2" when absent and checked when present.

Needs FW_PYTHON. --rehearse serves the fake engine (no provider, no
key) and skips the flow and evidence checks, saying so in its scope. Provider keys are popped from
this process's environment and passed only to the server (its own process group, stopped on exit).
"""

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import flow_check
from faults import redact

HERE = Path(__file__).resolve().parent
R = HERE.parents[2]
KEYS = tuple(runpy.run_path(str(R / "src/deploy_workflow/model/redact.py"))["KEY_ENV_NAMES"])
# The adapter's KEY_VARIABLES values (a test pins it); GitHub tokens are not provider keys.
PROVIDER_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "COPILOT_GITHUB_TOKEN",
)
SOURCES = R / "data/public-corpus/v1/TDG"
CONTEXT = R / "runs/cpos-launch-live-002/context.json"
CASE = "TDG as of 2024-09-30"
LITERALS = ("7,940", "6,261")  # filed net sales and cash, USD millions (10-K, 2024-09-30)
REHEARSAL = "rehearsal: fake engine, no provider called; flow and evidence checks skipped"
KEY_CONFIG, KEY_REQUESTED = "sol-medium", {"CP-1", "CP-1A"}  # the case the answer key checks
KEY_MODULES = {"CP-0", "CP-1", "CP-1A"}  # ... and what the launcher runs for it
# Run by `sh -c ... PGID` in its own session, with stdin a pipe only live_check holds: EOF means
# live_check is gone (any signal, a crash), so it stops the server's group. See arm_watchdog.
WATCHDOG = 'read _; kill -TERM -- "-$0"; sleep 15; kill -KILL -- "-$0"'
HALTING = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)
KEY_RUNNER = (
    "import importlib.util as u, sys\nfrom decimal import Decimal\nfrom pathlib import Path\n"
    "s = u.spec_from_file_location('answer_key', sys.argv[1]); m = u.module_from_spec(s)\n"
    "sys.modules['answer_key'] = m; s.loader.exec_module(m)\n"
    "m.assert_live_evidence(Path(sys.argv[2]), Decimal(sys.argv[3]))\n"
)


class Refusal(Exception):
    ends_run = True  # attempt re-raises it: exit 2, not a recorded fault


STAGE2 = "not applicable before Stage 2"
# Worst first. The status -> outcome table lives in src/deploy_workflow/handoff_outcome.py.
SEVERITY = ("will_refuse", "gap", "limited", "check", "information", "ready")
handoff_outcome = runpy.run_path(str(R / "src/deploy_workflow/handoff_outcome.py"))
# The report's text with svg removed and a newline after every table cell and block element, so
# adjacent cells do not run together ("September 11, 2014Rounded"). A detached clone has no layout,
# so innerText is not available; the separators are inserted into the clone.
REPORT_TEXT_JS = (
    "el => { const c = el.cloneNode(true);"
    " c.querySelectorAll('svg').forEach(n => n.remove());"
    " c.querySelectorAll('td, th, tr, p, div, li, h1, h2, h3, h4, h5, h6, section, article,"
    " header, footer, dt, dd, figcaption, caption, blockquote, pre, br')"
    ".forEach(n => n.after('\\n'));"
    " return c.textContent; }"
)
BUNDLE = ("report.html", "view.json", "report-view.json", "delivery.json")


def load_case(folder: str) -> dict[str, Any]:
    """The frozen case's files; a missing file or source is a refusal, named."""
    base = Path(folder)
    found: dict[str, Any] = {}
    for name in ("case", "context", "answer-key", "expected-outcomes"):
        try:
            found[name] = json.loads((base / f"{name}.json").read_text())
        except (OSError, ValueError) as error:
            raise Refusal(f"--case {folder}: cannot read {name}.json: {error}") from error
    if found["case"].get("schema") != "live-case/1":
        raise Refusal(f"--case {folder}: case.json is not schema live-case/1")
    found["files"] = [R / s for s in found["case"]["sources"]]
    if missing := [str(f) for f in found["files"] if not f.is_file()]:
        raise Refusal(f"--case {folder}: sources not found: {missing[0]}")
    found["context_path"] = base / "context.json"
    return found


def forecast_of(items: list[dict[str, Any]], ordered: list[str]) -> dict[str, str]:
    """Each module's worst forecast outcome among its items; `ready` when it has none."""
    return {
        m: min(
            (i["outcome"] for i in items if i["scope"] == m), key=SEVERITY.index, default="ready"
        )
        for m in ordered
    }


def expected_items(expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"scope": m, "outcome": r["outcome"]}
        for m, rules in expected["modules"].items()
        for r in rules
    ]


def outcome_faults(
    forecast: dict[str, str], run: Path, refused: str = ""
) -> tuple[list[str], dict[str, str]]:
    """Every module whose outcome is not confirmed equal to its forecast; and what each one did.
    `refused` names the module the run stopped at. Unconfirmed and not-reached are findings,
    except CP-0: it is the table, not a module under test, so it is never a finding."""
    found, did = [], {}
    cp0 = (run / "CP-0.md").read_text() if (run / "CP-0.md").exists() else ""
    for module, wanted in forecast.items():
        handoff = run / f"{module}.md"
        own = handoff.read_text() if handoff.exists() else None
        actual, how = handoff_outcome["actual_of"](module, own, cp0, refused=module == refused)
        did[module] = f"{actual} ({how})"
        if module != "CP-0" and handoff_outcome["verdict"](wanted, actual) != "agreed":
            found.append(f"{module}: forecast {wanted}, run did {actual} ({how})")
    return found, did


def spend_line_ok(shown: str, spent: Any) -> bool:
    """The app's spend line in its two finished forms (web/actions.js), matched exactly."""
    return bool(
        re.fullmatch(rf"Recorded spend: USD {re.escape(str(spent))}( of a USD \S+ cap)?", shown)
    )


def literal_faults(shown: str, literals: list[dict[str, str]]) -> list[str]:
    return [
        f"report lacks frozen literal {lit['text']} ({lit['source']})"
        for lit in literals
        if lit["text"] not in shown
    ]


def stage2_faults(
    args: argparse.Namespace, ws: Path, run: Path, review: dict[str, Any]
) -> list[str]:
    """Records only Stage 2 creates: reported when absent, checked when present."""
    intake = max((ws / "intake").glob("*/start-authorization.md"), default=None)
    context, kept = run / "context.json", run / "expectations.json"
    for name, path in (("expectations.json", kept), ("context.json", context)):
        print(f"{name}: " + ("present" if path.exists() else STAGE2), flush=True)
    stated = bool(intake and "accepted:" in intake.read_text())
    print(f"start receipt accepted ids: {'present' if stated else STAGE2}", flush=True)
    found = []
    reviewed = ws / "intake" / run.name / "context.json"
    if not context.exists():
        pass
    elif reviewed.exists():  # the form re-serialises the case file
        if context.read_bytes() != reviewed.read_bytes():
            found.append("run context.json is not byte-identical to the reviewed intake context")
        case_file = args.case_data["context_path"]
        if json.loads(context.read_text()) != json.loads(case_file.read_text()):
            found.append("run context.json differs in content from the case context")
    elif context.read_bytes() != args.case_data["context_path"].read_bytes():
        found.append("run context.json is not byte-identical to the case context")
    if kept.exists():
        shown = {
            k: review[k]
            for k in ("issue_classification", "documents", "expectations", "counted", "without")
        }
        if json.loads(kept.read_text()) != shown | {"review_id": review["review_id"]}:
            found.append("expectations.json differs from the approved review")
    return found


def required_outputs(
    args: argparse.Namespace, ws: Path, run: Path, review: dict[str, Any], stopped: str
) -> list[str]:
    """Faults in the run folder, delivery bundle and Stage 2 records. After a stop only the folder
    and the records are checked, and the stop reason is the recorded result."""
    found = [] if (run / "workflow.json").exists() else ["run folder lacks workflow.json"]
    found += [
        f"instructions/{m}.md missing"
        for m in review["modules"]
        if not (run / f"instructions/{m}.md").exists()
    ]
    found += [] if intake_status(ws) else ["intake status.json missing"]
    found += stage2_faults(args, ws, run, review)
    print(
        "HTML Model / calculation.json: not published by app runs (known beta limitation)",
        flush=True,
    )
    if stopped:
        return found
    if not list(run.glob("completed-*.json")):
        found.append("no completion receipt (completed-*.json)")
    delivery = next(run.glob("deliveries/*"), None)
    if delivery is None:
        return [*found, "no delivery bundle"]
    found += [f"delivery bundle lacks {n}" for n in BUNDLE if not (delivery / n).exists()]
    for handoff in sorted(delivery.glob("CP-*.md")):
        accepted = run / handoff.name
        if not accepted.exists() or accepted.read_bytes() != handoff.read_bytes():
            found.append(f"delivered {handoff.name} differs from the accepted handoff")
    return found


def case_outcomes(
    bc: Any, args: argparse.Namespace, ws: Path, summary: dict[str, Any], stopped: str = ""
) -> None:
    """Forecast (the shown review, the frozen outcomes) against what the run did."""
    summary["stopped"] = stopped or None
    reviews = list((ws / "intake").glob("*/review.json"))
    if not reviews:
        bc.note(
            False, "no review.json in the intake folder: forecast not available", kind="forecast"
        )
        return
    review = json.loads(max(reviews).read_text())
    expected = args.case_data["expected-outcomes"]
    shown = forecast_of(review.get("expectations", []), review["modules"])
    frozen = forecast_of(expected_items(expected), expected["ordered_modules"])
    summary.update(forecast_shown=shown, forecast_frozen=frozen)
    for module in sorted(set(shown) | set(frozen)):
        if shown.get(module, "ready") != frozen.get(module, "ready"):
            bc.note(
                False,
                f"review forecast {module} {shown.get(module)} != frozen {frozen.get(module)}",
                kind="forecast",
            )
    counted = len(review.get("counted", []))
    if counted != expected["counted_total"]:
        bc.note(
            False,
            f"review counts {counted} items, frozen {expected['counted_total']}",
            kind="forecast",
        )
    run = max((ws / "runs").glob("web-*"), default=None)
    if run is None:
        return
    named = re.search(r"\((CP-[0-9A-Z]+)\) not accepted", stopped)
    found, did = outcome_faults(shown, run, named[1] if named else "")
    summary["outcomes"] = did
    for line in found:
        bc.note(False, f"forecast vs outcome: {line}", kind="forecast")
    if "CP-0" in shown:
        print("CP-0: not testable (states no status of its own)", flush=True)
    testable = len(shown) - ("CP-0" in shown)
    bc.note(not found, f"forecast confirmed equal for the {testable} testable modules: {did}")
    for line in required_outputs(args, ws, run, review, stopped):
        bc.note(False, f"required output: {line}", kind="outputs")


def config_models() -> dict[str, str]:
    """The model each configuration runs (turn.py, a stdlib-only table, loaded by path)."""
    return dict(runpy.run_path(str(R / "src/deploy_workflow/model/turn.py"))["CONFIG_MODELS"])


def call_faults(rows: list[dict[str, Any]], config: str) -> list[str]:
    found = [f"call {i}: no request_id" for i, r in enumerate(rows) if not r.get("request_id")]
    found += [
        f"call {i}: reported {r.get('reported_model')} != requested {r.get('requested_model')}"
        for i, r in enumerate(rows)
        if r.get("reported_model") != r.get("requested_model")
    ]
    configs = {r.get("config_id") for r in rows}
    if len(configs) != 1 or None in configs or (config and configs != {config}):
        return [
            *found,
            f"calls ran config(s) {sorted(map(str, configs))}, wanted {config or 'one'}",
        ]
    expected = config_models().get(str(next(iter(configs))))
    return found + [
        f"call {i}: model {r.get('requested_model')} != {expected} for config {r['config_id']}"
        for i, r in enumerate(rows)
        if r.get("requested_model") != expected
    ]


def spend_faults(rows: list[dict[str, Any]], cap: Decimal, status_spent: str) -> list[str]:
    amounts, unknown = [], 0
    for r in rows:
        try:
            amounts.append(Decimal(str(r["settled_usd"])))
        except (KeyError, InvalidOperation):  # null is the engine's unknown cost
            unknown += 1
    charged = sum(amounts, Decimal(0))
    found = [f"{unknown} calls of unknown cost: spend is not known"] if unknown else []
    if charged <= 0:
        found.append(f"settled spend {charged} is not above zero")
    if charged > cap:
        found.append(f"settled spend {charged} exceeds cap {cap}")
    try:
        if Decimal(status_spent) != charged:
            found.append(f"status spend {status_spent} != settled sum {charged}")
    except InvalidOperation:
        found.append(f"status spend {status_spent!r} is not a number")
    return found


def handoff_faults(run: Path, modules: set[str], filed: tuple[str, ...] = LITERALS) -> list[str]:
    """Live execution, and each handoff carrying the sha256 of its upstream (as the answer key)."""
    done = sorted(run.glob("completed-*.json"))
    if not done:
        return ["no completed-*.json: execution is not recorded"]
    record = json.loads(done[0].read_text())
    executed = dict(record.get("module_execution", {}))
    kinds = {record.get("execution"), *executed.values()}
    found = (
        [] if kinds == {"live-provider"} else [f"execution {sorted(map(str, kinds))} is not live"]
    )
    if set(executed) != modules:
        found.append(f"module_execution {sorted(executed)} != accepted {sorted(modules)}")
    text = {m: (run / f"{m}.md").read_bytes() for m in modules if (run / f"{m}.md").exists()}
    digest = {m: hashlib.sha256(raw).hexdigest().encode() for m, raw in text.items()}
    for later, upstream in (("CP-1", "CP-0"), ("CP-1A", "CP-0"), ("CP-1A", "CP-1")):
        if later in text and upstream in text and digest[upstream] not in text[later]:
            found.append(f"{later} handoff lacks the {upstream} digest: upstream not consumed")
    if "CP-1" in text:
        found += [
            f"CP-1 handoff lacks filed value {n}" for n in filed if n.encode() not in text["CP-1"]
        ]
    return found


def call_evidence(
    run: Path, cap: Decimal, status_spent: str, modules: set[str], config: str = ""
) -> list[str]:
    """Faults in the retained provider calls: config, model, spend, modules called."""
    rows = [json.loads(n) for n in (run / "live/calls.jsonl").read_text().splitlines() if n]
    found = call_faults(rows, config) + spend_faults(rows, cap, status_spent)
    seen = {r["module_id"] for r in rows}
    if seen != modules:
        found.append(f"modules called {sorted(seen)} != accepted {sorted(modules)}")
    return found


def live_evidence(
    run: Path, cap: Decimal, status_spent: str, modules: set[str], config: str = ""
) -> list[str]:
    """Faults in the retained provider calls and handoffs (rules of assert_live_evidence)."""
    return call_evidence(run, cap, status_spent, modules, config) + handoff_faults(run, modules)


def is_key_case(args: argparse.Namespace) -> bool:
    """The request is the one the answer key covers; decided from the arguments, not the run."""
    return args.config == KEY_CONFIG and set(args.modules.split()) == KEY_REQUESTED


def key_env() -> dict[str, str]:
    """The answer key's environment: pytest's pythonpath, and asserts never compiled away."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONOPTIMIZE"}
    return env | {"PYTHONPATH": f"{R / 'src'}{os.pathsep}{R}"}


def answer_key(run: Path, cap: Decimal) -> list[str]:
    """Run the test suite's own assert_live_evidence on the run, in the project interpreter."""
    command = [os.environ["FW_PYTHON"], "-c", KEY_RUNNER, str(R / "tests/test_cpos_launch.py")]
    try:
        done = subprocess.run(
            [*command, str(run), str(cap)],
            cwd=R,
            env=key_env(),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ["answer key assert_live_evidence timed out after 300 s"]
    if done.returncode == 0:
        return []
    tail = " | ".join(done.stderr.strip().splitlines()[-4:])
    return [
        f"answer key assert_live_evidence (exit {done.returncode})" + (f": {tail}" if tail else "")
    ]


def parse(argv: list[str]) -> argparse.Namespace:
    class One(argparse.ArgumentParser):
        def error(self, message: str) -> Any:
            raise Refusal(message.splitlines()[0])

    p = One(add_help=False)
    p.add_argument("--cap")
    p.add_argument("--config")
    p.add_argument("--modules")
    p.add_argument("--case")
    p.add_argument("--accept-limitations", action="store_true")
    p.add_argument("--minutes", type=float, default=60)
    p.add_argument("--out")
    p.add_argument("--rehearse", action="store_true")
    args = p.parse_args(argv)
    args.case_data = load_case(args.case) if args.case else None
    if (case := args.case_data) and not args.modules:
        args.modules = " ".join(case["case"]["requested_modules"])
    args.config = args.config or (case["case"]["config"] if case else "sol-medium")
    args.modules = args.modules or "CP-1 CP-1A"
    args.context, args.sources = (case["context_path"], SOURCES) if case else (CONTEXT, SOURCES)
    cap_text = args.cap if args.cap is not None else (case["case"]["cap_usd"] if case else None)
    try:
        cap = Decimal(cap_text) if cap_text is not None else None
    except InvalidOperation:
        cap = None
    if cap is None or not cap.is_finite() or cap <= 0:
        raise Refusal("--cap USD is required and must be a finite number above zero")
    if args.accept_limitations and not args.case and not args.rehearse:
        raise Refusal("--accept-limitations on a paid run needs --case (the frozen counted_total)")
    if not args.rehearse and not any(os.environ.get(k) for k in PROVIDER_KEYS):
        raise Refusal(f"no provider key in the environment (one of {', '.join(PROVIDER_KEYS)})")
    if not (math.isfinite(args.minutes) and args.minutes >= 1):
        raise Refusal("--minutes must be at least 1")
    used = Path(args.out) if args.out else None
    if used and used.exists() and (not used.is_dir() or any(used.iterdir())):
        raise Refusal("--out exists and is not an empty folder")
    for name in ("FW_PYTHON",):
        if not os.environ.get(name):
            raise Refusal(f"{name} is not set")
    args.cap = cap
    return args


def group_alive(server: subprocess.Popen[bytes]) -> bool:
    server.poll()  # reap the server itself, so a zombie does not count
    try:
        os.killpg(server.pid, 0)
    except (ProcessLookupError, PermissionError):
        # macOS refuses signal 0 to a group holding only zombies (reparented, not yet reaped).
        # The group is ours (same user), so no live foreign process explains the refusal.
        return False
    return True


def stop_group(server: subprocess.Popen[bytes]) -> str | None:
    """SIGTERM, then SIGKILL, the server's process group; a message if anything may still live."""
    try:
        leads = os.getpgid(server.pid) == server.pid
    except ProcessLookupError:
        leads = True  # already gone; killpg on its id finds nothing either way
    if not leads:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            with suppress(ProcessLookupError):
                os.kill(server.pid, sig)
            with suppress(subprocess.TimeoutExpired):
                server.wait(timeout=10)
        return (
            f"server {server.pid} does not lead its own process group: only it was signalled, "
            "its workers may still be spending. Find them with: pgrep -fl 'bridge.py start'"
        )
    for sig, patience in ((signal.SIGTERM, 15), (signal.SIGKILL, 10)):
        if not group_alive(server):
            return None
        with suppress(ProcessLookupError):
            os.killpg(server.pid, sig)
        end = time.monotonic() + patience
        while group_alive(server) and time.monotonic() < end:
            time.sleep(0.2)
    if not group_alive(server):
        return None
    return (
        f"process group {server.pid} still alive after SIGKILL: an engine worker may still be "
        "spending. Find it with: pgrep -fl 'bridge.py start'; its status.json is under "
        "<workspace>/intake/<id>/"
    )


def arm_watchdog(server: subprocess.Popen[bytes]) -> subprocess.Popen[bytes]:
    """A helper in its own session that stops the server's group if live_check dies by any means.

    Its stdin is a pipe only this process holds (children start with close_fds), so the kernel's
    close of it on our death, SIGKILL included, is the signal. It cannot see a hung live_check."""
    return subprocess.Popen(
        ["sh", "-c", WATCHDOG, str(server.pid)],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        start_new_session=True,
    )


def intake_status(ws: Path) -> Path | None:
    """The status.json both the shown-spend check and the teardown read: the last by name."""
    return max((ws / "intake").glob("*/status.json"), default=None)


def spend_of(ws: Path) -> tuple[str | None, Decimal, int]:
    """status.json's recorded spend, the ledger's settled sum, and rows of unknown cost.

    A row with no settled amount (cost unknown) or a torn line counts as unknown, never as zero."""
    status: str | None = None
    if path := intake_status(ws):
        try:
            spent = json.loads(path.read_text()).get("spent_usd")
            status = None if spent is None else str(spent)
        except (OSError, ValueError):
            status = "unreadable"
    ledger, unknown = Decimal(0), 0
    for path in (ws / "runs").glob("*/live/calls.jsonl"):
        try:
            lines = [n for n in path.read_text().splitlines() if n]
        except OSError:
            unknown += 1
            continue
        for line in lines:
            try:
                ledger += Decimal(str(json.loads(line)["settled_usd"]))
            except (ValueError, KeyError, TypeError, InvalidOperation):
                unknown += 1
    return status, ledger, unknown


def check_review(page: Any, args: argparse.Namespace) -> list[str]:
    """What the review screen says it will run, against what was asked for."""
    shown = page.evaluate(
        """() => ({
          rows: Object.fromEntries([...document.querySelectorAll('#run-review dl dt')]
            .map(t => [t.textContent, t.nextElementSibling.textContent])),
          ids: [...document.querySelectorAll('#run-review .review-modules li')]
            .map(li => li.title.split(':')[0])})"""
    )
    print(f"review screen will run: {shown['ids']} ({shown['rows']})", flush=True)
    found = []
    model, effort = config_models().get(args.config), args.config.rsplit("-", 1)[-1]
    if (
        not model
        or model not in shown["rows"].get("Model", "")
        or effort not in shown["rows"]["Model"]
    ):
        found.append(f"review model {shown['rows'].get('Model')!r} is not config {args.config}")
    cap = shown["rows"].get("Maximum spend", "").removeprefix("USD ")
    try:
        if Decimal(cap) != args.cap:
            found.append(f"review cap USD {cap} != {args.cap}")
    except InvalidOperation:
        found.append(f"review cap {cap!r} is not a number")
    ids, wanted = set(shown["ids"]), set(args.modules.split())
    if is_key_case(args) and ids != KEY_MODULES:
        found.append(f"review modules {shown['ids']} are not exactly {sorted(KEY_MODULES)}")
    elif not wanted <= ids:
        found.append(f"review modules {shown['ids']} lack some of {args.modules}")
    return found


def fill_form(page: Any, args: argparse.Namespace) -> None:
    expect = importlib.import_module("playwright.sync_api").expect
    page.goto(f"http://127.0.0.1:{args.port}/")
    page.wait_for_selector("#library-new-run", timeout=30000)
    page.click("#library-new-run")
    frame = page.frame_locator("#context-editor")
    frame.locator("#load").wait_for(state="attached", timeout=15000)
    frame.locator("#load").set_input_files(str(args.context))
    expect(page.locator("#context-readiness")).to_contain_text(
        "Required fields complete", timeout=15000
    )
    page.click("#use-context")
    page.wait_for_selector("#source-step:not([hidden])")
    page.set_input_files("#run-sources", str(args.sources))
    expect(page.locator("#upload-list")).to_contain_text(
        f"{len(list(args.sources.iterdir()))} files"
    )
    page.select_option("#run-model", args.config)
    page.fill("#run-budget", str(args.cap))
    page.locator("details.run-advanced summary").click()
    page.fill("#run-modules", args.modules)
    page.click("#review-run")
    # The app bounds the review at 10 minutes; a refusal shows its problems in #new-run-message.
    page.wait_for_function(
        "() => !document.getElementById('review-step').hidden"
        " || /\\S/.test(document.getElementById('new-run-message').textContent)"
        " && !/^Checking/.test(document.getElementById('new-run-message').textContent)",
        timeout=660000,
    )
    if page.locator("#review-step").is_hidden():
        raise RuntimeError("review refused: " + page.inner_text("#new-run-message")[:500])


def shown_count(items: str) -> int:
    """The N in the page's `I accept these N items` label; 0 when the page has no box."""
    found = re.search(r"\d+", items)
    return int(found[0]) if found else 0


def check_frozen_count(args: argparse.Namespace, shown: int) -> None:
    """With a case loaded `counted_total` must be a non-negative integer equal to the shown N."""
    if args.case_data is None:  # no --case: nothing frozen to compare (rehearsal only)
        return
    frozen = args.case_data["expected-outcomes"].get("counted_total")
    if type(frozen) is not int or frozen < 0:
        raise Refusal(f"the case's counted_total must be a non-negative integer, not {frozen!r}")
    if shown != frozen:
        raise Refusal(f"the review counts {shown} items but the case froze counted_total {frozen}")


def accept_frozen_count(page: Any, args: argparse.Namespace, shown: int) -> None:
    """Tick the acceptance box with the flag, printing the N accepted (the count is checked)."""
    if args.case_data is None:
        print(f"accepting {shown} counted items (no case: no frozen count to compare)", flush=True)
    elif not shown:
        print("accepting nothing: no items were counted", flush=True)
    else:
        print(f"accepting {shown} counted items (the case froze {shown})", flush=True)
    if shown:
        page.check("#run-accept")


def walk(
    bc: Any, browser: Any, args: argparse.Namespace, ws: Path, summary: dict[str, Any]
) -> None:
    page = browser.new_page(viewport={"width": 1366, "height": 768})  # inside attempt: captured
    bc.errors_of(page)
    fill_form(page, args)
    wrong = check_review(page, args)
    if wrong:  # raised, so the attempt keeps the page: screenshot, source and URL
        raise RuntimeError("review screen: " + "; ".join(wrong))
    boxed = bool(page.locator("#run-accept").count())  # counted items: only the flag accepts
    items = page.inner_text("label:has(#run-accept)").strip() if boxed else ""
    shown = shown_count(items)
    check_frozen_count(args, shown)
    if boxed and not args.accept_limitations:
        raise RuntimeError(
            f"review counts items ({items!r}); rerun with --accept-limitations to accept them"
        )
    if args.accept_limitations:
        accept_frozen_count(page, args, shown)
    page.check("#run-confirm")
    if page.is_disabled("#start-run"):
        raise RuntimeError("Start stays disabled after review (provider not configured?); no spend")
    page.click("#start-run")  # the one paid step; never retried
    page.wait_for_selector("#progress-step:not([hidden])")
    page.wait_for_selector(
        "#open-run:not([hidden]), #another-run:not([hidden])", timeout=int(args.minutes * 60000)
    )
    status = page.inner_text("#run-progress")
    if not status.lower().startswith("complete"):
        if args.case_data:  # a stop is a recorded result (what ended where), then still a fault
            case_outcomes(bc, args, ws, summary, stopped=status[:300])
        raise RuntimeError(f"run did not complete: {status[:300]}")
    bc.note(True, f"run finished: {status[:120]}")
    check_run(bc, page, args, ws, summary)


def check_run(
    bc: Any, page: Any, args: argparse.Namespace, ws: Path, summary: dict[str, Any]
) -> None:
    note = bc.note
    shown_spend = page.inner_text("#run-spend")
    page.click("#open-run")
    page.wait_for_selector(".report-built .report-row a", timeout=30000)
    page.click(".report-built .report-row a >> nth=0")
    report = page.frame_locator("#report-preview")
    report.locator("#view-root").wait_for(state="attached", timeout=30000)
    run = max((ws / "runs").glob("web-*"))
    summary["run_id"] = run.name
    status_file = intake_status(ws)
    assert status_file, "no intake status.json"
    state = json.loads(status_file.read_text())
    summary["report"] = str(next(run.glob("deliveries/*/report.html"), ""))
    note(
        spend_line_ok(shown_spend, state.get("spent_usd")),
        f"app spend {shown_spend!r} equals status.json {state.get('spent_usd')!r}",
    )
    accepted = {p.stem for p in run.glob("CP-*.md")}
    built = page.locator(".built-from summary", has_text="Built from").first.inner_text()
    count = re.search(r"Built from (\d+) handoffs", built)
    note(
        count is not None and int(count[1]) == len(accepted),
        f"{built!r} vs {len(accepted)} accepted",
    )
    if args.case_data:
        case_outcomes(bc, args, ws, summary)
    if args.rehearse:
        return
    shown = report.locator("#view-root").evaluate(REPORT_TEXT_JS)
    handoffs = [p.read_text() for p in sorted(run.glob("deliveries/*/CP-*.md"))]
    problems = flow_check.run_faults(run, args.sources) + flow_check.report_faults(shown, handoffs)
    case = args.case_data
    spent = str(state.get("spent_usd"))
    if case:  # its literals are the frozen answer key's, checked below
        problems += call_evidence(run, args.cap, spent, accepted, args.config)
        problems += handoff_faults(run, accepted, ())
    else:
        problems += live_evidence(run, args.cap, spent, accepted, args.config)
    if case:
        literals = case["answer-key"]["literals"]
        problems += literal_faults(shown, literals)
        summary["answer_key"] = f"case answer-key.json: {len(literals)} frozen literals checked"
    else:
        problems += [f"report lacks filed value {n}" for n in LITERALS if n not in shown]
    problems += [
        f"requested module {m} not accepted" for m in sorted(set(args.modules.split()) - accepted)
    ]
    if not case and is_key_case(
        args
    ):  # any mismatch with the key's case (e.g. an extra module) is its fault
        problems += answer_key(run, args.cap)
        summary["answer_key"] = "applied"
    elif not case:
        summary["answer_key"] = (
            f"not applicable: request is not {KEY_CONFIG} with {sorted(KEY_REQUESTED)}"
        )
    for problem in problems:
        note(False, f"live check: {problem}", kind="flow")
    note(not problems, "flow, evidence and filed-value checks")


def run_walk(
    bc: Any, args: argparse.Namespace, out: Path, summary: dict[str, Any], held: dict[str, str]
) -> None:
    sync_playwright = importlib.import_module("playwright.sync_api").sync_playwright
    ws = out / "ws"
    ws.mkdir()
    if args.case_data:  # the case's files as one folder, the form's own upload path
        args.sources = out / "sources"
        args.sources.mkdir()
        for source in args.case_data["files"]:
            shutil.copyfile(source, args.sources / source.name)  # a browser upload skips symlinks
    engine = HERE / "fake_engine" if args.rehearse else R / "apps/issuer-library/engine"
    server = dog = None
    try:
        server, port = bc.serve_free(
            ws,
            engine,
            key="not-a-real-key" if args.rehearse else None,
            extra=held,
        )
        args.port = port  # the free port the server took; the form and the walks use it
        dog = arm_watchdog(server)
        with sync_playwright() as driver:
            browser = bc.SignedBrowser(driver.chromium.launch(**bc.engine_options()["chromium"]))
            try:
                bc.attempt("live", browser, lambda: walk(bc, browser, args, ws, summary))
            finally:
                browser.close()
            if args.case_data:
                single_run_walks(bc, driver, ws, summary, port)
    finally:
        ignore_signals()  # teardown must finish
        try:
            if server is not None and (left := stop_group(server)):
                print(left, file=sys.stderr, flush=True)
                bc.FAULTS.add("live", "worker", left)
        finally:
            if dog is not None:
                dog.kill()  # disarmed: the group is gone, its id must not be signalled again
                dog.wait()
            report_spend(bc, ws, summary)


def single_run_walks(bc: Any, driver: Any, ws: Path, summary: dict[str, Any], port: int) -> None:
    """The real-workspace walk over this workspace's one run, in both engines (browser_check)."""
    if not summary["run_id"]:  # the run never completed: nothing to read
        summary["real_workspace_walk"] = "not run: the run did not complete"
        return
    for name, options in bc.engine_options().items():
        try:
            browser = bc.SignedBrowser(getattr(driver, name).launch(**options))
        except Exception as error:  # noqa: BLE001
            # Recorded, not hidden: a FAIL line and an "exception" fault name the engine and the
            # error; the other engine still walks.
            detail = f"{type(error).__name__}: {str(error)[:600]}"
            bc.note(False, f"{name}-single-run: launch failed: {detail}", fault=False)
            bc.FAULTS.add(f"{name}-single-run", "exception", detail)
            continue
        try:
            bc.attempt(
                f"{name}-single-run",
                browser,
                lambda: bc.single_run_walk(browser, name, port, ws),  # noqa: B023
            )
        finally:
            browser.close()
    for line in bc.NOT_EXERCISABLE:  # R18 allows a skip only on the retained fixture, never here
        bc.FAULTS.add("live", "missing", line)
    summary["real_workspace_walk"] = {
        "engines": list(bc.engine_options()),
        "repo_store_counts": bc.NOT_APPLICABLE,
        "not_exercisable": list(bc.NOT_EXERCISABLE),
    }


def report_spend(bc: Any, ws: Path, summary: dict[str, Any]) -> None:
    status, ledger, unknown = spend_of(ws)
    summary.update(spent_usd=status, ledger_usd=str(ledger), unknown_cost_calls=unknown)
    extra = f" + {unknown} calls of unknown cost" if unknown else ""
    print(f"spend: status.json USD {status}, ledger USD {ledger}{extra}", flush=True)
    if unknown:
        bc.FAULTS.add("live", "spend", f"{unknown} calls of unknown cost: spend is not known")


def ignore_signals() -> None:
    for sig in HALTING:
        signal.signal(sig, signal.SIG_IGN)


def case_label(args: argparse.Namespace) -> str:
    return args.case_data["case"]["label"] if args.case_data else CASE


def finish(bc: Any, args: argparse.Namespace, out: Path, summary: dict[str, Any]) -> int:
    passed = sum(ok for ok, _ in bc.results)
    mode = "rehearsal" if args.rehearse else "live"
    scope = (
        (f"{REHEARSAL} ({case_label(args)})" if args.case_data else REHEARSAL)
        if args.rehearse
        else f"live provider: {args.config}, {case_label(args)}, modules {args.modules}, "
        f"spend USD {summary['spent_usd']}; answer key {summary.get('answer_key', 'not reached')}"
    )
    secrets = bc.secrets()
    bc.FAULTS.write(out / "faults.json", scope, passed, secrets)
    recorded = json.loads((out / "faults.json").read_text()) | {"mode": mode}
    (out / "faults.json").write_text(redact(json.dumps(recorded, indent=2), secrets) + "\n")
    summary.update(mode=mode, scope=scope, failed=len(bc.FAULTS.items))
    (out / "summary.json").write_text(
        redact(json.dumps(summary, indent=2, default=str), secrets) + "\n"
    )
    print(f"{passed} passed, {len(bc.FAULTS.items)} faults: {out / 'faults.json'}")
    return int(bool(bc.FAULTS.items) or passed != len(bc.results))


def main(argv: list[str]) -> int:
    try:
        args = parse(argv)
    except Refusal as refusal:
        print(f"live_check: {refusal}", file=sys.stderr)
        return 2
    # Keys leave this process's environment now; only the server gets the provider ones.
    popped = {k: os.environ.pop(k) for k in KEYS if k in os.environ}
    held = {k: v for k, v in popped.items() if k in PROVIDER_KEYS and not args.rehearse}
    import browser_check as bc  # imports Playwright; after the refusals

    known = bc.secrets
    bc.secrets = lambda: [*known(), *popped.values()]
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="issuer-library-live-"))
    out.mkdir(parents=True, exist_ok=True)
    bc.NEW_SESSION = True  # each server in its own process group
    bc.S, bc.PY = out, os.environ["FW_PYTHON"]
    mode = "REHEARSAL (fake engine, no provider)" if args.rehearse else "PAID RUN"
    print(
        f"{mode}: config={args.config}, modules={args.modules} (dependencies added by the "
        f"launcher), cap=USD {args.cap}, case={case_label(args)}, workspace={out / 'ws'}",
        flush=True,
    )
    summary: dict[str, Any] = {"run_id": None, "spent_usd": None, "report": None}
    signalled_at: list[int] = []  # faults recorded when the first signal arrived

    def terminate(_signal: int, _frame: Any) -> None:
        signalled_at.append(len(bc.FAULTS.items))
        raise KeyboardInterrupt

    for sig in HALTING:  # also SIGINT: a shell's background job starts with it ignored
        signal.signal(sig, terminate)
    refused: Refusal | None = None
    try:
        run_walk(bc, args, out, summary, held)
    except Refusal as refusal:  # before Start; not a fault
        refused = refusal
        print(f"live_check: {refusal}", file=sys.stderr)
    except KeyboardInterrupt:
        ignore_signals()
        bc.FAULTS.add("live", "interrupted", "interrupted by a signal; spend may be above zero")
    except (Exception, SystemExit) as error:  # noqa: BLE001 - recorded as a fault, never silent
        bc.FAULTS.add("live", "exception", f"{type(error).__name__}: {str(error)[:600]}")
    finally:
        ignore_signals()
        # A Ctrl-C to the whole group also breaks the browser: only faults recorded after the
        # signal are relabelled; a failure from before it keeps its kind.
        for fault in bc.FAULTS.items[signalled_at[0] :] if signalled_at else ():
            if fault.kind == "exception":
                fault.kind = "interrupted"
        bc.scan_server_logs()
        code = finish(bc, args, out, summary)
    return 2 if refused else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
