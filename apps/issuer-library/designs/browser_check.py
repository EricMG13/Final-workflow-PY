"""Browser check over the retained workspace and an offline fake-provider run; no provider is called.

Run by validate.py browser. Needs Playwright and FW_PYTHON. Screenshots go to
FW_BROWSER_OUT, or to a temporary folder.
"""

import http.client
import json
import os
import re
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import flow_check
import single_run as expected
from faults import Faults, crashes, http_fault, redact, request_fault
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

MODULE_CODE = re.compile(r"\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])")

HERE = Path(__file__).resolve().parent
R = HERE.parents[2]
# Hand-written by someone other than the code's author (Plan 1, L0); the walk fails on drift.
KEY = json.loads((HERE.parent / "web/testdata/library-screening-expected.json").read_text())
# Set by main(): importing this module creates nothing and starts nothing.
S = Path()
PY = ""
NEW_SESSION = False
ISSUER = "Northbridge Synthetic Group"
# Every provider key the Redactor knows, from its one list; the fake engine gets a dummy key only.
KEYS = tuple(runpy.run_path(str(R / "src/deploy_workflow/model/redact.py"))["KEY_ENV_NAMES"])
# HTTP statuses the walk deliberately provokes, as (status, path), each with a reason. None yet.
EXPECTED_HTTP: frozenset[tuple[int, str]] = frozenset()
SCOPE = "offline: retained workspace and fake-provider runs; no provider called"
results: list[tuple[bool, str]] = []
# Checks a walk could not exercise: printed, kept here for the live record, never counted as a pass.
NOT_EXERCISABLE: list[str] = []
NOT_APPLICABLE = "not applicable: repo-store key"
RETAINED_FIXTURE = (
    False  # set only by `--single-run WS --retained-fixture`; live_check never sets it
)
FAULTS = Faults()
WALK = ""  # the walk now running, for the fault record
# Each server's log file and the thread copying its stdout into it, by port.
LOGS: dict[int, Path] = {}
DRAINS: list[threading.Thread] = []
# Each instance's session cookie, by port, in this process's memory only.
SESSIONS: dict[int, dict[str, Any]] = {}


def note(ok: bool, what: str, fault: bool = True, kind: str = "check") -> None:
    results.append((ok, what))
    if not ok and fault:
        FAULTS.add(WALK, kind, what)
    print(redact(("PASS " if ok else "FAIL ") + what, secrets()), flush=True)


def not_exercisable(name: str, what: str, why: str) -> None:
    """Only the retained fixture (--retained-fixture) may lack a record (R18); anywhere else a
    missing events.jsonl, spend, citation or chart is a failed check, never a skip."""
    if not RETAINED_FIXTURE:
        note(False, f"{name}: {what}: not recorded by this run: {why}", kind="missing")
        return
    line = f"{name}: {what}: not exercisable on this fixture: {why}"
    NOT_EXERCISABLE.append(line)
    print(redact("SKIP " + line, secrets()), flush=True)


def free_port() -> int:
    # ponytail: free when returned; another process may take it before the server binds.
    # serve_free retries on a taken port, so the race costs a new port, not a failed walk.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class PortTaken(SystemExit):
    """The server exited because its port was occupied; any other exit stays a plain SystemExit."""


def serve_free(
    workspace: Path,
    engine: Path,
    key: str | None = None,
    extra: dict[str, str] | None = None,
) -> tuple[subprocess.Popen[bytes], int]:
    """Start the server on a free port; if another process took it first, pick again (3 tries)."""
    for _ in range(2):
        port = free_port()
        try:
            return serve(workspace, port, engine, key, extra), port
        except PortTaken:
            continue
    port = free_port()
    return serve(workspace, port, engine, key, extra), port


def serve(
    workspace: Path,
    port: int,
    engine: Path,
    key: str | None = None,
    extra: dict[str, str] | None = None,
) -> subprocess.Popen[bytes]:
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    env |= {
        "PYTHONPATH": str(R / "src"),
        "PYTHONUNBUFFERED": "1",  # the launch line must reach the pipe at once
        "ISSUER_LIBRARY_ENGINE_ROOT": str(engine),
        "PYTHONDONTWRITEBYTECODE": "1",
        "CHECK_ROOT": str(R),
    }
    if key:
        env["OPENAI_API_KEY"] = key
    env |= extra or {}
    state = S / f"state-{port}"
    shutil.rmtree(state, ignore_errors=True)
    LOGS[port] = S / f"server-{port}.log"
    LOGS[port].write_bytes(b"")  # stdout and stderr both append, so neither overwrites the other
    stderr = LOGS[port].open("ab")
    process = subprocess.Popen(
        [
            PY,
            "-B",
            "-m",
            "issuer_library",
            "--workspace",
            str(workspace),
            "--port",
            str(port),
            "--state-dir",
            str(state),
            "--no-browser",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=stderr,
        start_new_session=NEW_SESSION,  # live_check sets it, to stop the server's whole group
    )
    stderr.close()  # the child holds its own copy
    try:
        return wait_ready(process, port)
    except BaseException:
        process.terminate()
        process.wait()
        raise


def wait_ready(process: subprocess.Popen[bytes], port: int) -> subprocess.Popen[bytes]:
    for _ in range(100):
        if process.poll() is not None:
            taken = "local port is occupied" in LOGS[port].read_text(errors="replace")
            raise (PortTaken if taken else SystemExit)(f"server exited with {process.returncode}")
        try:
            urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                f"http://127.0.0.1:{port}/health", timeout=1
            )
        except OSError:
            time.sleep(0.1)
            continue
        sign_in(process, port)
        drain = threading.Thread(target=copy_log, args=(process, LOGS[port]), daemon=True)
        drain.start()
        DRAINS.append(drain)
        return process
    raise SystemExit("server did not start")


def secrets() -> list[str]:
    """Every provider key value in this environment, and the dummy key the fake engine gets."""
    return [os.environ[k] for k in KEYS if k in os.environ] + ["not-a-real-key"]


def copy_log(process: subprocess.Popen[bytes], log: Path) -> None:
    """Copy the server's stdout after the launch line into its log, so the pipe never fills."""
    assert process.stdout is not None
    with log.open("ab") as out:
        for line in process.stdout:
            out.write(redact(line.decode(errors="replace"), secrets()).encode())
            out.flush()


def sign_in(process: subprocess.Popen[bytes], port: int) -> None:
    """Exchange the one-time link the library prints with --no-browser for its session cookie."""
    assert process.stdout is not None
    origin = f"http://127.0.0.1:{port}"
    line = process.stdout.readline().decode().strip()
    if not line.startswith(f"Issuer Library: {origin}/launch?ticket="):
        raise SystemExit("server printed no launch link")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request("GET", line.removeprefix(f"Issuer Library: {origin}"))
        response = connection.getresponse()
        response.read()
        cookie = response.getheader("Set-Cookie") or ""
    finally:
        connection.close()
    if response.status != 303 or "=" not in cookie:
        raise SystemExit("server refused its launch link")
    name, value = cookie.split(";", 1)[0].split("=", 1)
    SESSIONS[port] = {
        "name": name,
        "value": value,
        "url": origin,
        "httpOnly": True,
        "sameSite": "Strict",
    }


class SignedBrowser:
    """Opens pages holding each started instance's session cookie, as its launch leaves them.

    The cookie names carry the port, so each instance reads only its own."""

    def __init__(self, browser: Any) -> None:
        self.browser = browser
        self.pages: list[Any] = []

    def new_page(self, **options: Any) -> Any:
        context = self.browser.new_context(**options)
        context.add_cookies(list(SESSIONS.values()))
        page = context.new_page()
        self.pages.append(page)
        return page

    def close(self) -> None:
        self.browser.close()


def errors_of(page: Any) -> list[str]:
    """Console and page errors, returned for the walk's own check; every fault is also recorded."""
    errors: list[str] = []
    walk = WALK  # bound now: a page left open by a failed walk keeps its own walk's name

    def console(message: Any) -> None:
        if message.type == "error":
            errors.append(message.text)
            FAULTS.add(walk, "console", message.text, page.url)

    def pageerror(error: Any) -> None:
        errors.append(str(error))
        FAULTS.add(walk, "pageerror", str(error), page.url)

    def response(received: Any) -> None:
        parts = urlparse(received.url)
        if parts.hostname == "127.0.0.1" and http_fault(received.status, parts.path, EXPECTED_HTTP):
            FAULTS.add(walk, "http", f"{received.status} {parts.path}", received.url)

    def failed(request: Any) -> None:
        if request_fault(request.failure):
            FAULTS.add(walk, "requestfailed", str(request.failure), request.url)

    page.on("console", console)
    page.on("pageerror", pageerror)
    page.on("response", response)
    page.on("requestfailed", failed)
    return errors


def real_workspace(browser: Any, name: str, port: int, full: bool) -> None:
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = errors_of(page)
    library_and_report(page, name, port)
    if full:
        every_section_renders(page, name)
    deliveries_and_settings(page, name, port)
    fitted_screens(page, name, port)
    note(not errors, f"{name}: no console errors {errors[:4]}")
    page.close()


ROW_IDS = "els => els.map(e => e.dataset.librarySelect)"


def row_ids(page: Any) -> list[str]:
    ids: list[str] = page.eval_on_selector_all(
        "#library-results button[data-library-select]", ROW_IDS
    )
    return ids


def library_counts(page: Any, name: str) -> None:
    """Row, run folder, delivery and issuer counts against the key; a drifted workspace fails."""
    ids = row_ids(page)
    folders = KEY["run_folder_rows"]["ids"]
    note(
        sorted(ids) == sorted(folders + KEY["delivery_rows"]["ids"]),
        f"{name}: library rows are the key's {len(folders)} run folders and"
        f" {KEY['delivery_rows']['count']} delivery rows (got {len(ids)}; drift fails here)",
    )
    total, issuers = KEY["row_count"]["value"], KEY["issuer_count"]["value"]
    note(
        page.locator("#library-count").inner_text()
        == f"{total} of {total} runs \u00b7 {issuers} issuers",
        f"{name}: the count line says {total} runs and {issuers} issuers",
    )
    note(
        page.evaluate("document.documentElement.scrollWidth<=innerWidth"),
        f"{name}: the library fits 1366x768 with no horizontal overflow",
    )


def reset_library(page: Any) -> None:
    """Reset returns Runs to Latest; Plan 1 steps compare every row, so choose Any run."""
    page.click("#library-clear")
    page.select_option("#library-runs", "any")


def coverage_line(page: Any, group: str) -> str:
    text: str = page.locator(f"[data-library-coverage='{group}']").inner_text()
    return text


def library_credit(page: Any, name: str) -> None:
    """Credit and market controls on the retained workspace, where most new fields are absent."""
    every = sorted(KEY["run_folder_rows"]["ids"] + KEY["delivery_rows"]["ids"])
    total = len(every)
    reset_library(page)
    note("runs=any" in page.url, f"{name}: Any run is written to the Library query")
    note(sorted(row_ids(page)) == every, f"{name}: Any run lists every key row")
    page.select_option("#library-runs", "latest")
    note(set(row_ids(page)) <= set(every), f"{name}: the Latest view lists only key rows")
    page.select_option("#library-runs", "any")
    page.click("#rating-filters summary")
    page.select_option("#library-classification", "high_yield")
    note(
        f"recorded for 0 of {total} runs" in coverage_line(page, "classification")
        and row_ids(page) == [],
        f"{name}: classification screening reports none recorded on the retained runs",
    )
    reset_library(page)
    page.click("#metric-filters summary")
    page.fill("#library-netLeverageMax", "4")
    note(
        f"recorded for 0 of {total} runs" in coverage_line(page, "net_leverage")
        and row_ids(page) == [],
        f"{name}: a net leverage maximum reports none recorded and lists no run",
    )
    reset_library(page)
    page.click("#deal-filters summary")
    page.fill("#library-talkMin", "300")
    note(
        f"recorded for 0 of {total} runs" in coverage_line(page, "talk") and row_ids(page) == [],
        f"{name}: a spread talk minimum reports none recorded and lists no run",
    )
    reset_library(page)
    page.click("#limit-filters summary")
    options = "els => els.map(e => e.value)"
    gaps = page.eval_on_selector_all("#library-limitation option", options)
    if len(gaps) < 2:
        print(f"SKIP {name}: accepted-limitation step, the workspace serves no gap text")
    else:
        page.select_option("#library-limitation", gaps[1])
        note(
            row_ids(page) != [] and "recorded for" in coverage_line(page, "limitation"),
            f"{name}: an accepted limitation taken from the served list keeps its runs",
        )
    reset_library(page)
    for column in ("net_leverage", "rating"):
        page.locator(f"[data-library-sort='{column}']").click()
        note(
            page.locator(f"[data-library-sort='{column}']").evaluate(
                "e => e.closest('th').getAttribute('aria-sort')"
            )
            == "ascending"
            and sorted(row_ids(page)) == every,
            f"{name}: the {column} column sorts ascending and keeps every key row",
        )
    page.click("[data-library-select='tdg-002']")
    detail = page.locator("#run-detail").inner_text()
    note(
        "Net leverage" in detail and "Classification" in detail and "Currency" in detail,
        f"{name}: a run detail shows the credit rows",
    )
    # The query restores the state after a reload, on Plan 1's leverage minimum case.
    case = KEY["filter_cases"]["a_leverage_min"]
    reset_library(page)
    page.click("#metric-filters summary")
    page.locator("[data-library-sort='leverage']").click()
    page.fill("#library-leverageMin", case["filters"]["leverageMin"])
    before = row_ids(page)
    page.reload()
    page.wait_for_selector("#library-results tbody tr")
    sort = page.locator("[data-library-sort='leverage']")
    note(
        page.input_value("#library-runs") == "any"
        and page.input_value("#library-leverageMin") == case["filters"]["leverageMin"]
        and sorted(before) == sorted(case["expected_ids"])
        and row_ids(page) == before
        and sort.evaluate("e => e.closest('th').getAttribute('aria-sort')") == "ascending",
        f"{name}: a reload from the Library query restores the controls, the sort and the key rows",
    )
    reset_library(page)


def library_screening(page: Any, name: str, port: int) -> None:
    """A filter and a sort change the rows; a detail opens; Open run and Open report stay in app."""
    cases = KEY["filter_cases"]
    page.fill("#library-query", cases["c_search_issuer_name"]["filters"]["search"])
    note(
        row_ids(page) == cases["c_search_issuer_name"]["expected_ids"],
        f"{name}: a search narrows the rows to the key's",
    )
    reset_library(page)
    page.click("#metric-filters summary")
    page.fill("#library-leverageMin", cases["a_leverage_min"]["filters"]["leverageMin"])
    note(
        sorted(row_ids(page)) == sorted(cases["a_leverage_min"]["expected_ids"]),
        f"{name}: a leverage minimum keeps the key's rows",
    )
    reset_library(page)
    sort = page.locator("[data-library-sort='leverage']")
    sort.focus()
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")
    note(
        row_ids(page)[:4] == KEY["sort_leverage_desc_missing_last"]["first_4_ids"],
        f"{name}: the keyboard sorts by leverage descending, missing last, as the key says",
    )
    page.locator("[data-library-issuer='TDG']").focus()
    page.keyboard.press("Space")
    note(
        len(row_ids(page)) == KEY["issuer_count"]["rows_per_issuer"]["TDG"],
        f"{name}: the keyboard chooses an issuer",
    )
    reset_library(page)
    page.click("[data-library-select='tdg-002']")
    detail = page.locator("#run-detail")
    note(
        "Total carrying debt / EBITDA As Defined" in detail.inner_text()
        and "5.96\u00d7" in detail.inner_text(),
        f"{name}: a row's detail opens with its metric and basis",
    )
    library_detail_links(page, name, port, "tdg-002")
    library_credit(page, name)


def library_detail_links(page: Any, name: str, port: int, run: str) -> None:
    """From an open detail, Open report and Open run stay in the app and are followed."""
    detail = page.locator("#run-detail")
    detail.locator("a:has-text('Open report')").click()
    page.wait_for_selector("#report-preview")
    note("W-Reports" in page.url, f"{name}: Open report opens the report inside the app")
    page.goto(f"http://127.0.0.1:{port}/#W-Library/cases?runs=any")
    page.reload()
    page.wait_for_selector("#library-results tbody tr")
    page.click(f"[data-library-select='{run}']")
    page.locator("#run-detail a:has-text('Open run')").click()
    page.wait_for_selector(".summary-lead")
    note("W-Overview" in page.url, f"{name}: Open run reaches the Overview")
    page.goto(f"http://127.0.0.1:{port}/#W-Library/cases?runs=any")
    page.reload()
    page.wait_for_selector("#library-results tbody tr")


def used_in(page: Any, name: str) -> None:
    used = page.locator("#module-head a", has_text="Used in")
    note(used.count() == 1, f"{name}: module output names the deliverables that used it")


def reader_names(page: Any, frame: Any, name: str) -> None:
    """The report's reader text and the navigation show names, and the rail marks Reports."""
    note(
        not MODULE_CODE.search(frame.locator("#view-root").inner_text()),
        f"{name}: the report's reader text shows names, not module codes",
    )
    note(
        not MODULE_CODE.search(page.locator("#module-list").text_content()),
        f"{name}: navigation shows names, not module codes",
    )
    note(
        page.locator(".rail a[data-place='Reports'][aria-current]").count() == 1,
        f"{name}: rail stays beside the report and marks Reports",
    )


def follow_built_from(page: Any, name: str) -> None:
    page.locator(".built-from tbody a").first.click()
    page.wait_for_selector("#module-head h2")
    note("W-Reports" not in page.url, f"{name}: Built from opens the module output")


def library_and_report(page: Any, name: str, port: int) -> None:
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#library-results tbody tr", timeout=30000)
    page.select_option("#library-runs", "any")  # Plan 1's checks compare every row
    want = sum(p.is_dir() for p in (R / "runs").iterdir())
    # Each run folder in the store has one Overview link; delivery rows sit beside them.
    note(
        page.locator("#library-results a.run-link").count() == want,
        f"{name}: library lists all {want} run folders, one link each",
    )
    pick = "#library-results [data-library-select"
    note(
        page.locator(pick + "='cpos-launch-live-002']").count() == 1
        and page.locator(pick + "^='delivery:']").count() > 0,
        f"{name}: launcher run is in the library",
    )
    library_counts(page, name)
    page.screenshot(path=str(S / f"{name}-library.png"))
    library_screening(page, name, port)
    page.goto(f"http://127.0.0.1:{port}/#CP-1/performance?c=tdg-002")
    page.wait_for_selector(".bars")
    note(
        page.locator(".bar-column").count() == 3,
        f"{name}: curated CP-1 chart renders from the live store",
    )
    page.screenshot(path=str(S / f"{name}-module.png"))
    used_in(page, name)
    chart_style(page, name, port)
    page.click(".workspace-tabs a:has-text('Reports')")
    page.wait_for_selector(".report-row a")
    page.click(".report-built .report-row a >> nth=0")
    page.wait_for_selector("#report-preview")
    frame = page.frame_locator("#report-preview")
    frame.locator("body.library-report").wait_for(state="attached", timeout=15000)
    note(
        frame.locator("#view-root").count() == 1,
        f"{name}: report renders inside the app, with the adapter",
    )
    reader_names(page, frame, name)
    page.screenshot(path=str(S / f"{name}-report.png"))
    href = page.locator(".report-tools a[download]").get_attribute("href")
    note("download=1" in href and "sha256=" in href, f"{name}: original download link is pinned")
    page.locator(".built-from summary").first.click()
    follow_built_from(page, name)


EVERY_SECTION_JS = """async()=>{
  const bad=[];
  const extra=['W-Overview','W-Calendar','W-Reports','W-Evidence','CP-OS','W-Forecast'];
  const content=()=>document.getElementById('content').textContent;
  for(const [key,run] of Object.entries(contexts))
  for(const module of [...Object.keys(run.modules),...extra]) {
    location.hash=`${module}?c=${encodeURIComponent(key)}`;renderRoute();
    for(const [section] of navigationSections(module,key,current.output)) {
      location.hash=routeHref(module,section,null,key).slice(1);renderRoute();
      if(!showsCodes(current)&&section!=='audit'&&(isAnalytical(module)||module==='W-Overview')){
        const left=content().match(/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/);
        if(left)bad.push(`code ${left[0]} on ${key} ${module} ${section}`);
      }
      if(/Couldn.t present this output/.test(content()))bad.push(`${key} ${module} ${section}`);
      if(current.module!==module)bad.push(`redirected ${key} ${module}`);
    }
  }
  return bad;}"""


def throttled(js: str) -> str:
    """A route-walking script that pauses after each route change: Firefox refuses history
    changes beyond about 200 in ten seconds, and the single-run walk visits many sections."""
    return js.replace("renderRoute();", "renderRoute(); await new Promise(r => setTimeout(r, 80));")


def every_section_renders(page: Any, name: str, script: str = EVERY_SECTION_JS) -> None:
    problems = page.evaluate(script)
    note(
        not problems,
        f"{name}: every section of every module of every run renders ({problems[:6]})",
    )


def deliveries_and_settings(page: Any, name: str, port: int) -> None:
    page.goto(f"http://127.0.0.1:{port}/#CP-8/comparison?c=tdg-run-comparison")
    page.reload()
    page.wait_for_selector(".comparison-pair")
    note(
        page.locator(".comparison-pair a").count() == 2,
        f"{name}: CP-8 comparison links both compared deliverables",
    )
    page.goto(f"http://127.0.0.1:{port}/#W-Reports/list?c=cpos-launch-live-002")
    page.reload()
    page.wait_for_selector(".report-row a")
    page.click(".report-built .report-row a >> nth=0")
    page.frame_locator("#report-preview").locator("body").wait_for(state="attached")
    note(
        page.locator("#report-preview").count() == 1
        and "TransDigm" in page.frame_locator("#report-preview").locator("body").inner_text(),
        f"{name}: CLI launcher delivery opens as a deliverable",
    )
    page.click(".rail a[data-place='Settings']")
    page.wait_for_selector("#workspace-path")
    note(
        page.input_value("#workspace-path") == str(R),
        f"{name}: Settings shows the workspace folder",
    )
    page.screenshot(path=str(S / f"{name}-settings.png"))
    page.click(".rail a[data-place='Help']")
    page.wait_for_selector(".help-copy")
    page.keyboard.press("/")
    note(
        page.evaluate("document.activeElement.id") == "library-query" and "W-Library" in page.url,
        f"{name}: / from Help opens the library search",
    )


def fitted_screens(page: Any, name: str, port: int, key: str = "tdg-002") -> None:
    for width, height in ((1280, 600), (1536, 730)):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"http://127.0.0.1:{port}/#W-Overview/overview?c={key}")
        page.reload()
        page.wait_for_selector(".summary-lead")
        lead = page.locator(".summary-lead")
        lead.scroll_into_view_if_needed()
        box = lead.bounding_box()
        scroller = page.locator("#content").bounding_box()
        note(
            box["height"] <= scroller["height"]
            and lead.evaluate("e=>e.scrollHeight<=e.clientHeight"),
            f"{name}: the bottom line is fully visible at {width}x{height}",
        )
        note(
            page.evaluate("document.documentElement.scrollWidth<=innerWidth"),
            f"{name}: no horizontal overflow at {width}x{height}",
        )
        page.screenshot(path=str(S / f"{name}-summary-{width}.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"http://127.0.0.1:{port}/#W-Library/cases")
    page.reload()
    page.wait_for_selector("#library-results tbody tr")
    note(
        page.evaluate("document.documentElement.scrollWidth<=innerWidth"),
        f"{name}: no horizontal overflow at 390 wide (library)",
    )
    page.goto(f"http://127.0.0.1:{port}/#W-NewRun/run")
    page.wait_for_selector("#context-step h2")
    note(
        page.evaluate("document.documentElement.scrollWidth<=innerWidth"),
        f"{name}: no horizontal overflow at 390 wide (new run)",
    )
    page.screenshot(path=str(S / f"{name}-newrun-narrow.png"))


CHART_STYLE = """() => {
  const css = (selector, property) => {
    const element = document.querySelector(selector);
    return element ? getComputedStyle(element)[property] : 'missing';
  };
  return {
    bar: css('.bar', 'borderTopLeftRadius'),
    card: css('.summary-chart', 'borderTopLeftRadius'),
    track: css('.horizontal-chart .track:not(.missing)', 'backgroundColor'),
    barEnd: css('.horizontal-chart .track:not(.missing)>i', 'borderTopRightRadius'),
    rect: css('.vector-chart rect.movement', 'rx'),
    grade: css('.grade', 'borderTopLeftRadius'),
  };
}"""


# CHART_STYLE over every section of every module of one run, keeping each style a chart shows.
CHART_STYLE_ALL = (
    "async(key) => { const style = "
    + CHART_STYLE
    + "; const seen = {}; const modules = [...Object.keys(contexts[key].modules), 'W-Overview'];"
    " for (const module of modules) {"
    "  location.hash = `${module}?c=${encodeURIComponent(key)}`; renderRoute();"
    "  for (const [section] of navigationSections(module, key, current.output)) {"
    "   location.hash = routeHref(module, section, null, key).slice(1); renderRoute();"
    "   for (const [k, v] of Object.entries(style())) if (v !== 'missing') seen[k] = v;"
    "  } } return seen; }"
)
CHART_STYLE_ALL = throttled(CHART_STYLE_ALL)


CHART_STYLE_WANT = {
    "bar": "4px",
    "card": "12px",
    "track": "rgba(0, 0, 0, 0)",
    "barEnd": "4px",
    "rect": "4px",
    "grade": "999px",
}


def chart_style(page: Any, name: str, port: int) -> None:
    """Charts follow the Untitled UI look: rounded data-ends, no tracks, pill grades, 12px cards."""
    run = "?c=tdg-002"
    seen: dict[str, str] = {}
    for route in ("#CP-1/performance", "#W-Overview/overview", "#CP-2/assessment"):
        page.goto(f"http://127.0.0.1:{port}/{route}{run}")
        page.wait_for_selector("#content .section-heading")
        seen.update({k: v for k, v in page.evaluate(CHART_STYLE).items() if v != "missing"})
    note(
        seen == CHART_STYLE_WANT,
        f"{name}: charts use rounded data-ends, no tracks and pill grades ({seen})",
    )
    page.goto(f"http://127.0.0.1:{port}/#CP-1/performance{run}")
    page.wait_for_selector(".bars")


def chart_style_single(page: Any, name: str, folder: str) -> None:
    """A single run may draw only some charts: each one it draws must match the shared style, and
    one that draws none is reported as not exercisable, never as a pass."""
    seen: dict[str, str] = page.evaluate(CHART_STYLE_ALL, folder)
    if not seen:
        not_exercisable(name, "chart style", "this run draws no chart")
        return
    wrong = {k: v for k, v in seen.items() if CHART_STYLE_WANT[k] != v}
    note(not wrong, f"{name}: the charts it draws use the shared style ({seen})")


FORM_STYLE = """() => {
  const css = (selector, property) => {
    const element = document.querySelector(selector);
    return element ? getComputedStyle(element)[property] : 'missing';
  };
  return {
    select: [css('#run-model', 'height'), css('#run-model', 'borderTopLeftRadius')],
    input: [css('#run-budget', 'height'), css('#run-budget', 'borderTopLeftRadius')],
    secondary: css('#edit-context', 'height'),
    done: css('.run-stages li[data-stage=context]', 'borderTopColor'),
    current: css('.run-stages li[aria-current]', 'borderTopColor'),
    todo: css('.run-stages li[data-stage=review]', 'borderTopColor'),
  };
}"""
FORM_WANT = {
    "select": ["40px", "8px"],
    "input": ["40px", "8px"],
    "secondary": "40px",
    "done": "rgb(0, 23, 229)",
    "current": "rgb(0, 23, 229)",
    "todo": "rgb(228, 230, 236)",
}


def check_flow(name: str, workspace: Path, report: Any) -> None:
    """Sources -> handoffs -> delivered copies -> the report text, by the independent checker."""
    (run,) = sorted(Path(workspace, "runs").glob("web-*"))
    # The report's own chart drawing (svg) is not text the handoffs carry.
    shown = report.locator("#view-root").evaluate(
        "el => { const c = el.cloneNode(true); c.querySelectorAll('svg').forEach(n => n.remove());"
        " return c.textContent; }"
    )
    delivered = [p.read_text() for p in sorted(run.glob("deliveries/*/CP-*.md"))]
    problems = flow_check.run_faults(run, S / "issuer") + flow_check.report_faults(shown, delivered)
    for problem in problems:
        note(False, f"{name}: flow check: {problem}", kind="flow")
    if not problems:
        note(True, f"{name}: data flows from sources to the report (flow check)")


# One browser walk through New run, kept in page order; splitting it would hide the sequence.
def new_run(  # noqa: PLR0915, RUF100
    browser: Any, name: str, port: int, workspace: Path, start: bool | str
) -> None:
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = errors_of(page)
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#library-new-run", timeout=30000)
    note(
        "No runs in this workspace yet" in page.inner_text("#content"),
        f"{name}: empty workspace opens on the library",
    )
    note(
        not page.locator(".rail a[data-place='Run activity']").is_visible(),
        f"{name}: run-level rail links are hidden when empty",
    )
    page.screenshot(path=str(S / f"{name}-empty.png"))
    page.click("#library-new-run")
    frame = page.frame_locator("#context-editor")
    frame.locator("#load").wait_for(state="attached", timeout=15000)
    frame.locator("#load").set_input_files(str(S / "context.json"))
    # The user states the two required choices by clicking their cards; nothing is preselected.
    # The walk's folder holds no legal documents, so the declaration is "None".
    frame.locator("label[for='issue_classification-high_yield']").click()
    frame.locator("summary", has_text="Attachments").click()
    frame.locator("label[for='legal_documents-none']").click()
    expect(page.locator("#context-readiness")).to_contain_text(
        "Required fields complete", timeout=15000
    )
    page.screenshot(path=str(S / f"{name}-context.png"))
    page.click("#use-context")
    page.wait_for_selector("#source-step:not([hidden])")
    note(
        ISSUER in page.inner_text("#context-summary"),
        f"{name}: context from the form reaches the folder step",
    )
    page.set_input_files("#run-sources", str(S / "issuer"))
    expect(page.locator("#upload-list")).to_contain_text("4 files", timeout=10000)
    note(True, f"{name}: choosing the folder lists its files, dot files left out")
    page.fill("#run-budget", "50")
    page.screenshot(path=str(S / f"{name}-folder.png"))
    form = page.evaluate(FORM_STYLE)
    note(
        form == FORM_WANT,
        f"{name}: New run fields, buttons and stages use the shared controls ({form})",
    )
    # Navigation away and back keeps the prepared run.
    page.click(".rail a[data-place='Help']")
    page.wait_for_selector(".help-copy")
    page.click(".rail a[data-place='New run']")
    page.wait_for_selector("#source-step:not([hidden])")
    note(
        page.input_value("#run-budget") == "50",
        f"{name}: leaving and returning keeps the prepared run",
    )
    page.click("#review-run")
    page.wait_for_selector("#review-step:not([hidden])", timeout=60000)
    text = page.inner_text("#run-review")
    note(
        ISSUER in text
        and "Source readiness" in text
        and "CP-0" not in text
        and "gpt-6.1-sol" in text,
        f"{name}: review shows the launcher's plan",
    )
    note(page.is_disabled("#start-run"), f"{name}: Start stays disabled before approval")
    note(not any(Path(workspace, "runs").iterdir()), f"{name}: review created no run")
    page.locator("#run-review details").first.click()
    note(
        "chart.png" in page.inner_text("#run-review"),
        f"{name}: review lists the file no module can read",
    )
    page.screenshot(path=str(S / f"{name}-review.png"))
    page.check("#run-confirm")
    if page.locator("#run-accept").count():
        note(
            page.is_disabled("#start-run"),
            f"{name}: Start stays disabled until the acceptance is ticked",
        )
        page.check("#run-accept")
    page.click("#start-run")
    page.wait_for_selector("#progress-step:not([hidden])")
    page.wait_for_selector("#open-run:not([hidden])", timeout=180000)
    status = page.inner_text("#run-progress")
    if start == "stop":
        note(
            status.startswith(
                "Stopped: a module's handoff did not pass its check within the allowed turns."
            )
            and "no automatic paid retry" in status,
            f"{name}: a rejected module stops the run: {status[:90]}",
        )
        note(
            page.inner_text("#open-run") == "Open run",
            f"{name}: a stopped run offers Open run, not deliverables",
        )
        page.screenshot(path=str(S / f"{name}-stopped-progress.png"))
        page.click("#open-run")
        page.wait_for_selector(".workspace-tabs a, .workspace-tabs button", timeout=30000)
        note(ISSUER in page.inner_text("body"), f"{name}: the stopped run opens under its issuer")
        page.evaluate("location.hash = location.hash.replace(/^#[^?]*/, '#CP-0/audit')")
        expect(page.locator("#content")).to_contain_text("as of 2025-03-31", timeout=15000)
        note(True, f"{name}: the handoff it accepted can be read in the app")
        page.screenshot(path=str(S / f"{name}-stopped-handoff.png"))
        reports = Path(workspace, "runs").glob("*/deliveries/*/report.html")
        note(not list(reports), f"{name}: a stopped run published no report")
        note(not errors, f"{name}: stopped run, no console errors {errors[:4]}")
        page.close()
        return
    note(
        status.startswith("Complete: Report written.") and "Automated checks only" in status,
        f"{name}: fake-provider run finishes through the real bridge: {status[:70]}",
    )
    note("Recorded spend: USD" in page.inner_text("#run-spend"), f"{name}: spend is shown")
    page.screenshot(path=str(S / f"{name}-progress.png"))
    page.click("#open-run")
    page.wait_for_selector(".report-built .report-row a", timeout=30000)
    note(
        page.locator(".report-built .report-row a").count() == 1,
        f"{name}: the finished run's deliverable is listed",
    )
    page.click(".report-built .report-row a")
    page.frame_locator("#report-preview").locator("body").wait_for(state="attached", timeout=15000)
    note(
        ISSUER in page.frame_locator("#report-preview").locator("body").inner_text(),
        f"{name}: its report opens inside the app",
    )
    report = page.frame_locator("#report-preview")
    note(
        report.locator("#view-root figure").count() == 4,
        f"{name}: synthetic fake-provider run, its report draws the four CP-1 charts",
    )
    note(
        report.locator("img[src='x']").count() == 0,
        f"{name}: synthetic hostile text in a handoff stays text in the report",
    )
    check_flow(name, workspace, report)
    page.screenshot(path=str(S / f"{name}-delivered.png"))
    page.locator(".built-from summary").first.click()
    page.locator(".built-from tbody a").first.click()
    page.wait_for_selector("#module-head a:has-text('Used in')")
    note(
        page.locator("#content .record-field").count() > 0 or len(page.inner_text("#content")) > 20,
        f"{name}: Built from opens the run's module output",
    )
    page.click("#module-head a:has-text('Used in')")
    page.wait_for_selector("#report-preview")
    note(True, f"{name}: Used in returns to the deliverable")
    page.evaluate("location.hash = location.hash.replace(/^#[^?]*/, '#W-Overview/overview')")
    page.wait_for_selector(".summary-lead")
    note(
        "A fake engine finding only." in page.inner_text(".summary-lead")
        and "Confidence" in page.inner_text(".summary-lead"),
        f"{name}: synthetic fake-provider run, Summary leads with its stored bottom line",
    )
    note(
        "Total debt / EBITDA fell" in page.inner_text(".summary-card[data-module='CP-1']")
        and page.locator(".summary-chart").count() == 4,
        f"{name}: synthetic fake-provider run, Summary shows the CP-1 reader text and charts",
    )
    page.screenshot(path=str(S / f"{name}-synthetic-summary.png"))
    size = page.viewport_size
    for width, height in ((1280, 600), (1536, 730)):
        page.set_viewport_size({"width": width, "height": height})
        page.locator(".summary-lead .summary-facts").scroll_into_view_if_needed()
        note(
            page.evaluate(
                """(() => {
                  const lead = document.querySelector('.summary-lead').getBoundingClientRect();
                  const facts = document.querySelector('.summary-facts').getBoundingClientRect();
                  return facts.left >= lead.left && facts.right <= lead.right
                    && facts.bottom <= lead.bottom
                    && document.documentElement.scrollWidth <= innerWidth;
                })()"""
            ),
            f"{name}: confidence and limitation fit the lead at {width}x{height}, with no overflow",
        )
        page.screenshot(path=str(S / f"{name}-synthetic-summary-{width}.png"))
    page.set_viewport_size(size)
    page.click(".rail a[data-place='Issuer library']")
    page.wait_for_selector("#library-results tbody tr")
    page.select_option("#library-runs", "any")  # Latest could hide the new run
    # The catalogue names a run by its folder; only the store knows its issuer.
    find = "(issuer) => Object.keys(contexts).find(k => contexts[k].issuer === issuer)"
    key = page.evaluate(find, ISSUER)
    link = page.locator(f"#library-results a.run-link[href*='c={key}']")
    note(
        key is not None and link.count() == 1,
        f"{name}: the library lists the new run with its Overview link",
    )
    # A run that appears on disk while the app is open is offered, not forced.
    added = Path(workspace, "runs", "added-001")
    added.mkdir()
    (added / "CP-0.md").write_text("# CP-0\n\nAdded later.\n")
    expect(page.locator("#workspace-updated")).to_be_visible(timeout=70000)
    page.click("#reload-workspace")
    page.wait_for_selector("#library-results tbody tr")
    note(
        page.locator("[data-library-select='added-001']").count() == 1,
        f"{name}: a run added on disk is offered, then listed after Reload",
    )
    note(not errors, f"{name}: no console errors {errors[:4]}")
    page.close()


def run_row(page: Any, name: str, port: int, want: dict[str, Any]) -> None:
    """The run's one Library row, its Open run and Open report links, and the count line."""
    folder, delivery = want["folder_id"], want["delivery_id"]
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#library-results tbody tr", timeout=30000)
    note(folder in row_ids(page), f"{name}: the Library lists the run row {folder}")
    links = page.locator("#library-results a.run-link")
    note(
        links.count() == 1
        and links.first.get_attribute("href", timeout=5000) == f"#W-Overview/overview?c={folder}",
        f"{name}: the row has one Open run link to this run's Overview",
    )
    report = page.locator(f"#library-results a[href^='#W-Reports/{delivery}']")
    note(
        report.count() == 1, f"{name}: the row has one Open report link to delivery {delivery[:12]}"
    )
    note(
        page.locator("#library-count").inner_text() == "1 of 1 run \u00b7 1 issuer",
        f"{name}: the count line says 1 run and 1 issuer (this workspace holds one run)",
    )
    note(
        page.evaluate("document.documentElement.scrollWidth<=innerWidth"),
        f"{name}: the library fits 1366x768 with no horizontal overflow",
    )
    page.click(f"[data-library-select='{folder}']")
    library_detail_links(page, name, port, folder)
    line = f"N/A {name}: library counts and screening cases of the repo store: {NOT_APPLICABLE}"
    print(redact(line, secrets()), flush=True)


def overview_row(page: Any, name: str, port: int, want: dict[str, Any]) -> None:
    folder = want["folder_id"]
    page.goto(f"http://127.0.0.1:{port}/#W-Overview/overview?c={folder}")
    page.reload()
    page.wait_for_selector(".summary-lead")
    shown = page.evaluate("(k) => Object.keys(contexts[k].modules)", folder)
    ids = want["modules"]
    note(
        sorted(shown) == sorted(ids),
        f"{name}: the run's modules in the app are the delivery's ({shown} vs {ids})",
    )
    note(
        want["issuer_name"] in page.inner_text("body"),
        f"{name}: the Overview names the issuer {want['issuer_name']}",
    )


def reports_row(page: Any, name: str, port: int, want: dict[str, Any]) -> None:
    """Reports opens the report; Built from lists the delivered handoffs and their hashes."""
    folder = want["folder_id"]
    page.goto(f"http://127.0.0.1:{port}/#W-Reports/list?c={folder}")
    page.reload()
    page.wait_for_selector(".report-row a")
    day = date.fromisoformat(want["as_of"])
    row = page.locator(".report-built .report-row").first.inner_text()
    note(
        f"{want['issuer_name']} \u00b7 as of {day.day} {day:%B} {day.year}" in row
        and want["delivery_id"] in row,
        f"{name}: the Reports row names the issuer, the as-of date and the delivery",
    )
    page.click(".report-built .report-row a >> nth=0")
    frame = page.frame_locator("#report-preview")
    frame.locator("body.library-report").wait_for(state="attached", timeout=15000)
    note(
        want["issuer_name"] in frame.locator("#view-root").inner_text(),
        f"{name}: the report opens inside the app and names {want['issuer_name']}",
    )
    shown_text = " ".join(frame.locator("body").inner_text().split())
    titles = [want["title"], *want["module_titles"]]
    note(
        all(t in shown_text for t in titles),
        f"{name}: the report shows its title and the module titles {titles[:2]}",
    )
    reader_names(page, frame, name)
    href = page.locator(".report-tools a[download]").get_attribute("href")
    note("download=1" in href and "sha256=" in href, f"{name}: original download link is pinned")
    page.locator(".built-from summary").first.click()
    handoffs = want["handoffs"]
    note(
        page.locator(".built-from summary").first.inner_text()
        == f"Built from {len(handoffs)} handoffs \u00b7 byte-identical by SHA-256",
        f"{name}: Built from says {len(handoffs)} handoffs, byte-identical by SHA-256",
    )
    shown = {
        tuple(cell.strip() for cell in (r[0], r[2], r[3]))
        for r in page.eval_on_selector_all(
            ".built-from >> nth=0 >> tbody tr",
            "rows => rows.map(r => [...r.children].map(c => c.textContent))",
        )
    }
    prefixes = {(n.removesuffix(".md"), n, h[:12]) for n, h in handoffs.items()}
    note(
        shown == prefixes, f"{name}: Built from file names and SHA-256 prefixes match delivery.json"
    )
    note(
        all(want["handoff_bytes_match"].values()),
        f"{name}: the delivered handoff bytes hash to delivery.json's SHA-256 values",
    )
    follow_built_from(page, name)
    used_in(page, name)


FIND_EVIDENCE = throttled(
    """async([key, candidates]) => {
  for (const module of new Set(candidates.map(c => c[0]))) {
    location.hash = `${module}?c=${encodeURIComponent(key)}`; renderRoute();
    for (const [section] of navigationSections(module, key, current.output)) {
      location.hash = routeHref(module, section, null, key).slice(1); renderRoute();
      const marks = document.querySelectorAll('[data-evidence]');
      const shown = new Set([...marks].map(e => e.dataset.evidence));
      const hit = candidates.findIndex(c => c[0] === module && shown.has(c[1]));
      if (hit >= 0) return hit;
    }
  }
  return null;}"""
)


def evidence_row(page: Any, name: str, port: int, want: dict[str, Any]) -> None:
    """The evidence inspector opens a cited handoff line and shows that line's cells."""
    if not want["evidence"]:
        not_exercisable(name, "evidence inspector", "no handoff-line citation in view.json")
        return
    page.goto(f"http://127.0.0.1:{port}/#W-Overview/overview?c={want['folder_id']}")
    # The app marks only the lines it renders as records: open the first cited line it marks.
    pairs = [(e, k) for e in want["evidence"] for k in e["keys"]]
    marks = [[e["module"], k] for e, k in pairs]
    index = page.evaluate(FIND_EVIDENCE, [want["folder_id"], marks])
    note(
        index is not None,
        f"{name}: the app marks one of the {len(want['evidence'])} handoff lines cited",
    )
    if index is None:
        return
    cited, wanted = pairs[index]
    escaped = wanted.replace("\\", "\\\\").replace('"', '\\"')
    page.locator(f'[data-evidence="{escaped}"]').first.click()
    page.wait_for_selector("#inspector:not([hidden]) .evidence-fields")
    shown = " ".join(page.inner_text("#inspector").split())
    cells = [c for c in cited["cells"] if not expected.SYNTAX.search(c)]
    note(
        f"Line {cited['line']}" in shown and cited["file"] in shown,
        f"{name}: the inspector opens {cited['file']} line {cited['line']}",
    )
    missing = [c for c in cells if " ".join(c.split()) not in shown]
    note(
        bool(cells) and not missing,
        f"{name}: the inspector shows the cited line's cells {missing[:3]}",
    )
    page.keyboard.press("Escape")
    return


def activity_row(page: Any, name: str, port: int, want: dict[str, Any]) -> None:
    """Run activity lists the run's own events and spend; absent records are not exercisable."""
    page.goto(f"http://127.0.0.1:{port}/#CP-OS/activity?c={want['folder_id']}")
    page.reload()
    events, spent = want["activity"]["events"], want["activity"]["spent_usd"]
    if events is None and spent is None:
        page.wait_for_selector("#content .section-heading, #content p")
        note(
            # views.js's retained page; actions.js's "No events were recorded" is for a live run.
            "No live progress is recorded for this run" in page.inner_text("#content"),
            f"{name}: Run activity says no live progress is recorded for this run",
        )
    if events is None:
        not_exercisable(name, "Run activity events", "no events.jsonl")
    else:
        page.wait_for_selector(".activity-log tbody tr")
        rows = page.eval_on_selector_all(
            ".activity-log tbody tr", "rows => rows.map(r => r.children[1].textContent)"
        )
        accepted = [e for e in events if e["event"] == "module_accepted"]
        note(
            len(rows) == len(events)
            and sum(r.startswith("Accepted ") for r in rows) == len(accepted),
            f"{name}: Run activity lists the run's {len(events)} events, {len(accepted)} accepted",
        )
    if spent is None:
        not_exercisable(name, "Run activity spend", "no intake status.json with spent_usd")
    else:
        page.wait_for_selector("text=Recorded spend: USD")
        note(
            f"Recorded spend: USD {spent}" in page.inner_text("#content"),
            f"{name}: Run activity shows the recorded spend USD {spent}",
        )


def single_run_walk(browser: Any, name: str, port: int, workspace: Path) -> None:
    """Every per-run check of the real-workspace walk over a workspace holding one run.

    The expected values are read from the run's own files (single_run.py), not from the repo-store
    answer key; only that key's count asserts are skipped, and they say so."""
    folders = sorted(p.name for p in (workspace / "runs").iterdir() if p.is_dir())
    note(len(folders) == 1, f"{name}: the workspace holds only this run {folders[:3]}")
    want = expected.expectations(workspace, folders[0])
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = errors_of(page)
    run_row(page, name, port, want)
    overview_row(page, name, port, want)
    every_section_renders(page, name, throttled(EVERY_SECTION_JS))
    reports_row(page, name, port, want)
    evidence_row(page, name, port, want)
    activity_row(page, name, port, want)
    fitted_screens(page, name, port, want["folder_id"])
    chart_style_single(page, name, want["folder_id"])
    note(not errors, f"{name}: no console errors {errors[:4]}")
    page.close()


def attempt(walk: str, browser: SignedBrowser, action: Any) -> None:
    """Run one walk. A failure is recorded with the page it left open, and the next walk still runs.

    The broad catch is deliberate and not silent: any exception, including a walk's own bug, becomes
    an "exception" fault with a screenshot and the page source, and the gate then exits 1."""
    global WALK
    WALK = walk
    opened = len(browser.pages)
    try:
        action()
    except (Exception, SystemExit) as error:  # noqa: BLE001
        artifacts: list[str] = []
        detail = f"{type(error).__name__}: {str(error)[:600]}"
        # Only pages this walk opened; a name already used gets a number, so nothing is overwritten.
        page = next((p for p in reversed(browser.pages[opened:]) if not p.is_closed()), None)
        if page is not None:
            try:
                taken = len(list(S.glob(f"{walk}-failure*.png")))
                stem = f"{walk}-failure" + (f"-{taken + 1}" if taken else "")
                png, html = S / f"{stem}.png", S / f"{stem}.html"
                page.screenshot(path=str(png))
                html.write_text(redact(page.content(), secrets()))
                artifacts = [str(png), str(html)]
            except PlaywrightError as capture:
                detail += f" (page capture failed: {str(capture)[:200]})"
        note(False, f"{walk}: stopped: {detail}", fault=False)
        FAULTS.add(walk, "exception", detail, page.url if page is not None else "", artifacts)


def scan_server_logs() -> None:
    """Redact every provider key value in each server log, then record each crash it shows."""
    known = secrets()
    for drain in DRAINS:
        drain.join(timeout=5)
    # The Go server logs to <state-dir>/library.log; server-<port>.log holds only engine stdio.
    logs = [(port, log) for port, log in LOGS.items()]
    logs += [(port, S / f"state-{port}" / "library.log") for port in LOGS]
    for port, log in logs:
        if not log.exists():
            continue
        text = redact(log.read_text(errors="replace"), known)
        log.write_text(text)
        for crash in crashes(text):
            FAULTS.add(f"server-{port}", "server-log", crash, artifacts=[str(log)])


def engine_options() -> dict[str, dict[str, str]]:
    """The walk's two engines and their launch options."""
    home = Path.home() / "Library/Caches/ms-playwright"
    firefox = next((p for p in home.glob("firefox-*/**/firefox") if p.is_file()), None)
    chromium = os.environ.get("ISSUER_LIBRARY_CHROMIUM")
    return {
        "chromium": {"executable_path": chromium} if chromium else {},
        "firefox": {"executable_path": str(firefox)} if firefox else {},
    }


def single_main(workspace: Path, fixture: bool = False) -> int:
    """--single-run WORKSPACE: the per-run walk over a workspace holding one run, both engines."""
    global S, PY, SCOPE, RETAINED_FIXTURE
    RETAINED_FIXTURE = fixture
    S = Path(os.environ.get("FW_BROWSER_OUT") or tempfile.mkdtemp(prefix="issuer-library-single-"))
    S.mkdir(parents=True, exist_ok=True)
    PY = os.environ["FW_PYTHON"]
    SCOPE = f"offline: single-run walk over {workspace}; no provider called"
    server = None
    try:
        try:
            server, port = serve_free(workspace, R / "apps/issuer-library/engine")
            with sync_playwright() as driver:
                for name, options in engine_options().items():
                    browser = SignedBrowser(getattr(driver, name).launch(**options))
                    try:
                        attempt(
                            f"{name}-single-run",
                            browser,
                            lambda: single_run_walk(browser, name, port, workspace),  # noqa: B023
                        )
                    finally:
                        browser.close()
        except (Exception, SystemExit) as error:  # noqa: BLE001 - recorded below, never silent
            note(False, f"setup: stopped: {type(error).__name__}: {str(error)[:600]}", fault=False)
            FAULTS.add("setup", "exception", f"{type(error).__name__}: {str(error)[:600]}")
    finally:
        if server is not None:
            server.terminate()
            server.wait()
        scan_server_logs()
        passed = sum(ok for ok, _ in results)
        FAULTS.write(S / "faults.json", SCOPE, passed, secrets())
        print(
            f"{passed} passed, {len(results) - passed} failed,"
            f" {len(NOT_EXERCISABLE)} not exercisable"
        )
        print(f"faults: {S / 'faults.json'}")
    return int(bool(FAULTS.items) or passed != len(results))


def main(argv: list[str]) -> int:
    global S, PY
    if argv[:1] == ["--single-run"]:
        return single_main(Path(argv[1]).resolve(), argv[2:] == ["--retained-fixture"])
    S = Path(os.environ.get("FW_BROWSER_OUT") or tempfile.mkdtemp(prefix="issuer-library-browser-"))
    S.mkdir(parents=True, exist_ok=True)
    PY = os.environ["FW_PYTHON"]
    context = json.loads((R / "cases/cpdr-context-cutoff/context.json").read_text())
    context["run"].update(pathway="credit_snapshot", as_of="2025-03-31", cutoff="")
    context["identity"].update(issuer_name=ISSUER, issuer_id="nbg")
    (S / "context.json").write_text(json.dumps(context))
    issuer = S / "issuer"
    (issuer / "filings").mkdir(parents=True, exist_ok=True)
    (issuer / "annual.txt").write_text("Net sales were 100 and debt was 0.\n")
    (issuer / "filings/notes.md").write_text("Notes mature in 2030.\n")
    # The fake engine's CP-1 figures come from this fixture, so the data-flow check has a source.
    shutil.copy(HERE / "reader-fixture/CP-1.md", issuer / "figures.md")
    (issuer / "chart.png").write_bytes(b"\x89PNG")
    (issuer / ".DS_Store").write_bytes(b"\0")
    engines = engine_options()
    only = argv or list(engines)
    servers: list[subprocess.Popen[bytes]] = []
    try:
        try:
            library_server, library_port = serve_free(R, R / "apps/issuer-library/engine")
            servers.append(library_server)
            with sync_playwright() as driver:
                for name in only:
                    browser = SignedBrowser(getattr(driver, name).launch(**engines[name]))
                    walk_engine(browser, name, library_port, servers)
                    browser.close()
        except (Exception, SystemExit) as error:  # noqa: BLE001 - recorded below, never silent
            note(False, f"setup: stopped: {type(error).__name__}: {str(error)[:600]}", fault=False)
            FAULTS.add("setup", "exception", f"{type(error).__name__}: {str(error)[:600]}")
    finally:
        for server in servers:
            server.terminate()
        for server in servers:
            server.wait()
        scan_server_logs()
        passed = sum(ok for ok, _ in results)
        FAULTS.write(S / "faults.json", SCOPE, passed, secrets())
        print(f"{passed} passed, {len(results) - passed} failed")
        print(f"faults: {S / 'faults.json'}")
    return int(bool(FAULTS.items) or passed != len(results))


def walk_engine(browser: SignedBrowser, name: str, library_port: int, servers: list[Any]) -> None:
    workspace = S / f"ws-{name}"

    def library() -> None:
        # Via Any: real_workspace is untyped; typing it would pull its 75 statements into the gate.
        walk: Any = real_workspace
        walk(browser, name, library_port, full=name == "chromium")

    def fake_run() -> None:
        shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir()
        process, port = serve_free(workspace, HERE / "fake_engine", key="not-a-real-key")
        servers.append(process)
        new_run(browser, name, port, workspace, start=True)

    def stopped_run() -> None:
        stopped = S / "ws-stopped"
        shutil.rmtree(stopped, ignore_errors=True)
        stopped.mkdir()
        extra = {"FAKE_REJECT_AFTER": "1"}
        process, stopped_port = serve_free(
            stopped, HERE / "fake_engine", key="not-a-real-key", extra=extra
        )
        servers.append(process)
        new_run(browser, "stopped", stopped_port, stopped, start="stop")

    attempt(f"{name}-library", browser, library)
    attempt(f"{name}-run", browser, fake_run)
    if name == "chromium":
        attempt("stopped", browser, stopped_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
