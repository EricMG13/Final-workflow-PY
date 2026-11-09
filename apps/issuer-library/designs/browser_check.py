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
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import flow_check
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


def library_screening(page: Any, name: str, port: int) -> None:
    """A filter and a sort change the rows; a detail opens; Open run and Open report stay in app."""
    cases = KEY["filter_cases"]
    page.fill("#library-query", cases["c_search_issuer_name"]["filters"]["search"])
    note(
        row_ids(page) == cases["c_search_issuer_name"]["expected_ids"],
        f"{name}: a search narrows the rows to the key's",
    )
    page.click("#library-clear")
    page.click("#metric-filters summary")
    page.fill("#library-leverageMin", cases["a_leverage_min"]["filters"]["leverageMin"])
    note(
        sorted(row_ids(page)) == sorted(cases["a_leverage_min"]["expected_ids"]),
        f"{name}: a leverage minimum keeps the key's rows",
    )
    page.click("#library-clear")
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
    page.click("#library-clear")
    page.click("[data-library-select='tdg-002']")
    detail = page.locator("#run-detail")
    note(
        "Total carrying debt / EBITDA As Defined" in detail.inner_text()
        and "5.96\u00d7" in detail.inner_text(),
        f"{name}: a row's detail opens with its metric and basis",
    )
    detail.locator("a:has-text('Open report')").click()
    page.wait_for_selector("#report-preview")
    note("W-Reports" in page.url, f"{name}: Open report opens the report inside the app")
    page.goto(f"http://127.0.0.1:{port}/#W-Library/cases")
    page.reload()
    page.wait_for_selector("#library-results tbody tr")
    page.click("[data-library-select='tdg-002']")
    page.locator("#run-detail a:has-text('Open run')").click()
    page.wait_for_selector(".summary-lead")
    note("W-Overview" in page.url, f"{name}: Open run reaches the Overview")
    page.goto(f"http://127.0.0.1:{port}/#W-Library/cases")
    page.reload()
    page.wait_for_selector("#library-results tbody tr")


def library_and_report(page: Any, name: str, port: int) -> None:
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#library-results tbody tr", timeout=30000)
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
    used = page.locator("#module-head a", has_text="Used in")
    note(used.count() == 1, f"{name}: module output names the deliverables that used it")
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
    page.screenshot(path=str(S / f"{name}-report.png"))
    href = page.locator(".report-tools a[download]").get_attribute("href")
    note("download=1" in href and "sha256=" in href, f"{name}: original download link is pinned")
    page.locator(".built-from summary").first.click()
    page.locator(".built-from tbody a").first.click()
    page.wait_for_selector("#module-head h2")
    note("W-Reports" not in page.url, f"{name}: Built from opens the module output")


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


def every_section_renders(page: Any, name: str) -> None:
    problems = page.evaluate(EVERY_SECTION_JS)
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


def fitted_screens(page: Any, name: str, port: int) -> None:
    for width, height in ((1280, 600), (1536, 730)):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"http://127.0.0.1:{port}/#W-Overview/overview?c=tdg-002")
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


def chart_style(page: Any, name: str, port: int) -> None:
    """Charts follow the Untitled UI look: rounded data-ends, no tracks, pill grades, 12px cards."""
    run = "?c=tdg-002"
    seen: dict[str, str] = {}
    for route in ("#CP-1/performance", "#W-Overview/overview", "#CP-2/assessment"):
        page.goto(f"http://127.0.0.1:{port}/{route}{run}")
        page.wait_for_selector("#content .section-heading")
        seen.update({k: v for k, v in page.evaluate(CHART_STYLE).items() if v != "missing"})
    want = {
        "bar": "4px",
        "card": "12px",
        "track": "rgba(0, 0, 0, 0)",
        "barEnd": "4px",
        "rect": "4px",
        "grade": "999px",
    }
    note(seen == want, f"{name}: charts use rounded data-ends, no tracks and pill grades ({seen})")
    page.goto(f"http://127.0.0.1:{port}/#CP-1/performance{run}")
    page.wait_for_selector(".bars")


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


def main(argv: list[str]) -> int:
    global S, PY
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
    home = Path.home() / "Library/Caches/ms-playwright"
    firefox = next((p for p in home.glob("firefox-*/**/firefox") if p.is_file()), None)
    chromium = os.environ.get("ISSUER_LIBRARY_CHROMIUM")
    engines = {
        "chromium": {"executable_path": chromium} if chromium else {},
        "firefox": {"executable_path": str(firefox)} if firefox else {},
    }
    only = argv or list(engines)
    servers: list[subprocess.Popen[bytes]] = []
    try:
        try:
            servers.append(serve(R, 53901, R / "apps/issuer-library/engine"))
            with sync_playwright() as driver:
                for number, name in enumerate(only):
                    browser = SignedBrowser(getattr(driver, name).launch(**engines[name]))
                    walk_engine(browser, name, number, servers)
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


def walk_engine(browser: SignedBrowser, name: str, number: int, servers: list[Any]) -> None:
    workspace = S / f"ws-{name}"

    def library() -> None:
        # Via Any: real_workspace is untyped; typing it would pull its 75 statements into the gate.
        walk: Any = real_workspace
        walk(browser, name, 53901, full=name == "chromium")

    def fake_run() -> None:
        shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir()
        port = 53902 + number
        servers.append(serve(workspace, port, HERE / "fake_engine", key="not-a-real-key"))
        new_run(browser, name, port, workspace, start=True)

    def stopped_run() -> None:
        stopped = S / "ws-stopped"
        shutil.rmtree(stopped, ignore_errors=True)
        stopped.mkdir()
        extra = {"FAKE_REJECT_AFTER": "1"}
        servers.append(
            serve(stopped, 53910, HERE / "fake_engine", key="not-a-real-key", extra=extra)
        )
        new_run(browser, "stopped", 53910, stopped, start="stop")

    attempt(f"{name}-library", browser, library)
    attempt(f"{name}-run", browser, fake_run)
    if name == "chromium":
        attempt("stopped", browser, stopped_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
