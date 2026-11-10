"""Answer key: a loaded context keeps every entered value (R-SB2 instrument defect).

context-form.html drew the deal-term `instrument` as a closed six-value <select>, so a loaded
"ABL revolver" or "6.00% senior secured notes due 2033" came out blank. The keys here are the
case files and a hand-written term list, never the form. The output is the `cpos:context`
message the app receives on #use-context, which it later posts to /api/runs/review.
"""

from __future__ import annotations

import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from issuer_library_browser import ROOT, WEB, json_reply, open_app, serve
from playwright.sync_api import expect

pytestmark = pytest.mark.browser

DESIGNS = ROOT / "apps/issuer-library/designs"
sys.path.insert(0, str(DESIGNS))
_spec = importlib.util.spec_from_file_location("live_check", DESIGNS / "live_check.py")
live_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_check)

CAPTURE = (
    "if(window===window.top){window.__ctx=[];window.addEventListener('message',"
    "e=>{if(e.data&&e.data.type==='cpos:context')window.__ctx.push(e.data);});}"
)
C2 = ROOT / "cases/live-mattress-firm-2014/c2/context.json"
B_LIVE = ROOT / "cases/live-tdg-fy2024/b-live/context.json"
A_LIVE = ROOT / "cases/live-tdg-fy2024/a-live/context.json"
CASES = sorted(
    {*ROOT.glob("cases/*/*/context.json"), *ROOT.glob("cases/*/context.json"), C2, B_LIVE, A_LIVE}
)


def through_the_editor(browser: Any, path: Path) -> tuple[dict[str, Any], str]:
    """Load a context file as live_check.fill_form does, press Use, return (context, load note)."""
    screen = open_app(browser, "W-NewRun/run", init=CAPTURE)
    try:
        frame = screen.page.frame_locator("#context-editor")
        frame.locator("#load").wait_for(state="attached", timeout=15000)
        frame.locator("#load").set_input_files(str(path))
        frame.locator("#loadmsg").filter(has_text=re.compile(r"^Loaded")).wait_for(timeout=15000)
        note = frame.locator("#loadmsg").inner_text()
        screen.page.click("#use-context")
        screen.page.wait_for_function("window.__ctx.length>0", timeout=15000)
        sent: dict[str, Any] = screen.page.evaluate("window.__ctx.at(-1)")
        assert screen.errors == []
        return sent["context"], note
    finally:
        screen.close()


def leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f"{path}[{index}]")
    else:
        yield path, value


def test_c2_keeps_its_abl_revolver_instrument_and_the_second_term(browser: Any) -> None:
    sent, _ = through_the_editor(browser, C2)
    first, second = sent["deal_terms"][:2]
    assert len(sent["deal_terms"]) == 2
    key_first = {
        "facility_id": "abl-revolver",
        "instrument": "ABL revolver",
        "currency": "USD",
        "size_m": "125",
        "tenor_years": "5",
        "talk_spread_bps_low": "125",
        "talk_spread_bps_high": "175",
        "call_protection": "Prepayable at par",
        "as_of": "2014-09-11",
    }
    key_second = {
        "facility_id": "term-loan-b",
        "instrument": "Term loan B",
        "currency": "USD",
        "size_m": "720",
        "tenor_years": "7",
        "floor_pct": "1.00",
        "call_protection": "101 soft call, 6 months",
        "as_of": "2014-09-11",
    }
    assert {k: first.get(k) for k in key_first} == key_first
    assert {k: second.get(k) for k in key_second} == key_second


def test_a_free_text_instrument_is_kept_exactly(browser: Any) -> None:
    sent, note = through_the_editor(browser, B_LIVE)
    term = sent["deal_terms"][0]
    assert term["instrument"] == "6.00% senior secured notes due 2033"
    assert (term["facility_id"], term["size_m"], term["coupon_pct"], term["maturity"]) == (
        "tdg-6-00-secured-2033",
        "1500",
        "6.00",
        "2033-01-15",
    )
    assert "unknown value" not in note


@pytest.mark.parametrize(
    "case", CASES, ids=lambda p: p.relative_to(ROOT / "cases").parent.as_posix()
)
def test_every_entered_value_of_a_case_context_survives_the_editor(
    browser: Any, case: Path
) -> None:
    saved = json.loads(case.read_text("utf-8"))
    sent, note = through_the_editor(browser, case)
    out = dict(leaves(sent))
    lost = {
        path: (value, out.get(path, "<absent>"))
        for path, value in leaves(saved)
        if value not in ("", None, []) and out.get(path, "<absent>") != value
    }
    assert lost == {}, note


def test_fill_form_refuses_while_the_form_shows_an_unknown_value_note(
    browser: Any, tmp_path: Path
) -> None:
    """A closed-list loss must stop the walk before Start, not ride along as a silent note."""
    frame = (
        '<input id="load" type="file"><div id="loadmsg"></div><script>'
        "document.getElementById('load').onchange=()=>{document.getElementById('loadmsg')"
        ".textContent='Loaded context.json. 1 note(s): deal_terms[0].instrument: unknown value "
        '"ABL revolver", left blank\';};</script>'
    )
    shell = (
        '<button id="library-new-run">New</button><div id="context-readiness">'
        'Required fields complete</div><button id="use-context">Use</button>'
        '<div id="source-step" hidden>Sources</div>'
        '<input id="run-sources" type="file" webkitdirectory>'
        '<div id="upload-list"></div><select id="run-model"><option>cfg</option></select>'
        '<input id="run-budget"><details class="run-advanced"><summary>More</summary>'
        '<input id="run-modules"></details><button id="review-run">Review</button>'
        '<div id="review-step" hidden>Review</div><div id="new-run-message"></div><script>'
        "document.getElementById('use-context').onclick=()=>{"
        "document.getElementById('source-step').hidden=false};"
        "document.getElementById('run-sources').onchange=e=>{"
        "document.getElementById('upload-list').textContent=e.target.files.length+' files'};"
        "document.getElementById('review-run').onclick=()=>{"
        "document.getElementById('review-step').hidden=false};</script>"
        f'<iframe id="context-editor" srcdoc="{html.escape(frame, quote=True)}"></iframe>'
    )
    context = tmp_path / "context.json"
    context.write_text("{}", encoding="utf-8")
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "a.txt").write_text("x", encoding="utf-8")
    page = browser.new_page()
    page.set_default_timeout(3000)
    page.route(
        "http://127.0.0.1:1/**",
        lambda route: route.fulfill(body=shell, content_type="text/html"),
    )
    page.goto("http://127.0.0.1:1/")
    editor = page.frame_locator("#context-editor")
    editor.locator("#load").set_input_files(str(context))
    assert "unknown value" in editor.locator("#loadmsg").inner_text()  # the fixture shows the note
    args = SimpleNamespace(
        port=1, context=context, sources=sources, config="cfg", cap=1, modules="CP-1"
    )
    try:
        with pytest.raises(live_check.Refusal, match="unknown value"):
            live_check.fill_form(page, args)
    finally:
        page.close()


# No entered value may be silently blanked or defaulted. The server (context.py) types agency,
# outlook and focus_module as plain str, so those must keep any text; it enumerates every other
# field below (Literal/PathwayId/bool), so an out-of-list value must refuse the whole load.
FULL = ROOT / "cases/context/primary-full.json"
FREE_TEXT = [
    ("ratings[0].agency", "Egan-Jones"),
    ("ratings[0].outlook", "Negative watch"),
    ("research_questions[0].focus_module", "CP-XYZ"),
]
CLOSED = [
    ("run.run_type", "tertiary"),
    ("run.pathway", "bogus_path"),
    ("run.case_kind", "hypothetical"),
    ("identity.issue_classification", "junk_grade"),
    ("identity.listed_equity", "maybe"),
    ("valuation.peer_source", "some_peers"),
    ("valuation.basis", "vibes"),
    ("valuation.issuer_market.ebitda_basis", "LTM+1"),
    ("valuation.user_multiple.basis", "FWD"),
    ("attachments.legal_documents", "sketch"),
    ("attachments.management_bridge", "sometimes"),
    ("quotes[0].kind", "rumoured"),
    ("ratings[0].scope", "group"),
]


def with_values(changes: dict[str, Any], tmp_path: Path) -> Path:
    """A copy of the full context with entered values replaced; every path must exist."""
    saved = json.loads(FULL.read_text("utf-8"))
    saved["identity"]["issue_classification"] = "high_yield"  # older file; the form would note it
    for path, value in changes.items():
        node: Any = saved
        *parents, last = path.replace("]", "").replace("[", ".").split(".")
        for step in parents:
            node = node[int(step)] if step.isdigit() else node[step]
        assert last in node, path
        node[int(last) if last.isdigit() else last] = value
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(saved), encoding="utf-8")
    return changed


def value_at(sent: dict[str, Any], path: str) -> Any:
    return dict(leaves(sent))[path]


@pytest.mark.parametrize(("path", "value"), FREE_TEXT, ids=[p for p, _ in FREE_TEXT])
def test_a_free_text_field_keeps_any_entered_value(
    browser: Any, tmp_path: Path, path: str, value: str
) -> None:
    sent, note = through_the_editor(browser, with_values({path: value}, tmp_path))
    assert value_at(sent, path) == value, note


def load_and_use(browser: Any, changed: Path) -> tuple[str, str, list[dict[str, Any]]]:
    """Load a file into the real editor; return the load note, its class and what Use sent."""
    screen = open_app(browser, "W-NewRun/run", init=CAPTURE)
    try:
        frame = screen.page.frame_locator("#context-editor")
        frame.locator("#load").wait_for(state="attached", timeout=15000)
        frame.locator("#load").set_input_files(str(changed))
        message = frame.locator("#loadmsg")
        message.filter(has_text=re.compile(r"\S")).wait_for(timeout=15000)
        text, kind = message.inner_text(), message.get_attribute("class")
        screen.page.click("#use-context", force=True)
        screen.page.wait_for_timeout(500)
        sent: list[dict[str, Any]] = screen.page.evaluate("window.__ctx")
        assert screen.errors == []
        return text, kind or "", sent
    finally:
        screen.close()


def assert_refused(path: str, value: str, result: tuple[str, str, list[dict[str, Any]]]) -> None:
    text, kind, sent = result
    assert path in text and value in text, text
    assert not text.startswith("Loaded") and kind == "bad", (kind, text)
    # Nothing from the refused file may reach the posted context.
    assert [m["context"]["identity"]["issuer_name"] for m in sent] in ([], [""])


@pytest.mark.parametrize(("path", "value"), CLOSED, ids=[p for p, _ in CLOSED])
def test_an_out_of_list_value_in_a_closed_field_refuses_the_load_visibly(
    browser: Any, tmp_path: Path, path: str, value: str
) -> None:
    assert_refused(path, value, load_and_use(browser, with_values({path: value}, tmp_path)))


# Server-valid contexts the form narrows. Server: tenor and talk are plain str on any run type
# (context.py: only `primary` needs a deal row), so the value survives or the load is refused.
# Skipped because the server's own model/validation rejects the same input: rows over a cap
# (_MAX_* equal the form's), issuer_trading without a listed issuer, a non-object assumption;
# "issue_classification: not stated" drops nothing (an empty value is valid).
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenor_years", "7"),
        ("talk_spread_bps_low", "325"),
        ("talk_spread_bps_high", "350"),
        ("talk_oid_low", "99.0"),
        ("talk_oid_high", "99.5"),
    ],
)
def test_tenor_and_talk_on_a_non_primary_run_survive_or_the_load_is_refused(
    browser: Any, tmp_path: Path, field: str, value: str
) -> None:
    changed = with_values({"run.run_type": "secondary"}, tmp_path)
    saved = json.loads(changed.read_text("utf-8"))
    assert saved["deal_terms"][0][field] == value  # the key: entered in the file
    text, kind, sent = load_and_use(browser, changed)
    if text.startswith("Loaded"):
        assert sent[-1]["context"]["deal_terms"][0][field] == value, text
    else:
        assert_refused(f"deal_terms[0].{field}", value, (text, kind, sent))


def real_fill_form(browser: Any, context: Path, tmp_path: Path) -> None:
    """live_check.fill_form against the real index.html and context form."""
    page = browser.new_context().new_page()
    page.set_default_timeout(5000)
    store = {k: {} for k in ("runs", "outputs", "inputs", "pins", "handoffs")}
    serve(
        page,
        {
            "/api/catalogue": json_reply(
                {"workspace": "/r", "policy_locked": False, "issues": [], "real": []}
            ),
            "/api/workspace": json_reply(
                store | {"reports": [], "models": [], "visuals": [], "issues": []}
            ),
            "/api/runs/list": json_reply([]),
        },
    )
    page.route(  # registered after serve(), so it answers the root page first
        "http://127.0.0.1:1/",
        lambda route: route.fulfill(
            body=(WEB / "index.html").read_bytes(), content_type="text/html"
        ),
    )
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "a.txt").write_text("x", encoding="utf-8")
    args = SimpleNamespace(
        port=1, context=context, sources=sources, config="cfg", cap=1, modules="CP-1"
    )
    try:
        live_check.fill_form(page, args)
    finally:
        page.context.close()


def test_fill_form_refuses_an_out_of_list_value_through_the_real_form(
    browser: Any, tmp_path: Path
) -> None:
    """Whatever wording the form's note has, a dropped or refused value must stop the walk."""
    changed = with_values({"run.case_kind": "hypothetical"}, tmp_path)
    with pytest.raises(live_check.Refusal):
        real_fill_form(browser, changed, tmp_path)


def test_fill_form_refuses_with_the_note_when_the_form_rejects_the_file(
    browser: Any, tmp_path: Path
) -> None:
    rejected = tmp_path / "rejected.json"
    rejected.write_text(json.dumps({"schema": "context/9"}), encoding="utf-8")
    with pytest.raises(live_check.Refusal, match=r"Not loaded.*context/9"):
        real_fill_form(browser, rejected, tmp_path)


def test_the_release_sync_regenerates_exactly_the_committed_context_form(tmp_path: Path) -> None:
    """packaging/build.py runs sync_assets.py, which rebuilds web/context-form.html from
    docs/templates/context-form.html; if they differ a release build undoes the form's fixes.
    The script runs unchanged in a scratch copy of what it reads, so nothing here is written."""
    app = tmp_path / "apps/issuer-library"
    (app / "packaging").mkdir(parents=True)
    (app / "web").mkdir()
    shutil.copy(DESIGNS.parent / "packaging/sync_assets.py", app / "packaging")
    for name in ("context-embed.css", "context-embed.js"):
        shutil.copy(DESIGNS.parent / "web" / name, app / "web")
    shutil.copytree(ROOT / "src/deploy_vii/assets", tmp_path / "src/deploy_vii/assets")
    (tmp_path / "docs/templates").mkdir(parents=True)
    shutil.copy(ROOT / "docs/templates/context-form.html", tmp_path / "docs/templates")
    (tmp_path / "examples/issuer-library").mkdir(parents=True)
    shutil.copy(ROOT / "examples/issuer-library/catalog.json", tmp_path / "examples/issuer-library")
    subprocess.run(
        [sys.executable, "-I", str(app / "packaging/sync_assets.py")], check=True, cwd=tmp_path
    )
    committed = (DESIGNS.parent / "web/context-form.html").read_text()
    assert (app / "web/context-form.html").read_text() == committed


# Conditional sections: build() drops these on load although they were entered. The server
# refuses every one of these files, so the form must refuse the load, naming field and value.
PEER = {"name": "Sealy", "ticker": "ZZ", "ev_m": "", "ebitda_m": "", "as_of": "", "source": ""}
PEER_FIG = PEER | {"ev_m": "5400", "ebitda_m": "600", "as_of": "2014-06-30", "source": "10-K"}
PREC = {
    "target": "Tempur",
    "acquirer": "A",
    "date": "2013-01-01",
    "ev_m": "100",
    "ebitda_m": "10",
    "source": "PR",
}
CONDITIONAL = {
    "peers-source-none": (
        {"valuation.peer_source": "none", "valuation.peers": [PEER]},
        "valuation.peers",
        "Sealy",
    ),
    "peers-source-cp_dr_public": (
        {"valuation.peer_source": "cp_dr_public", "valuation.peers": [PEER]},
        "valuation.peers",
        "Sealy",
    ),
    "user_list-peer-figure": (
        {"valuation.peer_source": "user_list", "valuation.peers": [PEER_FIG]},
        "valuation.peers[0].ev_m",
        "5400",
    ),
    "precedents-basis-auto": (
        {"valuation.basis": "auto", "valuation.precedents": [PREC]},
        "valuation.precedents",
        "Tempur",
    ),
    "market-cap-basis-auto": (
        {"valuation.basis": "auto", "valuation.issuer_market.market_cap_m": "900"},
        "valuation.issuer_market.market_cap_m",
        "900",
    ),
    "user-multiple-basis-auto": (
        {"valuation.basis": "auto", "valuation.user_multiple.value": "7.5"},
        "valuation.user_multiple.value",
        "7.5",
    ),
    "ticker-unlisted": (
        {"identity.listed_equity": False, "identity.ticker": "MFRM"},
        "identity.ticker",
        "MFRM",
    ),
    "issuer_trading-unlisted": (
        {"identity.listed_equity": False, "valuation.basis": "issuer_trading"},
        "valuation.basis",
        "issuer_trading",
    ),
    # A JSON null is not a boolean; the server refuses it, the form turned it into false.
    "attachment-null": ({"attachments.prior_case": None}, "attachments.prior_case", "null"),
    "listed_equity-null": ({"identity.listed_equity": None}, "identity.listed_equity", "null"),
}


def c2_variant(edits: dict[str, Any], tmp_path: Path) -> tuple[Path, bytes]:
    saved = json.loads(C2.read_text("utf-8"))
    for path, value in edits.items():
        *parents, last = path.split(".")
        node = saved
        for step in parents:
            node = node[step]
        node[last] = value
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(saved), encoding="utf-8")
    return changed, changed.read_bytes()


@pytest.mark.parametrize("case", CONDITIONAL)
def test_a_value_the_form_cannot_hold_refuses_the_load_visibly(
    browser: Any, tmp_path: Path, case: str
) -> None:
    from deploy_workflow.context import load_context  # the key: the server refuses the file

    edits, path, value = CONDITIONAL[case]
    changed, raw = c2_variant(edits, tmp_path)
    with pytest.raises(Exception, match=r"(?s).+"):
        load_context(raw)
    assert_refused(path, value, load_and_use(browser, changed))


# --- Load invariant (PR B): what the form sends is what the file held, or the load is refused. ---
# The key is the file itself and the server's verdict (load_context), never the form. Comparison:
# every non-blank leaf of the file (text stripped; JSON null is a value) must come back with the
# same type and value; Python's `True == 1` must not hide a change.


def main_checkout() -> Path | None:
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(common).parent


def context_files() -> list[Any]:
    """Every context/1 JSON under <worktree>/cases and the main checkout's .superpowers/live."""
    main = main_checkout()
    live = main / ".superpowers/live" if main else None
    found: dict[Path, str] = {}
    roots = [(ROOT / "cases", "cases")] + ([(live, "live")] if live and live.is_dir() else [])
    for base, label in roots:
        for path in sorted(base.rglob("*.json")):
            try:
                doc = json.loads(path.read_text("utf-8"))
            except (ValueError, OSError):
                continue  # not a readable JSON document, so not a context file
            if isinstance(doc, dict) and doc.get("schema") == "context/1":
                found.setdefault(path.resolve(), f"{label}/{path.relative_to(base).as_posix()}")
    params = [pytest.param(p, id=i) for p, i in found.items()]
    if not (live and live.is_dir()):
        reason = "the main checkout has no .superpowers/live folder (or git cannot name it)"
        params.append(pytest.param(None, id="live-folder-absent", marks=pytest.mark.skip(reason)))
    return params


def lost_leaves(saved: Any, sent: Any) -> dict[str, Any]:
    """File leaves that are non-blank (text stripped) and not sent with the same type and value."""
    out = dict(leaves(sent))
    lost: dict[str, Any] = {}
    for path, value in leaves(saved):
        want = value.strip() if isinstance(value, str) else value
        if isinstance(want, str) and want == "":
            continue
        got = out.get(path, "<absent>")
        if type(got) is not type(want) or got != want:
            lost[path] = (want, got)
    return lost


def server_refuses(raw: bytes) -> bool:
    from deploy_workflow.context import ContextRefused, load_context

    try:
        load_context(raw)
    except ContextRefused:
        return True
    return False


def load_then_use(browser: Any, path: Path) -> tuple[str, str, dict[str, Any] | None]:
    """Load a file into the real editor; return note, its class and the context Use sent."""
    note, kind, sent = load_and_use(browser, path)
    context = sent[-1]["context"] if sent and note.startswith("Loaded") else None
    return note, kind, context


@pytest.mark.parametrize("case", context_files())
def test_every_context_file_keeps_its_values_or_is_refused(browser: Any, case: Path) -> None:
    raw = case.read_bytes()
    saved = json.loads(raw)
    note, kind, context = load_then_use(browser, case)
    if not server_refuses(raw):
        assert note.startswith("Loaded") and context is not None, note
        assert lost_leaves(saved, context) == {}, note
    elif note.startswith("Not loaded"):
        assert kind == "bad", (kind, note)
    else:
        assert context is not None, note
        assert lost_leaves(saved, context) == {}, note


BLANK_PEER = {"name": "", "ticker": "", "ev_m": "", "ebitda_m": "", "as_of": "", "source": ""}
BLANK_PREC = {k: "" for k in PREC}


def deal_rows(count: int) -> list[dict[str, Any]]:
    """C2's two deal rows extended to `count` rows, each otherwise valid for the form."""
    rows = json.loads(C2.read_text("utf-8"))["deal_terms"]
    template = rows[0]
    rows += [template | {"facility_id": f"t{i}"} for i in range(len(rows), count)]
    return rows


def with_row(rows: list[dict[str, Any]], index: int, **cells: Any) -> list[dict[str, Any]]:
    rows[index] = rows[index] | cells
    return rows


PEERS_SECOND = (
    {
        "valuation.peer_source": "none",
        "valuation.peers": [BLANK_PEER, BLANK_PEER | {"name": "Sealy"}],
    },
    "valuation.peers[1].name",
    "Sealy",
)
CANNOT_HOLD = {
    "peers-second-row-only": PEERS_SECOND,
    "precedents-second-row-only": (
        {
            "valuation.basis": "auto",
            "valuation.precedents": [BLANK_PREC, BLANK_PREC | {"target": "Tempur"}],
        },
        "valuation.precedents[1].target",
        "Tempur",
    ),
    "21-deal-rows": (
        {"deal_terms": deal_rows(21)},
        "deal_terms[20].facility_id",
        "t20",
    ),
    "11-questions": (
        {"research_questions": [{"text": f"Q{i}?", "focus_module": ""} for i in range(11)]},
        "research_questions[10].text",
        "Q10?",
    ),
    "extra-identity-key": ({"identity.nickname": "Sleepy"}, "identity.nickname", "Sleepy"),
    "extra-cp2d-sub-key": (
        {"assumptions.cp2d": {"horizon_months": "18", "rationale": "r", "extra": "x"}},
        "assumptions.cp2d.extra",
        "x",
    ),
    "size_m-as-json-number": (
        {"deal_terms": with_row(deal_rows(2), 0, size_m=125)},
        "deal_terms[0].size_m",
        "125",
    ),
    # vis() throws on PATHWAYS[''] today, so no note appears at all.
    "pathway-empty": ({"run.pathway": ""}, "run.pathway", ""),
    "deal-as_of-not-iso": (
        {"deal_terms": with_row(deal_rows(2), 0, as_of="2014/09/11")},
        "deal_terms[0].as_of",
        "2014/09/11",
    ),
}


@pytest.mark.parametrize("case", CANNOT_HOLD)
def test_a_value_the_form_cannot_hold_refuses_the_load_visibly_anywhere(
    browser: Any, tmp_path: Path, case: str
) -> None:
    edits, path, value = CANNOT_HOLD[case]
    changed, raw = c2_variant(edits, tmp_path)
    assert server_refuses(raw)  # the key: the server refuses the file
    assert_refused(path, value, load_and_use(browser, changed))


def test_surrounding_spaces_are_trimmed_not_refused(browser: Any, tmp_path: Path) -> None:
    rows = with_row(deal_rows(2), 0, instrument="  ABL revolver  ")
    changed, _ = c2_variant({"deal_terms": rows}, tmp_path)
    sent, note = through_the_editor(browser, changed)
    assert sent["deal_terms"][0]["instrument"] == "ABL revolver", note


def test_a_refused_load_leaves_the_form_as_it_was(browser: Any, tmp_path: Path) -> None:
    """Load C2, then a file the form cannot hold, then Use: the first file's context is sent."""
    kept, _ = through_the_editor(browser, C2)
    edits, _path, _value = PEERS_SECOND
    changed, _ = c2_variant(edits, tmp_path)
    screen = open_app(browser, "W-NewRun/run", init=CAPTURE)
    try:
        frame = screen.page.frame_locator("#context-editor")
        frame.locator("#load").wait_for(state="attached", timeout=15000)
        frame.locator("#load").set_input_files(str(C2))
        message = frame.locator("#loadmsg")
        message.filter(has_text=re.compile(r"^Loaded")).wait_for(timeout=15000)
        first = message.inner_text()
        frame.locator("#load").set_input_files(str(changed))
        expect(message).not_to_have_text(first, timeout=15000)  # the second file was answered
        second = message.inner_text()
        screen.page.click("#use-context", force=True)
        screen.page.wait_for_function("window.__ctx.length>0", timeout=15000)
        sent: dict[str, Any] = screen.page.evaluate("window.__ctx.at(-1)")
        assert screen.errors == []
    finally:
        screen.close()
    assert second.startswith("Not loaded") and second.endswith("Nothing was changed."), second
    assert sent["context"] == kept


def test_fill_form_refuses_a_row_the_form_cannot_hold(browser: Any, tmp_path: Path) -> None:
    edits, _path, _value = PEERS_SECOND
    changed, _ = c2_variant(edits, tmp_path)
    with pytest.raises(live_check.Refusal, match=r"Not loaded.*valuation\.peers\[1\]"):
        real_fill_form(browser, changed, tmp_path)


def test_fill_form_refuses_an_empty_pathway_rather_than_timing_out(
    browser: Any, tmp_path: Path
) -> None:
    changed, raw = c2_variant({"run.pathway": ""}, tmp_path)
    assert server_refuses(raw)  # the key: the server refuses the file
    with pytest.raises(live_check.Refusal, match=r"Not loaded.*run\.pathway"):
        real_fill_form(browser, changed, tmp_path)
