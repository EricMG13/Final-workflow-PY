"""Back-test of the run-expectation rules on retained runs (offline, no model call, read-only).

    python tools/expectations_backtest.py [CASE ...] [--out FILE]

Each case's forecast is recomputed with `expectations()` from its context and source pages, then
compared with what the retained run did. The four launcher runs carry their own context; the four
campaign cases carry a context reconstructed under cases/expectations-backtest/ (a README line
there says so). Output is Markdown: a "deterministic retained-data report".
Handoff status -> actual class, and the verdict against a forecast, are the one documented table in
src/deploy_workflow/handoff_outcome.py (shared with live_check). A run with no completion record
is `not_reached` throughout, so it is not testable.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from deploy_vii.registry import plan
from deploy_workflow import handoff_outcome as outcome
from deploy_workflow.context import load_context
from deploy_workflow.model.handoff import _pages
from deploy_workflow.run_expectations import (
    RULES,
    edges_for,
    expectations,
    guess_kind,
)

logging.getLogger("pypdf").setLevel(logging.ERROR)  # font notices, not findings
RUNS = ROOT / "runs"
CHUNK, FIRST_PAGES = 12_000, 3
LAUNCHER = (
    "cpos-launch-live-001",
    "cpos-launch-live-002",
    "cpos-launch-cp2-reader-001",
    "web-04cd5a5d02ea7d1dea714a8a6632cd21",
)
FORD = "cpos-ford-ratings-2024-001"
# case -> run folder, modules in order, (file name the guess reads, text file), module -> handoff
CAMPAIGN = {
    "lmi-intercreditor": (
        "lmi-2014-001",
        ("CP-0", "CP-4"),
        {"d744045dex46.htm": "sources/source-lines.txt"},
        {"CP-0": "CP-0.md", "CP-4": "CP-4D-attempt-1.md"},
    ),
    "arcc-executed-indenture": (
        "arcc-2024-001",
        ("CP-0", "CP-1", "CP-4"),
        {
            "arcc-indenturexexhibit41.htm": "sources/base-lines.txt",
            "ARCC-FY2024-10K.pdf": "sources/annual-pages.txt",
        },
        {"CP-0": "CP-0.md", "CP-1": "CP-1.md", "CP-4": "CP-4.md"},
    ),
    "tdg-executed-notes": (
        "tdg-004",
        ("CP-0", "CP-4", "CP-3C"),
        {"d887611dex41.htm": "legal-source/source-lines.txt"},
        {"CP-0": "CP-0.md", "CP-4": "CP-4-attempt-2.md", "CP-3C": "CP-3C-legal-consumer.md"},
    ),
    "ford-ratings": (
        FORD,
        ("CP-0", "CP-1", "CP-2G", "CP-2H"),
        {"fitch-and-metrics.json": "../ford-otosan-2024-001/sources/fitch-and-metrics.json"},
        {},
    ),
}
Row = tuple[str, str, str, str, str]  # rule, module, forecast, actual, verdict


def source_pages(name: str, raw: bytes) -> list[str]:
    """What the launcher keeps for a file's guess: its first pages (text chunks of 12,000)."""
    if name.lower().endswith(".pdf") or b"=== PDF PAGE" in raw[:2000]:
        pages = [p for p in re.split(r"=== PDF PAGE \d+ ===", raw.decode(errors="replace")) if p]
    else:
        text = re.sub(r"^L\d+: ?", "", raw.decode(errors="replace"), flags=re.MULTILINE)
        pages = [text[i : i + CHUNK] for i in range(0, len(text), CHUNK)]
    return pages[:FIRST_PAGES]


def launcher_sources(run: Path, manifest: dict[str, dict[str, str]]) -> dict[str, list[str]]:
    """Each pinned source's first pages; a path that has gone is read from inputs/<hash>."""
    found: dict[str, list[str]] = {}
    for key, spec in manifest.items():
        if key == "context":
            continue
        path = (run / spec["path"]).resolve()
        raw = (path if path.is_file() else run / "inputs" / spec["sha256"]).read_bytes()
        name = key.removesuffix(".jsonl")
        if key.endswith(".jsonl"):
            rows = [json.loads(n)["text"] for n in raw.decode().splitlines() if n][:FIRST_PAGES]
            found[name] = rows
        else:
            found[name] = list(_pages(key, raw))[:FIRST_PAGES]
    return found


def completed(directory: Path) -> dict[str, str] | None:
    """module -> accepted handoff text from the run's completion record; None when it has none."""
    done = sorted(directory.glob("completed-*.json"))
    if not done:
        return None
    modules = json.loads(done[0].read_text())["modules"]
    return {m: (directory / rel).read_text() for m, rel in modules.items()}


def actual_of(module: str, texts: dict[str, str] | None) -> str:
    """The module's actual class from the accepted handoffs (None: no completion record)."""
    own = None if texts is None else texts.get(module)
    return outcome.actual_of(module, own, (texts or {}).get("CP-0", ""))[0]


verdict = outcome.verdict


def rule_of(item_id: str) -> str:
    key = item_id.split(":", 1)[1]
    return "inherited" if key.startswith("from:") else key


def load(case: str) -> tuple[str, str, tuple[str, ...], list[Row]]:
    """(issuer, as of, ordered modules, one row per forecast item and per module with none)."""
    if case in LAUNCHER:
        run = RUNS / case
        flow = json.loads((run / "workflow.json").read_text())
        ordered = plan(tuple(flow["run"]["requested_modules"]))
        spec = flow["sources"]["context"]
        ctx_path = (run / spec["path"]).resolve()
        raw = (ctx_path if ctx_path.is_file() else run / "inputs" / spec["sha256"]).read_bytes()
        pages, texts = launcher_sources(run, flow["sources"]), completed(run)
    else:
        folder, ordered, files, handoffs = CAMPAIGN[case]
        run = RUNS / folder
        raw = (ROOT / "cases/expectations-backtest" / case / "context.json").read_bytes()
        pages = {n: source_pages(n, (run / f).read_bytes()) for n, f in files.items()}
        texts = completed(run / "execution") if folder == FORD else None
        if texts is None:
            texts = {m: (run / f).read_text() for m, f in handoffs.items()}
    context = load_context(raw)
    guesses = [guess_kind(name, p) for name, p in pages.items()]
    items = expectations(ordered, guesses, context, edges_for(ordered))
    rows: list[Row] = [
        (rule_of(i["id"]), i["scope"], i["outcome"], "-", "not testable")
        for i in items
        if i["scope"] not in ordered
    ]
    for module in ordered:
        actual = actual_of(module, texts)
        own = [(rule_of(i["id"]), i["outcome"]) for i in items if i["scope"] == module] or [
            ("ready (no rule fired)", "ready")
        ]
        rows += [(rule, module, outcome, actual, verdict(outcome, actual)) for rule, outcome in own]
    return context.identity.issuer_name, context.run.as_of, tuple(ordered), rows


def report(cases: Sequence[str]) -> str:
    out = [
        "# Expectations back-test: deterministic retained-data report",
        "",
        (
            "No model call; runs/ read-only. Forecast recomputed offline with the current rules, "
            "compared with each retained run's handoffs (status table in "
            "tools/expectations_backtest.py). Campaign cases use a reconstructed context "
            "(cases/expectations-backtest/), not a context a user entered."
        ),
        "",
    ]
    tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for case in cases:
        issuer, as_of, ordered, rows = load(case)
        kind = "launcher run" if case in LAUNCHER else "reconstructed context"
        out += [
            f"## {case} ({kind}): {issuer}, as of {as_of}",
            f"Modules: {' '.join(ordered)}",
            "",
            "| Rule | Module | Forecast | Actual | Verdict |",
            "| --- | --- | --- | --- | --- |",
        ]
        for rule, module, forecast, actual, result in rows:
            out.append(f"| {rule} | {module} | {forecast} | {actual} | {result} |")
            tally[rule][result] += 1
        out.append("")
    out += [
        "## Per rule",
        "",
        "| Rule | Agreed | Disagreed | Not testable |",
        "| --- | --- | --- | --- |",
    ]
    for rule in sorted(tally):
        t = tally[rule]
        out.append(f"| {rule} | {t['agreed']} | {t['disagreed']} | {t['not testable']} |")
    never = sorted({r.key for r in RULES} - set(tally))
    out += ["", "Rules that fired in no case (not testable on this sample): " + ", ".join(never)]
    return "\n".join(out) + "\n"


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", nargs="*", default=[*LAUNCHER, *CAMPAIGN])
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    text = report(args.cases)
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
