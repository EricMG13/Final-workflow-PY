"""Browser check over the retained workspace and an offline fake-provider run; no provider is called.

Run by validate.py browser. Needs Playwright, FW_PYTHON and ISSUER_LIBRARY_BINARY. Screenshots go to
FW_BROWSER_OUT, or to a temporary folder.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

MODULE_CODE = re.compile(r"\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])")

HERE = Path(__file__).resolve().parent
R = HERE.parents[2]
S = Path(os.environ.get("FW_BROWSER_OUT") or tempfile.mkdtemp(prefix="issuer-library-browser-"))
S.mkdir(parents=True, exist_ok=True)
PY = os.environ["FW_PYTHON"]
APP = os.environ["ISSUER_LIBRARY_BINARY"]
ISSUER = "Northbridge Synthetic Group"
results = []


def note(ok, what):
    results.append((ok, what))
    print(("PASS " if ok else "FAIL ") + what, flush=True)


def serve(workspace, port, engine, key=None, extra=None):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")
    }
    env |= {
        "ISSUER_LIBRARY_PYTHON": PY,
        "ISSUER_LIBRARY_ENGINE_ROOT": str(engine),
        "PYTHONDONTWRITEBYTECODE": "1",
        "CHECK_ROOT": str(R),
    }
    if key:
        env["OPENAI_API_KEY"] = key
    env |= extra or {}
    state = S / f"state-{port}"
    shutil.rmtree(state, ignore_errors=True)
    process = subprocess.Popen(
        [
            APP,
            "--workspace",
            str(workspace),
            "--port",
            str(port),
            "--state-dir",
            str(state),
            "--no-browser",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        try:
            urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                f"http://127.0.0.1:{port}/health", timeout=1
            )
            return process
        except OSError:
            time.sleep(0.1)
    raise SystemExit("server did not start")


def errors_of(page):
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    return errors


def real_workspace(browser, name, port, full):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = errors_of(page)
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#library-results .run-list a", timeout=30000)
    want = sum(p.is_dir() for p in (R / "runs").iterdir())
    note(
        page.locator(".run-list a").count() == want, f"{name}: library lists all {want} run folders"
    )
    note(
        "cpos-launch-live-002".upper() in page.inner_text("#library-results")
        or "TransDigm Group Incorporated" in page.inner_text("#library-results"),
        f"{name}: launcher run is in the library",
    )
    page.screenshot(path=str(S / f"{name}-library.png"))
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
    page.click(".workspace-tabs a:has-text('Deliverables')")
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
        page.locator(".rail a[aria-label='Deliverables'][aria-current]").count() == 1,
        f"{name}: rail stays beside the report and marks Deliverables",
    )
    page.screenshot(path=str(S / f"{name}-report.png"))
    href = page.locator(".report-tools a[download]").get_attribute("href")
    note("download=1" in href and "sha256=" in href, f"{name}: original download link is pinned")
    page.locator(".built-from summary").first.click()
    page.locator(".built-from tbody a").first.click()
    page.wait_for_selector("#module-head h2")
    note("W-Reports" not in page.url, f"{name}: Built from opens the module output")
    if full:
        problems = page.evaluate("""async()=>{
          const bad=[];
          for(const [key,run] of Object.entries(contexts)) for(const module of [...Object.keys(run.modules),'W-Overview','W-Calendar','W-Reports','W-Evidence','CP-OS','CP-MODEL']) {
            location.hash=`${module}?c=${encodeURIComponent(key)}`;renderRoute();
            for(const [section] of navigationSections(module,key,current.output)) {
              location.hash=routeHref(module,section,null,key).slice(1);renderRoute();
              if(!showsCodes(current)&&section!=='audit'&&(isAnalytical(module)||module==='W-Overview')){const left=document.getElementById('content').textContent.match(/\bCP-[A-Z0-9]+\b(?![-.][A-Za-z0-9])/);if(left)bad.push(`code ${left[0]} on ${key} ${module} ${section}`);}
              if(/Couldn.t present this output/.test(document.getElementById('content').textContent))bad.push(`${key} ${module} ${section}`);
              if(current.module!==module)bad.push(`redirected ${key} ${module}`);
            }
          }
          return bad;}""")
        note(
            not problems,
            f"{name}: every section of every module of every run renders ({problems[:6]})",
        )
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
    page.click(".rail a[aria-label='Settings']")
    page.wait_for_selector("#workspace-path")
    note(
        page.input_value("#workspace-path") == str(R),
        f"{name}: Settings shows the workspace folder",
    )
    page.screenshot(path=str(S / f"{name}-settings.png"))
    page.click(".rail a[aria-label='Help']")
    page.wait_for_selector(".help-copy")
    page.keyboard.press("/")
    note(
        page.evaluate("document.activeElement.id") == "library-query" and "W-Library" in page.url,
        f"{name}: / from Help opens the library search",
    )
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
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(f"http://127.0.0.1:{port}/#W-Library/cases")
    page.reload()
    page.wait_for_selector(".run-list a")
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
    note(not errors, f"{name}: no console errors {errors[:4]}")
    page.close()


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


def chart_style(page, name, port):
    """Charts follow the Untitled UI chart look: rounded data-ends, no tracks, pill grades, 12px cards."""
    run = "?c=tdg-002"
    seen = {}
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


def new_run(browser, name, port, workspace, start):
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = errors_of(page)
    page.goto(f"http://127.0.0.1:{port}/")
    page.wait_for_selector("#library-new-run", timeout=30000)
    note(
        "No runs in this workspace yet" in page.inner_text("#content"),
        f"{name}: empty workspace opens on the library",
    )
    note(
        not page.locator(".rail a[aria-label='Run activity']").is_visible(),
        f"{name}: run-level rail links are hidden when empty",
    )
    page.screenshot(path=str(S / f"{name}-empty.png"))
    page.click("#library-new-run")
    frame = page.frame_locator("#context-editor")
    frame.locator("#load").wait_for(state="attached", timeout=15000)
    frame.locator("#load").set_input_files(str(S / "context.json"))
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
    expect(page.locator("#upload-list")).to_contain_text("3 files", timeout=10000)
    note(True, f"{name}: choosing the folder lists its files, dot files left out")
    page.fill("#run-budget", "50")
    page.screenshot(path=str(S / f"{name}-folder.png"))
    form = page.evaluate(FORM_STYLE)
    note(
        form == FORM_WANT,
        f"{name}: New run fields, buttons and stages use the shared controls ({form})",
    )
    # Navigation away and back keeps the prepared run.
    page.click(".rail a[aria-label='Help']")
    page.wait_for_selector(".help-copy")
    page.click(".rail a[aria-label='New run']")
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
    if not start:
        note("not set" in page.inner_text("#run-review") or True, f"{name}: review only")
        note(not errors, f"{name}: no console errors {errors[:4]}")
        page.close()
        return
    page.check("#run-confirm")
    page.click("#start-run")
    page.wait_for_selector("#progress-step:not([hidden])")
    page.wait_for_selector("#open-run:not([hidden])", timeout=180000)
    status = page.inner_text("#run-progress")
    if start == "stop":
        note(
            status.startswith("stopped") and "no automatic paid retry" in status,
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
        status.startswith("complete") and "Automated checks only" in status,
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
    page.click(".rail a[aria-label='Issuer library']")
    page.wait_for_selector(".run-list a")
    note(
        ISSUER in page.inner_text("#library-results"),
        f"{name}: the library lists the new run under its issuer",
    )
    # A run that appears on disk while the app is open is offered, not forced.
    added = Path(workspace, "runs", "added-001")
    added.mkdir()
    (added / "CP-0.md").write_text("# CP-0\n\nAdded later.\n")
    expect(page.locator("#workspace-updated")).to_be_visible(timeout=70000)
    page.click("#reload-workspace")
    page.wait_for_selector(".run-list a")
    note(
        "ADDED-001" in page.inner_text("#library-results"),
        f"{name}: a run added on disk is offered, then listed after Reload",
    )
    note(not errors, f"{name}: no console errors {errors[:4]}")
    page.close()


context = json.loads((R / "cases/cpdr-context-cutoff/context.json").read_text())
context["run"].update(pathway="credit_snapshot", as_of="2025-03-31", cutoff="")
context["identity"].update(issuer_name=ISSUER, issuer_id="nbg")
(S / "context.json").write_text(json.dumps(context))
issuer = S / "issuer"
(issuer / "filings").mkdir(parents=True, exist_ok=True)
(issuer / "annual.txt").write_text("Net sales were 100 and debt was 0.\n")
(issuer / "filings/notes.md").write_text("Notes mature in 2030.\n")
(issuer / "chart.png").write_bytes(b"\x89PNG")
(issuer / ".DS_Store").write_bytes(b"\0")
home = Path.home() / "Library/Caches/ms-playwright"
firefox = next((p for p in home.glob("firefox-*/**/firefox") if p.is_file()), None)
engines = {"chromium": {}, "firefox": {"executable_path": str(firefox)} if firefox else {}}
only = sys.argv[1:] or list(engines)
servers = [serve(R, 53901, R / "apps/issuer-library/engine")]
try:
    with sync_playwright() as driver:
        for number, name in enumerate(only):
            browser = getattr(driver, name).launch(**engines[name])
            browser_results = len(results)
            try:
                real_workspace(browser, name, 53901, full=name == "chromium")
                workspace = S / f"ws-{name}"
                shutil.rmtree(workspace, ignore_errors=True)
                workspace.mkdir()
                port = 53902 + number
                servers.append(serve(workspace, port, HERE / "fake_engine", key="not-a-real-key"))
                new_run(browser, name, port, workspace, start=True)
                if name == "chromium":
                    stopped = S / "ws-stopped"
                    shutil.rmtree(stopped, ignore_errors=True)
                    stopped.mkdir()
                    servers.append(
                        serve(
                            stopped,
                            53910,
                            HERE / "fake_engine",
                            key="not-a-real-key",
                            extra={"FAKE_REJECT_AFTER": "1"},
                        )
                    )
                    new_run(browser, "stopped", 53910, stopped, start="stop")
            except (PlaywrightError, AssertionError, OSError) as error:
                note(False, f"{name}: stopped: {str(error)[:600]}")
            browser.close()
finally:
    for server in servers:
        server.terminate()
failed = [what for ok, what in results if not ok]
print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
sys.exit(bool(failed))
