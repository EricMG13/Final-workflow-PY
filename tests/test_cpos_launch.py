"""User-launched CP-OS runs. A fake provider proves wiring only, not model or analytical quality."""

import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import pytest

from deploy_workflow.handoff_delivery import HEADINGS, verify_delivery
from deploy_workflow.model.adapter import AdapterReply, LiveAdapter
from deploy_workflow.model.handoff import _pages
from deploy_workflow.model.providers import build
from deploy_workflow.model.turn import ToolCall, Turn, Usage
from deploy_workflow.owners.cpos import HandoffTask, _checked_handoff
from deploy_workflow.owners.cpos_launch import METHODS, checker, main, prepare

ROOT = Path(__file__).resolve().parents[1]
RULING = ROOT / "docs/rulings/2026-11-05-live-loop-tests.md"  # configs: sol-medium
ISSUER = "Northbridge Synthetic Group"
AS_OF = "2025-03-31"

# Written by hand from the registry's dependency rules and the block titles on the Front Page.
COVENANT_MODULES = ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-4", "CP-2D", "CP-3C", "CP-5")
COVENANT_ROUTES = {
    ("covenant-tests-headroom", "CP-4", "Covenant tests and headroom", "table"),
    ("liquidity-runway", "CP-2D", "Liquidity and cash runway", "table"),
    ("funding-gap", "CP-2D", "Funding gap", "table"),
    ("red-flags", "CP-4", "Red flags", "table"),
    ("lender-protection-score", "CP-4", "Lender protection score", "table"),
    ("refinancing-paths", "CP-3C", "Refinancing paths", "table"),
    ("capacity", "CP-4", "Capacity and baskets", "table"),
    ("lme-creditor-exposure", "CP-3C", "LME capacity and creditor exposure", "table"),
    ("ebitda-definition", "CP-4", "EBITDA definition", "table"),
    ("documents-structure", "CP-4", "Documents and structure", "table"),
}
PATHWAY_MODULES = {
    "credit_snapshot": ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-4", "CP-3", "CP-5", "CP-6"),
    "earnings_update": ("CP-0", "CP-1", "CP-1B", "CP-1D", "CP-5"),
    "relative_value": (
        *("CP-0", "CP-1", "CP-1A", "CP-3D", "CP-1C", "CP-2", "CP-2D", "CP-3C", "CP-3", "CP-5"),
    ),
    "covenant_refinancing": COVENANT_MODULES,
    "distressed_restructuring": (
        *("CP-0", "CP-1", "CP-1A", "CP-1C", "CP-2A", "CP-4", "CP-2", "CP-2G", "CP-2H", "CP-4C"),
        "CP-5",
    ),
    "portfolio_decision": ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6"),
}


def context_file(tmp_path: Path, pathway: str = "covenant_refinancing") -> Path:
    data = json.loads((ROOT / "cases/cpdr-context-cutoff/context.json").read_text())
    data["run"].update(pathway=pathway, as_of=AS_OF, cutoff="")
    data["identity"].update(issuer_name=ISSUER, issuer_id="nbg")
    path = tmp_path / "context.json"
    path.write_text(json.dumps(data))
    return path


def issuer_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "issuer"
    (folder / "filings").mkdir(parents=True)
    (folder / "annual.txt").write_text("Net sales were 100.")
    (folder / "filings/notes.md").write_text("Notes mature in 2030.")
    (folder / ".DS_Store").write_bytes(b"\xff\xfe")
    (folder / "chart.png").write_bytes(b"\x89PNG")
    return folder


# Deploy V CANON_SHARED.md "Credit-research reading order": the H3 a reader meets first.
OPENING = {"CP-2": "Credit view"}


def answer(context: dict, plan_routes: list) -> str:
    lines = [f"# {context['module_id']}", "", "## Request", f"{ISSUER} as of {AS_OF}.", ""]
    lines += ["## Sources", ""]
    lines += [f"- {n} {h}" for n, h in context["sources"].items()]
    lines += [f"- {n} {h['sha256']}" for n, h in context["handoffs"].items()]
    lines += ["", "## Findings", ""]
    own = [r for r in plan_routes if r.module_id == context["module_id"]]
    opening = OPENING.get(context["module_id"])
    if opening:  # The opening view comes first, whether or not a report section selects it.
        lines += [f"### {opening}", "", "The issuer's credit view, stated first.", ""]
        own = [r for r in own if r.heading != opening]
    for route in own:
        lines += [f"### {route.heading}", ""]
        if route.kind == "table":
            lines += ["| Item | Value |", "| --- | --- |", "| Observed | 1 |", ""]
        else:
            lines += ["A located finding.", ""]
    for heading in ("Calculations", "Gaps", "Next module"):
        lines += [f"## {heading}", "", "None.", ""]
    return "\n".join(lines)


@pytest.fixture
def provider(monkeypatch):
    """Fake provider that answers each module and records every call it receives."""
    calls = []
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")

    def complete(self, request, **kwargs):
        context = json.loads(request.messages[1].text)
        calls.append((context["module_id"], self.config_id, request.effort))
        # The real provider body builder must accept what the handoff loop sends this model.
        provider.models.add(json.loads(build(self._model, request, "not-a-real-key").body)["model"])
        turn = Turn(
            "",
            (ToolCall(str(len(calls)), "write_handoff", {"markdown": provider.answer(context)}),),
            Usage(
                input_tokens=10,
                cached_read_tokens=0,
                cache_write_tokens=0,
                output_tokens=5,
                reasoning_tokens=0,
            ),
            "tool_use",
            provider.reported,
            "fake",
            200,
            # OpenRouter's charge is the billed amount; the others price from token counts.
            billed_usd=Decimal("0.01") if self.config_id == "deepseek-max" else None,
        )
        return AdapterReply(
            "ok", turn, None, 200, None, None, 1, 2, turn.usage, billed_usd=turn.billed_usd
        )

    monkeypatch.setattr(LiveAdapter, "complete", complete)
    provider.calls = calls
    provider.models = set()
    provider.reported = "fake"
    provider.answer = lambda context: pytest.fail("no answer set")
    return provider


def launch(tmp_path: Path, *extra: str, pathway: str = "covenant_refinancing") -> list[str]:
    return [
        *("--context", str(context_file(tmp_path, pathway))),
        *("--sources", str(issuer_folder(tmp_path))),
        *("--config", "sol-medium", "--cap", "50", "--out", str(tmp_path / "out")),
        *extra,
    ]


def test_folder_files_are_pinned_and_unusable_ones_reported(tmp_path):
    folder = issuer_folder(tmp_path)
    prepared = prepare(
        context_file(tmp_path), folder, tmp_path / "out", config="sol-medium", cap="50"
    )
    assert set(prepared.plan.sources) == {"annual.txt", "filings/notes.md", "context"}
    assert prepared.plan.sources["annual.txt"].sha256 == (
        hashlib.sha256(b"Net sales were 100.").hexdigest()
    )
    assert prepared.ignored == ("chart.png",)
    # Relative, like the retained manifests, so a run folder still resolves from another checkout.
    pin = prepared.plan.sources["annual.txt"]
    assert not Path(pin.path).is_absolute()
    assert (tmp_path / "out" / pin.path).resolve() == (folder / "annual.txt").resolve()
    assert not Path(prepared.plan.sources["context"].path).is_absolute()


def test_underscore_folders_are_reported_rather_than_silently_dropped(tmp_path):
    folder = issuer_folder(tmp_path)
    (folder / "_archive").mkdir()
    (folder / "_archive/old.txt").write_text("Old filing.")
    prepared = prepare(
        context_file(tmp_path), folder, tmp_path / "out", config="sol-medium", cap="50"
    )
    assert "_archive/old.txt" in prepared.ignored
    assert "_archive/old.txt" not in prepared.plan.sources


@pytest.mark.parametrize(
    ("name", "raw"),
    [
        ("filing.htm", "<html><head><title>Skip</title></head><body><p>Net sales were 100.</p>"),
        ("filings/8-K.HTML", "<html><body><p>Net sales were 100.</p><script>x()</script></body>"),
        ("legacy.html", b"<html><meta charset='windows-1252'><p>Net sales were 100. Caf\xe9</p>"),
    ],
)
def test_html_filings_reach_the_model_as_visible_text(tmp_path, name, raw):
    folder = issuer_folder(tmp_path)
    (folder / name).parent.mkdir(exist_ok=True)
    original = raw if isinstance(raw, bytes) else raw.encode()
    (folder / name).write_bytes(original)
    prepared = prepare(
        context_file(tmp_path), folder, tmp_path / "out", config="sol-medium", cap="50"
    )
    key = name + ".jsonl"
    pinned = (tmp_path / "out" / prepared.plan.sources[key].path).read_bytes()
    assert prepared.plan.sources[key].sha256 == hashlib.sha256(pinned).hexdigest()
    text = "\n".join(_pages(key, pinned))
    assert "Net sales were 100." in text
    assert "<p>" not in text and "x()" not in text and "Skip" not in text
    # The filed document stays identifiable from what the model reads.
    assert name in text and hashlib.sha256(original).hexdigest() in text


def test_html_filings_use_the_page_size_of_the_cp_os_loop(tmp_path):
    # cp-os PAGE_CHARS is 3,000. convert_html runs prose together (102,760 characters on one line of
    # the TDG 10-K), so long lines are split too, and no read of eight pages passes about 24 KB.
    folder = issuer_folder(tmp_path)
    paragraphs = "".join(f"<p>Line {n} of the filing.</p>" for n in range(5000))
    long_line = "y" * 5000
    (folder / "filing.htm").write_text(f"<html><body>{paragraphs}<p>{long_line}</p></body></html>")
    prepared = prepare(
        context_file(tmp_path), folder, tmp_path / "out", config="sol-medium", cap="50"
    )
    key = "filing.htm.jsonl"
    pages = _pages(key, (tmp_path / "out" / prepared.plan.sources[key].path).read_bytes())
    assert len(pages) > 30
    assert max(map(len, pages)) <= 3000
    text = "".join(pages)
    assert text.replace("\n", "").count("y") == 5000  # Nothing lost where a long line splits.
    assert [f"Line {n} of" in text for n in (0, 2500, 4999)] == [True, True, True]
    assert text.index("Line 0 of") < text.index("Line 2500 of") < text.index("Line 4999 of")


def test_context_file_inside_the_folder_is_not_counted_as_issuer_evidence(tmp_path):
    folder = issuer_folder(tmp_path)
    inside = folder / "context.json"
    inside.write_text(context_file(tmp_path).read_text())
    prepared = prepare(inside, folder, tmp_path / "out", config="sol-medium", cap="50")
    assert set(prepared.plan.sources) == {"annual.txt", "filings/notes.md", "context"}


def blank_pdf(path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    with path.open("wb") as stream:
        writer.write(stream)


@pytest.mark.parametrize(
    ("damage", "reason"),
    [
        (lambda f: (f / "bad.txt").write_bytes(b"\xff\xfe\x00"), "bad.txt"),
        (lambda f: (f / "fake.pdf").write_bytes(b"%PDF-broken"), "fake.pdf"),
        (lambda f: blank_pdf(f / "scan.pdf"), "scan.pdf"),
    ],
)
def test_unreadable_source_refused_before_anything_is_written(tmp_path, capsys, damage, reason):
    argv = launch(tmp_path)
    damage(tmp_path / "issuer")
    assert main(argv) == 2
    assert reason in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("folder", ["missing", "empty", "a-file"])
def test_folder_must_hold_usable_files(tmp_path, capsys, folder):
    (tmp_path / "empty").mkdir()
    (tmp_path / "a-file").write_text("x")
    code = main(
        [
            *("--context", str(context_file(tmp_path)), "--sources", str(tmp_path / folder)),
            *("--config", "sol-medium", "--cap", "50", "--out", str(tmp_path / "out")),
        ]
    )
    assert code == 2
    assert folder in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_context_sets_run_identity_modules_and_report_routes(tmp_path):
    prepared = prepare(
        context_file(tmp_path),
        issuer_folder(tmp_path),
        tmp_path / "out",
        config="sol-medium",
        cap="50",
    )
    run = prepared.plan.run
    assert (run.issuer_id, run.issuer_name, run.as_of.isoformat()) == ("nbg", ISSUER, AS_OF)
    assert run.pathway == "covenant_refinancing"
    assert "CP-MODEL" not in run.requested_modules
    assert prepared.ordered == COVENANT_MODULES
    assert prepared.plan.execution == "live-provider"
    assert {
        (r.block_id, r.module_id, r.heading, r.kind) for r in prepared.plan.layout.routes
    } == COVENANT_ROUTES
    assert "maturity-wall" in prepared.omitted


def test_selected_method_and_report_selectors_reach_the_instructions(tmp_path):
    prepared = prepare(
        context_file(tmp_path),
        issuer_folder(tmp_path),
        tmp_path / "out",
        config="sol-medium",
        cap="50",
    )
    text = (tmp_path / "out" / prepared.plan.instructions["CP-4"].path).read_text()
    method = ROOT / "docs/reuse/selected-methods/skills/cp-4-legal-covenant-interpreter/SKILL.md"
    assert method.read_text() in text
    assert hashlib.sha256(method.read_bytes()).hexdigest() in text
    assert "### Covenant tests and headroom" in text
    assert "search_source" in text  # runs/cpos-launch-live-001 read whole filings unprompted.
    assert ISSUER in text and AS_OF in text


def test_explicit_modules_narrow_the_run_and_keep_dependencies(tmp_path):
    prepared = prepare(
        context_file(tmp_path),
        issuer_folder(tmp_path),
        tmp_path / "out",
        config="sol-medium",
        cap="50",
        modules=("CP-4",),
    )
    assert prepared.ordered == ("CP-0", "CP-1", "CP-4")
    assert "liquidity-runway" in prepared.omitted


@pytest.mark.parametrize("module", ["CP-MODEL", "CP-8", "CP-MEMO", "CP-OS", "CP-L10", "NOPE"])
def test_modules_without_a_launchable_method_are_refused(tmp_path, capsys, module):
    assert main([*launch(tmp_path), "--modules", module]) == 2
    assert module in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("cap", ["0", "-1", "nan", "inf", "lots"])
def test_cap_must_be_a_positive_finite_amount(tmp_path, cap):
    argv = launch(tmp_path)
    argv[argv.index("--cap") + 1] = cap
    with pytest.raises(SystemExit) as stopped:
        main(argv)
    assert stopped.value.code == 2


def test_modules_that_fill_no_report_section_are_refused(tmp_path, capsys):
    # CP-1A has no section in the covenant report, and completion needs a populated deliverable.
    assert main([*launch(tmp_path), "--modules", "CP-1A"]) == 2
    assert "report section" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_cap_too_small_for_one_call_is_refused_offline(tmp_path, capsys):
    # gpt-6.1-sol holds USD 5.73 per call at 32,000 output tokens (seen from the live budget).
    argv = launch(tmp_path)
    argv[argv.index("--cap") + 1] = "5"
    assert main(argv) == 2
    assert "--cap" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_cap_is_sized_for_the_largest_module_not_the_smallest(tmp_path, capsys):
    # claude-opus-5-5 holds about USD 1.5 for CP-3's 105 KB instructions, USD 0.7 for CP-2's 6 KB.
    argv = launch(tmp_path, pathway="credit_snapshot")
    argv[argv.index("sol-medium")] = "opus-medium"
    argv[argv.index("--cap") + 1] = "1"
    assert main(argv) == 2
    assert "--cap" in capsys.readouterr().err


def test_invalid_context_is_refused_with_its_problem(tmp_path, capsys):
    argv = launch(tmp_path)
    (tmp_path / "context.json").write_text('{"schema": "wrong"}')
    assert main(argv) == 2
    assert "schema" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_without_live_nothing_is_sent_and_the_plan_is_shown(tmp_path, provider, capsys):
    assert main(launch(tmp_path)) == 0
    printed = capsys.readouterr().out
    assert provider.calls == []
    assert not (tmp_path / "out/live").exists()
    assert "gpt-6.1-sol" in printed and "medium" in printed
    assert "CP-4" in printed and "annual.txt" in printed and "chart.png" in printed
    assert "maturity-wall" in printed
    assert "5.73" in printed  # The per-call hold, seen from the live budget.


@pytest.mark.parametrize("missing", ["ruling", "key", "config-not-in-ruling"])
def test_live_gates_refuse_before_any_provider_call(
    tmp_path, provider, monkeypatch, capsys, missing
):
    argv = [*launch(tmp_path), "--live", "--ruling", str(RULING)]
    if missing == "ruling":
        argv = argv[:-2]
    elif missing == "key":
        monkeypatch.delenv("OPENAI_API_KEY")
    else:
        argv[argv.index("sol-medium")] = "sol-high"
    assert main(argv) == 2
    error = capsys.readouterr().err
    assert {"ruling": "--ruling", "key": "OPENAI_API_KEY", "config-not-in-ruling": "sol-high"}[
        missing
    ] in error
    assert "not-a-real-key" not in error
    assert provider.calls == []


@pytest.mark.parametrize(
    ("config", "key", "model", "effort"),
    [
        ("sol-medium", "OPENAI_API_KEY", "gpt-6.1-sol", "medium"),
        ("sol-high", "OPENAI_API_KEY", "gpt-6.1-sol", "high"),
        ("opus-medium", "ANTHROPIC_API_KEY", "claude-opus-5-5", "medium"),
        ("deepseek-max", "OPENROUTER_API_KEY", "deepseek/deepseek-v4.1-flash-1017", "max"),
    ],
)
def test_selected_model_and_effort_reach_every_provider_request(
    tmp_path, provider, monkeypatch, config, key, model, effort
):
    from deploy_workflow.model import adapter

    monkeypatch.setenv(key, "not-a-real-key")
    monkeypatch.setattr(adapter, "LIVE_RULINGS_ROOT", tmp_path)
    ruling = tmp_path / "all-configs.md"
    ruling.write_text(
        "lifts: live-provider-pause\nby: user\ndate: 2026-11-05\n"
        "configs: sol-medium sol-high opus-medium deepseek-max\n"
    )
    argv = [*launch(tmp_path), "--modules", "CP-4", "--live", "--ruling", str(ruling)]
    argv[argv.index("sol-medium")] = config
    routes = prepare_routes(tmp_path, config)
    provider.answer = lambda context: answer(context, routes)
    assert main(argv) == 0
    assert [c[0] for c in provider.calls] == ["CP-0", "CP-1", "CP-4"]
    assert {(c[1], c[2]) for c in provider.calls} == {(config, effort)}
    assert provider.models == {model}
    records = [
        json.loads(line)
        for log in (tmp_path / "out/live").rglob("*.jsonl")
        for line in log.read_text().splitlines()
    ]
    assert len(records) == 3
    assert {(r["requested_model"], r["requested_effort"]) for r in records} == {(model, effort)}
    assert {r["provider"] for r in records} == {key.split("_")[0].lower()}


def prepare_routes(tmp_path: Path, config: str) -> list:
    return list(
        prepare(
            tmp_path / "context.json",
            tmp_path / "issuer",
            tmp_path / "preview",
            config=config,
            cap="50",
            modules=("CP-4",),
        ).plan.layout.routes
    )


@pytest.mark.parametrize("pathway", sorted(PATHWAY_MODULES))
def test_every_pathway_runs_end_to_end_to_a_verified_report(tmp_path, provider, capsys, pathway):
    argv = launch(tmp_path, "--live", "--ruling", str(RULING), pathway=pathway)
    routes = list(
        prepare(
            tmp_path / "context.json",
            tmp_path / "issuer",
            tmp_path / "preview",
            config="sol-medium",
            cap="50",
        ).plan.layout.routes
    )
    provider.answer = lambda context: answer(context, routes)
    assert main(argv) == 0
    out = tmp_path / "out"
    assert tuple(c[0] for c in provider.calls) == PATHWAY_MODULES[pathway]
    report = next((out / "deliveries").glob("*/report.html"))
    assert verify_delivery(next(out.glob("delivery-*.json")), report.parent) == report
    assert str(report) in capsys.readouterr().out
    page = report.read_text()
    assert "not been independently reviewed" in page
    assert not (report.parent / "model.html").exists()
    completed = json.loads(next(out.glob("completed-*.json")).read_text())
    assert completed["execution"] == "live-provider"
    assert completed["cp_model_published"] is False


def test_rejected_module_stops_the_run_without_a_report(tmp_path, provider, capsys):
    argv = launch(tmp_path, "--modules", "CP-4", "--live", "--ruling", str(RULING))
    provider.answer = lambda context: "## Request\n\nNot a handoff."
    assert main(argv) == 1
    assert "CP-0" in capsys.readouterr().err
    assert not (tmp_path / "out/deliveries").exists()
    assert not list((tmp_path / "out").glob("completed-*.json"))


def test_issuer_name_from_the_context_cannot_inject_into_the_report(tmp_path, provider):
    argv = launch(tmp_path, "--modules", "CP-4", "--live", "--ruling", str(RULING))
    hostile = "A</script><script>alert(1)</script>"
    path = tmp_path / "context.json"
    data = json.loads(path.read_text())
    data["identity"]["issuer_name"] = hostile
    path.write_text(json.dumps(data))
    routes = prepare_routes(tmp_path, "sol-medium")
    provider.answer = lambda context: answer(context, routes).replace(ISSUER, hostile)
    assert main(argv) == 0
    report = next((tmp_path / "out/deliveries").glob("*/report.html")).read_text()
    assert "<script>alert(1)" not in report


def test_interrupted_module_is_never_resent_because_its_charge_is_unknown(
    tmp_path, provider, monkeypatch, capsys
):
    argv = launch(tmp_path, "--modules", "CP-4", "--live", "--ruling", str(RULING))
    sent = []

    def fails_after_sending(self, request, **kwargs):
        sent.append(request)
        raise ConnectionError("connection lost after the request left")

    monkeypatch.setattr(LiveAdapter, "complete", fails_after_sending)
    assert main(argv) == 1
    assert "cpos_live_stopped" in capsys.readouterr().err
    assert main(argv) == 1
    assert "cpos_interrupted" in capsys.readouterr().err
    assert len(sent) == 1


def test_second_launch_resumes_without_sending_anything(tmp_path, provider):
    argv = launch(tmp_path, "--modules", "CP-4", "--live", "--ruling", str(RULING))
    routes = prepare_routes(tmp_path, "sol-medium")
    provider.answer = lambda context: answer(context, routes)
    assert main(argv) == 0
    sent = list(provider.calls)
    assert main(argv) == 0
    assert provider.calls == sent


def test_changed_folder_cannot_reuse_a_run_directory(tmp_path, capsys):
    argv = launch(tmp_path)
    assert main(argv) == 0
    (tmp_path / "issuer/new-filing.txt").write_text("Later filing.")
    assert main(argv) == 2
    assert "--out" in capsys.readouterr().err
    manifest = json.loads((tmp_path / "out/workflow.json").read_text())
    assert "new-filing.txt" not in manifest["sources"]


def test_run_directory_inside_the_issuer_folder_is_refused(tmp_path, capsys):
    argv = launch(tmp_path)
    argv[argv.index("--out") + 1] = str(tmp_path / "issuer/run")
    assert main(argv) == 2
    assert "--out" in capsys.readouterr().err
    assert not (tmp_path / "issuer/run").exists()


def good_task(tmp_path: Path, module: str = "CP-2", pathway: str = "covenant_refinancing"):
    prepared = prepare(
        context_file(tmp_path, pathway),
        issuer_folder(tmp_path),
        tmp_path / "out",
        config="sol-medium",
        cap="50",
    )
    upstream = {"CP-1": b"# upstream"}
    task = HandoffTask(
        prepared.plan.run,
        module,
        b"",
        {"annual.txt": b"Net sales", "context": b"{}"},
        upstream,
        1,
        (),
    )
    context = {
        "module_id": module,
        "sources": {"annual.txt": hashlib.sha256(b"Net sales").hexdigest()},
        "handoffs": {"CP-1": {"sha256": hashlib.sha256(b"# upstream").hexdigest()}},
    }
    return prepared, task, context


def test_checker_accepts_a_complete_handoff(tmp_path):
    prepared, task, context = good_task(tmp_path, "CP-4")
    raw = answer(context, list(prepared.plan.layout.routes)).encode()
    assert _checked_handoff(task, raw, checker(prepared.layout)) == ()


@pytest.mark.parametrize(
    ("old", "new", "complaint"),
    [
        (ISSUER, "Someone Else", "selected issuer"),
        (AS_OF, "2024-01-01", AS_OF),
        (hashlib.sha256(b"# upstream").hexdigest(), "gone", "CP-1"),
        ("annual.txt " + hashlib.sha256(b"Net sales").hexdigest(), "nothing", "source"),
        ("### Red flags", "### Other", "Red flags"),
        (
            "### Red flags\n\n| Item | Value |\n| --- | --- |\n| Observed | 1 |",
            "### Red flags",
            "Red flags",
        ),
    ],
)
def test_checker_rejects_each_missing_anchor(tmp_path, old, new, complaint):
    prepared, task, context = good_task(tmp_path, "CP-4")
    raw = answer(context, list(prepared.plan.layout.routes))
    assert old in raw
    issues = _checked_handoff(task, raw.replace(old, new).encode(), checker(prepared.layout))
    assert any(complaint in issue for issue in issues), issues


def test_module_without_report_sections_still_needs_the_issuer(tmp_path):
    prepared, task, context = good_task(tmp_path, "CP-0")
    raw = answer(context, []).replace(ISSUER, "Someone Else").encode()
    assert any(
        "selected issuer" in i for i in _checked_handoff(task, raw, checker(prepared.layout))
    )


def test_cp2_instructions_carry_the_reader_standard_and_its_opening(tmp_path):
    prepared = prepare(
        context_file(tmp_path, "credit_snapshot"),
        issuer_folder(tmp_path),
        tmp_path / "out",
        config="sol-medium",
        cap="50",
    )

    def read(module: str) -> str:
        return (tmp_path / "out" / prepared.plan.instructions[module].path).read_text()

    cp2 = read("CP-2")
    assert "open `## Findings` with `### Credit view`" in cp2
    assert "CANON_SHARED.md" in cp2
    assert "State each limitation once" in cp2 and "currency and unit" in cp2
    # The user's Microsoft 365 Copilot custom instruction, which Deploy V's M365 runs carried.
    assert "senior credit research analyst" in cp2 and "senior credit committees" in cp2
    assert "external sources" in cp2
    assert "CANON_SHARED.md" not in read("CP-1A")  # One analytical module at a time.


@pytest.mark.parametrize("pathway", ["credit_snapshot", "relative_value"])
def test_checker_accepts_cp2_opening_with_its_view(tmp_path, pathway):
    prepared, task, context = good_task(tmp_path, "CP-2", pathway)
    raw = answer(context, list(prepared.plan.layout.routes))
    assert raw.count("### Credit view") == 1
    assert _checked_handoff(task, raw.encode(), checker(prepared.layout)) == ()


VIEW = "### Credit view\n\nThe issuer's credit view, stated first.\n\n"


@pytest.mark.parametrize("pathway", ["credit_snapshot", "relative_value"])
@pytest.mark.parametrize(
    ("old", "new"),
    [
        (VIEW, ""),
        ("## Findings\n\n", "## Findings\n\nPreamble before the view.\n\n"),
        (VIEW, "### Overview\n\nText.\n\n" + VIEW),
        ("The issuer's credit view, stated first.", "| A | B |\n| --- | --- |\n| x | y |"),
    ],
    ids=["missing", "prose-first", "other-section-first", "table-first"],
)
def test_checker_rejects_cp2_that_does_not_open_with_its_view(tmp_path, pathway, old, new):
    prepared, task, context = good_task(tmp_path, "CP-2", pathway)
    raw = answer(context, list(prepared.plan.layout.routes))
    assert old in raw
    issues = _checked_handoff(task, raw.replace(old, new).encode(), checker(prepared.layout))
    assert any("Open ## Findings with ### Credit view" in issue for issue in issues), issues


def test_every_selected_method_file_exists():
    assert all((ROOT / path).is_file() for files in METHODS.values() for path in files)


def test_six_handoff_headings_are_still_enforced(tmp_path):
    prepared, task, context = good_task(tmp_path, "CP-0")
    raw = answer(context, []).replace("## Gaps", "## Risks").encode()
    assert "## " + HEADINGS[4] in _checked_handoff(task, raw, checker(prepared.layout))[0]


# runs/cpos-launch-live-001 is the retained attempt that the context bound below repairs.
LIVE_CASE = ROOT / "runs/cpos-launch-live-002"
LIVE_MODULES = {"CP-0", "CP-1", "CP-1A"}


def assert_live_evidence(out: Path, cap: Decimal) -> None:
    """Actual provider calls, handoffs consumed downstream, and filed values in the report.

    Expected values were read from the visible text of the filed 10-K's statements, not from any
    run: NET SALES 7,940 and cash 6,261, USD millions, fiscal year ended September 30, 2024.
    """
    records = [json.loads(n) for n in (out / "live/calls.jsonl").read_text().splitlines()]
    assert {r["module_id"] for r in records} == LIVE_MODULES
    assert all(r["requested_model"] == "gpt-6.1-sol" for r in records)
    assert {r["reported_model"] for r in records} == {"gpt-6.1-sol"}
    assert all(r["request_id"] for r in records)
    charged = sum(Decimal(str(r["settled_usd"])) for r in records)
    assert 0 < charged <= cap
    completed = json.loads(next(out.glob("completed-*.json")).read_text())
    assert completed["execution"] == "live-provider"
    assert set(completed["module_execution"]) == LIVE_MODULES
    assert set(completed["module_execution"].values()) == {"live-provider"}
    report = next((out / "deliveries").glob("*/report.html"))
    assert verify_delivery(next(out.glob("delivery-*.json")), report.parent) == report
    handoffs = {m: (report.parent / f"{m}.md").read_bytes() for m in LIVE_MODULES}
    digest = {m: hashlib.sha256(raw).hexdigest().encode() for m, raw in handoffs.items()}
    assert digest["CP-0"] in handoffs["CP-1"]
    assert digest["CP-0"] in handoffs["CP-1A"] and digest["CP-1"] in handoffs["CP-1A"]
    for filed in (b"7,940", b"6,261"):
        assert filed in handoffs["CP-1"]
        assert filed in report.read_bytes()
    view = json.loads((report.parent / "report-view.json").read_text())
    assert {b["block_id"]: b["state"] for b in view["blocks"]} == {
        "company-operating-model": "populated",
        "financials-credit-metrics": "populated",
        "company-profile": "populated",
        "transaction-summary": "populated",
    }


@pytest.mark.live
def test_live_launch_from_a_context_file_and_issuer_folder():
    """Paid. Historical TDG FY2024 as of 2024-09-30; proves this launch path, not current credit.

    Answers stay in the run folder, so a rerun rechecks them and sends nothing. Needs the provider
    key in the environment and CPOS_LIVE_RULING naming a docs/rulings file that lists sol-medium.
    """
    ruling = os.environ.get("CPOS_LIVE_RULING")
    if not ruling or not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("paid: set CPOS_LIVE_RULING and OPENAI_API_KEY to run")
    # Retained answers for these modules cost USD 2.72, and each call holds 5.73. With the USD 0.29
    # the first attempt charged, this keeps the user's approved USD 12 total.
    cap = Decimal("11.71")
    code = main(
        [
            *("--context", str(LIVE_CASE / "context.json")),
            *("--sources", str(ROOT / "data/public-corpus/v1/TDG")),
            *("--config", "sol-medium", "--cap", str(cap), "--modules", "CP-1", "CP-1A"),
            *("--out", str(LIVE_CASE), "--live", "--ruling", ruling),
        ]
    )
    assert code == 0
    assert_live_evidence(LIVE_CASE, cap)


def test_live_evidence_check_can_pass_and_refuses_each_kind_of_fake(tmp_path, provider):
    """The paid test has not run, so prove here that its evidence check is satisfiable and bites."""
    context = json.loads((LIVE_CASE / "context.json").read_text())
    (tmp_path / "context.json").write_text(json.dumps(context))
    folder = issuer_folder(tmp_path)
    routes = list(
        prepare(
            tmp_path / "context.json",
            folder,
            tmp_path / "preview",
            config="sol-medium",
            cap="12",
            modules=("CP-1", "CP-1A"),
        ).plan.layout.routes
    )

    def launched(name: str, *, reported: str, filed: str) -> Path:
        provider.reported = reported
        provider.answer = lambda current: (
            answer(current, routes)
            .replace(ISSUER, context["identity"]["issuer_name"])
            .replace(AS_OF, context["run"]["as_of"])
            .replace("| Observed | 1 |", filed)
        )
        out = tmp_path / name
        argv = [
            *("--context", str(tmp_path / "context.json"), "--sources", str(folder)),
            *("--config", "sol-medium", "--cap", "12", "--modules", "CP-1", "CP-1A"),
            *("--out", str(out), "--live", "--ruling", str(RULING)),
        ]
        assert main(argv) == 0
        return out

    filed = "| NET SALES | 7,940 |\n| Cash | 6,261 |"
    assert_live_evidence(launched("good", reported="gpt-6.1-sol", filed=filed), Decimal(12))
    with pytest.raises(AssertionError, match="fake"):
        assert_live_evidence(launched("fake", reported="fake", filed=filed), Decimal(12))
    with pytest.raises(AssertionError, match="7,940"):
        assert_live_evidence(
            launched("wrong", reported="gpt-6.1-sol", filed="| Observed | 1 |"), Decimal(12)
        )
