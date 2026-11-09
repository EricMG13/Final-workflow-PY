"""guess_kind against the hand-labelled key (tests/fixtures/run-expectations/document-key.json).

The key was written before the guess existed and is not edited here. Each entry's file goes through
the page reader the launcher uses, and the guess sees pages[:3]."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pypdf.errors import DependencyError

from deploy_vii.contracts import Run
from deploy_workflow.context import RunContext, load_context
from deploy_workflow.model.handoff import _pages
from deploy_workflow.owners.cpos_launch import _html_page_rows, _layout
from deploy_workflow.run_expectations import (
    EVIDENCE,
    FORECAST,
    ITEM_KEYS,
    KINDS,
    OUTCOMES,
    Guess,
    edges_for,
    expectations,
    guess_kind,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = json.loads((ROOT / "tests/fixtures/run-expectations/document-key.json").read_text("utf-8"))
ENTRIES: list[dict[str, Any]] = KEY["entries"]
HTML = {".htm", ".html"}
# Two real PDFs are AES-encrypted and pypdf here lacks `cryptography`, so the launcher's reader
# cannot open them. Their pages[:3], read once by the same reader from a qpdf-decrypted copy, are
# committed (the fixture says how); the test uses them only when the PDF cannot be opened.
READER_GAP = "cryptography"
PAGES_FIXTURE = json.loads(
    (ROOT / "tests/fixtures/run-expectations-pages/encrypted-pdfs.json").read_text("utf-8")
)["files"]


def first_pages(entry: dict[str, Any]) -> list[str]:
    path = ROOT / entry["path"]
    if entry["origin"] == "synthetic":
        body = path.read_text("utf-8").split("\n", 1)[1]  # line 1 is the banner, not page text
        return re.split(r"^=== PAGE ===$", body, flags=re.MULTILINE)[:3] if body.strip() else [""]
    raw = path.read_bytes()
    if path.suffix.lower() in HTML:
        return _pages(f"{path.name}.jsonl", _html_page_rows(path.name, raw))[:3]
    try:
        return _pages(path.name, raw)[:3]
    except DependencyError as error:
        assert READER_GAP in str(error), f"{entry['path']}: {error}"
        fixture = PAGES_FIXTURE[path.name]
        assert fixture["path"] == entry["path"]
        return list(fixture["pages"])


def scored() -> tuple[list[tuple[dict[str, Any], Guess]], list[str]]:
    results = [(e, guess_kind(Path(e["path"]).name, first_pages(e))) for e in ENTRIES]
    scored_paths = {e["path"] for e, _ in results}
    return results, [e["path"] for e in ENTRIES if e["path"] not in scored_paths]


RESULTS, UNSCORED = scored()


def table() -> str:
    rows: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for entry, guess in RESULTS:
        row = rows[(entry["origin"], entry["kind"])]
        row[0] += 1
        if guess.kind == entry["kind"]:
            row[1] += 1
        elif guess.kind == "unrecognised":
            row[2] += 1
        else:
            row[3] += 1
    lines = ["origin     kind                    n  right  unrecognised  wrong"]
    lines += [
        f"{origin:<10} {kind:<22} {n:>2} {right:>6} {unrec:>13} {wrong:>6}"
        for (origin, kind), (n, right, unrec, wrong) in sorted(rows.items())
    ]
    lines.append(f"entries not scored: {UNSCORED}")
    return "\n".join(lines)


def test_key_is_the_one_the_brief_describes() -> None:
    assert KEY["schema"] == "document-key/1"
    assert len(ENTRIES) >= 20
    assert {e["kind"] for e in ENTRIES} <= set(KINDS)
    assert UNSCORED == []
    assert len(RESULTS) == len(ENTRIES)


def test_no_recognised_kind_contradicts_the_key() -> None:
    print("\n" + table())
    wrong = [
        (e["path"], e["kind"], g.kind)
        for e, g in RESULTS
        if g.kind not in {e["kind"], "unrecognised"}
    ]
    assert not wrong, f"{wrong}\n{table()}"


def test_real_files_are_mostly_recognised() -> None:
    real = [(e, g) for e, g in RESULTS if e["origin"] == "real"]
    assert len(real) == sum(e["origin"] == "real" for e in ENTRIES)  # the ceiling counts them all
    missed = [
        e["path"] for e, g in real if g.kind == "unrecognised" and e["kind"] != "unrecognised"
    ]
    assert len(missed) <= 0.10 * len(real), f"{missed}\n{table()}"


def test_synthetic_files_are_all_recognised() -> None:
    missed = [e["path"] for e, g in RESULTS if e["origin"] == "synthetic" and g.kind != e["kind"]]
    assert not missed, f"{missed}\n{table()}"


def test_focus_entries_match_exactly() -> None:
    focus = [(e, g) for e, g in RESULTS if "focus" in e]
    assert len(focus) == sum("focus" in e for e in ENTRIES)
    bad = [
        (e["path"], (e["kind"], e["executed"], e["period_end"]), (g.kind, g.executed, g.period_end))
        for e, g in focus
        if (g.kind, g.executed, g.period_end) != (e["kind"], e["executed"], e["period_end"])
    ]
    assert not bad, f"{bad}\n{table()}"


def test_executed_never_contradicts_the_key() -> None:
    bad = [
        (e["path"], e["executed"], g.executed)
        for e, g in RESULTS
        if g.executed is not None and g.executed != e["executed"]
    ]
    assert not bad, bad


def test_period_end_is_the_key_or_none() -> None:
    bad = [
        (e["path"], e["period_end"], g.period_end)
        for e, g in RESULTS
        if g.period_end is not None and g.period_end != e["period_end"]
    ]
    assert not bad, bad


def test_signal_explains_a_recognised_kind() -> None:
    for entry, guess in RESULTS:
        assert bool(guess.signal) == (guess.kind != "unrecognised"), entry["path"]


def test_html_header_line_is_not_cover_text() -> None:
    header = "Visible text of FORM 10-K CREDIT AGREEMENT.htm, sha256 ab.\nSkip to content\n"
    assert guess_kind("page.htm", [header]).kind == "unrecognised"
    assert guess_kind("page.htm", [header + "CREDIT AGREEMENT\n"]).kind == "credit_agreement"


def test_preliminary_statements_is_never_a_draft_signal() -> None:
    page = "CREDIT AGREEMENT\ndated as of March 1, 2025\nPRELIMINARY STATEMENTS\nWHEREAS"
    assert guess_kind("a.txt", [page]).executed is None
    assert guess_kind("a.txt", ["EXECUTION VERSION\n" + page]).executed is True
    assert guess_kind("a.txt", ["DRAFT\n" + page]).executed is False


def test_a_page_naming_two_kinds_is_ambiguous() -> None:
    assert guess_kind("a.txt", ["CREDIT AGREEMENT\nINDENTURE\n"]).kind == "unrecognised"


def test_cover_outranks_later_pages_and_name() -> None:
    pages = ["COMPLIANCE CERTIFICATE\n", "INDENTURE\n"]
    assert guess_kind("Credit-Agreement.txt", pages).kind == "compliance_certificate"


def test_name_decides_only_when_the_pages_are_silent() -> None:
    assert guess_kind("notes.txt", ["no cover phrase here"]).kind == "unrecognised"
    named = guess_kind("Term-Sheet-draft.txt", ["no cover phrase here"])
    assert (named.kind, named.executed) == ("term_sheet", None)  # term sheets carry no mark
    guess = guess_kind("Indenture-executed.pdf", [""])
    assert (guess.kind, guess.executed) == ("indenture", True)
    assert guess_kind("Indenture-executed.pdf", ["COMPLIANCE CERTIFICATE"]).executed is None


def test_period_end_needs_one_unambiguous_date() -> None:
    two = "FORM 10-K\nFor the fiscal year ended June 30, 2025\nand the year ended June 30, 2024"
    assert guess_kind("a.txt", [two]).period_end is None
    assert (
        guess_kind(
            "a.txt", [two.split("\n")[0] + "\nFor the fiscal year ended February 30, 2025"]
        ).period_end
        is None
    )
    one = guess_kind("a.txt", ["FORM 10-K\nFor the fiscal year ended June 30, 2025"])
    assert one.period_end == "2025-06-30"


def test_no_pages_is_unrecognised() -> None:
    assert guess_kind("x.txt", []) == Guess("unrecognised", "", None, None)


def test_a_wrapped_body_line_is_not_a_title() -> None:
    wrapped = (
        "as illustrated in the Supplement n. 2 dated October 12, 2020 to the Base\n"
        "Prospectus of the Euro 35,000,000,000 Euro Medium Term Note Programme dated\n"
        "January 9, 2020, as already supplemented\n"
    )
    assert guess_kind("a.pdf", [wrapped]).kind == "unrecognised"
    assert guess_kind("a.pdf", [wrapped + "\nPROSPECTUS\n"]).kind == "prospectus"


# --- Task 3: rules and expected outcomes, against the hand-written outcome key -----------------
# tests/fixtures/run-expectations/outcome-key.json was written by someone else and is not edited.
# Each scenario's summary context is rebuilt as a real context file (the Task 1 reader), its
# documents become Guess objects, and expectations() is compared per scope.

OUTCOME_KEY = json.loads(
    (ROOT / "tests/fixtures/run-expectations/outcome-key.json").read_text("utf-8")
)
SCENARIOS: list[dict[str, Any]] = OUTCOME_KEY["scenarios"]
CONTEXTS = ROOT / "cases/context"
DISPLAY = {
    "Will refuse": "will_refuse",
    "Gap": "gap",
    "Limited": "limited",
    "Check": "check",
    "Information": "information",
    "Ready": "ready",
}


def build_context(summary: dict[str, Any], run_type: str, pathway: str) -> RunContext:
    """A valid context file whose declarations are the scenario's summary."""
    base = json.loads((CONTEXTS / "research-minimal.json").read_text("utf-8"))
    full = json.loads((CONTEXTS / "primary-full.json").read_text("utf-8"))
    base["run"].update(
        run_type=run_type, pathway=pathway, reporting_currency=summary["reporting_currency"]
    )
    base["run"].update(current_period="q3-2026", prior_period="q2-2026")  # Earnings runs need them.
    if summary["issue_classification"]:
        base["identity"]["issue_classification"] = summary["issue_classification"]
    base["attachments"].update(
        legal_documents=summary["legal_documents"],
        management_bridge=summary["management_bridge"],
        portfolio_workbook=summary["portfolio_workbook"],
        prior_case=summary["prior_case"],
    )
    base["valuation"]["peer_source"] = summary["peer_source"]
    if summary["peer_source"] == "user_list":
        base["valuation"]["peers"] = [
            {**p, "ev_m": "", "ebitda_m": "", "as_of": "", "source": ""}
            for p in full["valuation"]["peers"]
        ]
    facility = dict(full["deal_terms"][0])
    if summary["deal_terms"]:
        if not summary["talk"]:
            for name in ("talk_spread_bps_low", "talk_spread_bps_high"):
                facility[name] = ""
            for name in ("talk_oid_low", "talk_oid_high"):
                facility[name] = ""
        base["deal_terms"] = [facility]
    base["quotes"] = [{**full["quotes"][0], "kind": q["kind"]} for q in summary["quotes"]]
    if summary["quotes"] and not base["deal_terms"]:
        base["deal_terms"] = [{**facility, **dict.fromkeys(TALK_FIELDS, "")}]
    base["ratings"] = full["ratings"][: summary["ratings"]]
    return load_context(json.dumps(base).encode())


TALK_FIELDS = ("talk_spread_bps_low", "talk_spread_bps_high", "talk_oid_low", "talk_oid_high")


def guesses_of(scenario: dict[str, Any]) -> list[Guess]:
    return [
        Guess(
            d["kind"],
            f"found {d['kind']!r} on page 1" if d["kind"] != "unrecognised" else "",
            d["executed"],
            None,
        )
        for d in scenario["documents"]
    ]


def omitted_of(scenario: dict[str, Any]) -> list[str]:
    """The sections the launcher's own _layout omits for this pathway and modules."""
    run = Run(
        run_id="expectations-test",
        issuer_id="issuer",
        issuer_name="Issuer",
        as_of=date(2026, 10, 31),
        case_kind="public",
        pathway=scenario["pathway"],
        requested_modules=tuple(scenario["modules"]),
    )
    return list(_layout(run, tuple(scenario["modules"]), (), "test")[1])


def test_key_run_rows_agree_with_the_launcher_layout() -> None:
    """The key's section-omitted rows are a real check on _layout, not the test's input."""
    for scenario in SCENARIOS:
        keyed = [
            r["section"] for r in scenario["expected"]["run"] if r["rule"] == "section-omitted"
        ]
        assert sorted(keyed) == sorted(omitted_of(scenario)), scenario["id"]


def test_a_guessed_kind_with_underscores_reads_as_words() -> None:
    scenario = next(s for s in SCENARIOS if s["id"] == "rule-cp4-final-offering-memorandum")
    reason = next(i["reason"] for i in run_scenario(scenario) if i["id"].endswith("final-om"))
    assert "Likely: offering memorandum (found 'offering_memorandum' on page 1)" in reason


def run_scenario(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    ordered = tuple(scenario["modules"])
    context = build_context(scenario["context"], scenario["run_type"], scenario["pathway"])
    return expectations(
        ordered, guesses_of(scenario), context, edges_for(ordered), omitted=omitted_of(scenario)
    )


def key_rows(scenario: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    expected = scenario["expected"]
    return {"run": expected["run"], **expected["modules"]}


def pairs(rows: list[dict[str, Any]]) -> list[tuple[str, bool]]:
    return sorted((DISPLAY.get(r["outcome"], r["outcome"]), r["counted"]) for r in rows)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_outcomes_equal_the_key(scenario: dict[str, Any]) -> None:
    items = run_scenario(scenario)
    wanted = key_rows(scenario)
    by_scope: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_scope[item["scope"]].append(item)
    for scope in wanted.keys() | by_scope.keys():
        # A requested module the key does not list is Ready: no row, or a ready row, never counted.
        got = [i for i in by_scope.get(scope, []) if i["outcome"] != "ready" or i["counted"]]
        assert pairs(got) == pairs(wanted.get(scope, [])), (scope, got)
        for row in wanted.get(scope, []):
            if "detail" in row:
                reasons = " ".join(i["reason"] for i in got).lower()
                assert row["detail"].lower() in reasons, (scope, row["detail"], reasons)
            if row.get("inherited"):
                inherited = [i for i in got if i["inherited_from"]]
                assert [set(i["inherited_from"]) for i in inherited] == [set(row["inherited_from"])]
    assert sum(i["counted"] for i in items) == scenario["expected"]["counted_total"]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_item_shape_ids_and_order_are_stable(scenario: dict[str, Any]) -> None:
    items = run_scenario(scenario)
    assert items == run_scenario(scenario)
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids))
    order = ["run", *scenario["modules"]]
    assert [order.index(i["scope"]) for i in items] == sorted(
        order.index(i["scope"]) for i in items
    )
    for item in items:
        assert set(item) == ITEM_KEYS
        assert item["outcome"] in OUTCOMES
        assert item["evidence"] in EVIDENCE
        assert item["id"].startswith(f"{item['scope']}:")
        assert bool(item["inherited_from"]) == (":from:" in item["id"])
        if item["inherited_from"] or item["outcome"] in {"information", "ready"}:
            assert item["counted"] is False
        else:
            assert item["counted"] is True
            assert item["basis"] and item["reason"] and item["fix"]
        if item["inherited_from"]:
            assert item["id"] == f"{item['scope']}:from:{item['inherited_from'][0]}"


def test_a_row_that_inherits_nothing_carries_an_empty_list() -> None:
    scenario = next(s for s in SCENARIOS if s["id"] == "rf4-amendment-alone")
    items = run_scenario(scenario)
    assert any(i["inherited_from"] == [] for i in items)
    assert all(isinstance(i["inherited_from"], list) for i in items)


def test_chart_strip_row_has_its_exact_id_and_never_propagates() -> None:
    scenario = next(s for s in SCENARIOS if s["id"] == "rf5-non-usd-issuer")
    items = {i["id"]: i for i in run_scenario(scenario)}
    strip = items["CP-1:chart-strip-usd"]
    assert (strip["scope"], strip["outcome"], strip["counted"]) == ("CP-1", "limited", True)
    assert not [i for i in items.values() if "CP-1" in (i["inherited_from"] or [])]


def test_will_refuse_wording_is_provisional_until_a_live() -> None:
    scenario = next(s for s in SCENARIOS if s["id"] == "a-live-legal-none-will-refuse")
    (row,) = [i for i in run_scenario(scenario) if i["outcome"] == "will_refuse"]
    assert "entered by user" in row["reason"]
    assert FORECAST not in row["reason"]  # the shared sentence is a constant, not repeated


def test_a_guessed_kind_reads_as_a_forecast_not_a_fact() -> None:
    scenario = next(s for s in SCENARIOS if s["id"] == "rf4-amendment-alone")
    reason = next(i["reason"] for i in run_scenario(scenario) if i["id"].endswith("only-amendment"))
    assert "Likely: amendment (found 'amendment' on page 1)" in reason


def test_an_unlisted_pathway_run_context_is_read_as_entered() -> None:
    """A blank classification adds no information row; nothing compares two entries."""
    scenario = json.loads(
        json.dumps(next(s for s in SCENARIOS if s["id"] == "rf6-investment-grade"))
    )
    scenario["context"]["issue_classification"] = ""
    assert not [i for i in run_scenario(scenario) if i["id"] == "run:investment-grade"]


def test_check_and_gap_never_propagate_but_will_refuse_does() -> None:
    """Hand-built edges: a gap on one module leaves its consumers Ready; a block edge keeps a
    Will refuse as Will refuse."""
    scenario = next(s for s in SCENARIOS if s["id"] == "a-live-legal-none-will-refuse")
    ordered = ("CP-0", "CP-4", "CP-2D")
    context = build_context(scenario["context"], "secondary", "covenant_refinancing")
    edges = {"CP-2D": {"CP-4": "block"}}
    items = expectations(ordered, guesses_of(scenario), context, edges)
    inherited = [i for i in items if i["inherited_from"]]
    assert [(i["scope"], i["outcome"], i["inherited_from"]) for i in inherited] == [
        ("CP-2D", "will_refuse", ["CP-4"])
    ]
    gap = next(s for s in SCENARIOS if s["id"] == "rule-cp2h-no-ratings")
    items = run_scenario(gap)
    assert not [i for i in items if i["inherited_from"]]
