"""Start a CP-OS run from a context file, an issuer folder and a selected model.

Without ``--live`` this only prepares: it pins the inputs, writes ``workflow.json`` with the module
instructions, prints the plan and calls no provider. ``--live`` passes that manifest to
``cpos.run_live_handoffs``, which keeps ordering, retention, resume, budget and delivery.

The generic check here covers handoff structure, issuer/date/source/upstream anchors and report
selectors. It has no independent expected values, so a passing run is not analytical review; every
report says so in its scope. ponytail: report only. The HTML Model and charts need issuer-specific
row selectors; add them when a run can derive those from CP-1's actual tables.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from deploy_vii.contracts import PATHWAY_MODULES, Run
from deploy_vii.live.prompts import STEP_CONTRACTS
from deploy_vii.registry import plan
from deploy_vii.report_view import _spec_of, pathways
from deploy_workflow.context import CONTEXT_SOURCE_ID, load_context
from deploy_workflow.handoff_delivery import (
    DeliveryRequest,
    HandoffInput,
    MarkdownLayout,
    MarkdownRoute,
    section,
)
from deploy_workflow.html_text import convert_html
from deploy_workflow.markdown_delivery import literal_module, markdown_files, require_issuer
from deploy_workflow.model.adapter import KEY_VARIABLES, LivePauseInForce, check_ruling
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.handoff import Check, _pages
from deploy_workflow.model.pricing import price_of, request_reservation_usd
from deploy_workflow.model_testing.configs import CONFIGS
from deploy_workflow.owners.cpos import HandoffPlan, HandoffTask, run_live_handoffs
from deploy_workflow.workflow import _put

ROOT = Path(__file__).resolve().parents[3]
HTML_SUFFIXES = frozenset({".htm", ".html"})
PAGE_CHARS = 3000  # cp-os's page for an HTML filing: eight pages per read is at most about 24 KB.
SOURCE_SUFFIXES = frozenset(
    {".pdf", ".htm", ".html", ".txt", ".md", ".xlsx", ".csv", ".json", ".jsonl"}
)
NOT_ANALYTICAL = frozenset({"CP-MODEL", "CP-8"})  # In the presets; each has its own route.
MAX_OUTPUT_TOKENS = 32000  # What the retained live campaigns ran with.

_SKILLS = "docs/reuse/selected-methods/skills/"
_VII = "src/deploy_vii/methods/"
# The method each module runs, per METHODOLOGY-REVIEW.md and what the 2026-11-05 live campaigns
# consumed. prompts/CP-0.md and CP-1-intake.md are TDG case instructions, so they are left out.
METHODS: dict[str, tuple[str, ...]] = {
    "CP-0": (_VII + "cp0.md",),
    "CP-1": ("prompts/CP-1.md",),  # Plus CP1_STEPS; no standalone CP-1 method file exists.
    "CP-1A": (_VII + "cp1a.md",),
    "CP-1B": ("src/deploy_workflow/prompts/texts/earnings_delta.md",),
    "CP-1C": (
        _SKILLS + "cp-1c-peer-benchmark/SKILL.md",
        _SKILLS + "cp-1c-peer-benchmark/references/REF_CP-1C_STEPS.md",
    ),
    "CP-1D": (_SKILLS + "cp-1d-earnings-quality/SKILL.md",),
    "CP-2": (_VII + "cp2.md",),
    "CP-2A": (
        _SKILLS + "cp-2a-downside-pathway/SKILL.md",
        _SKILLS + "cp-2a-downside-pathway/references/REF_CP-2B_STEPS.md",
        _VII + "cp2a.md",
    ),
    "CP-2D": (
        _SKILLS + "cp-2d-liquidity-cash-flow-bridge/SKILL.md",
        _SKILLS + "cp-2d-liquidity-cash-flow-bridge/references/REF_CP-2D_STEPS.md",
    ),
    "CP-2E": (
        _SKILLS + "cp-2e-macro-fx-hedging-sensitivity/SKILL.md",
        _SKILLS + "cp-2e-macro-fx-hedging-sensitivity/references/REF_CP-2E_STEPS.md",
        _SKILLS + "cp-2e-macro-fx-hedging-sensitivity/references/REF_CP-2F_STEPS.md",
    ),
    "CP-2G": (
        _SKILLS + "cp-2g-forward-credit-model/SKILL.md",
        _SKILLS + "cp-2g-forward-credit-model/references/REF_CP-2G_STEPS.md",
    ),
    "CP-2H": (
        _SKILLS + "cp-2h-ratings-migration-trigger/SKILL.md",
        _SKILLS + "cp-2h-ratings-migration-trigger/references/REF_CP-2H_STEPS.md",
    ),
    "CP-3": (
        _SKILLS + "cp-3-relative-value-security-selection/SKILL.md",
        _SKILLS + "cp-3-relative-value-security-selection/references/REF_CP-3_STEPS.md",
        _SKILLS + "cp-3-relative-value-security-selection/references/REF_CP-3A_STEPS.md",
    ),
    "CP-3C": (_VII + "cp3c.md",),
    "CP-3D": (
        _SKILLS + "cp-3d-market-implied-risk/SKILL.md",
        _SKILLS + "cp-3d-market-implied-risk/references/REF_CP-3D_STEPS.md",
    ),
    "CP-4": (
        _SKILLS + "cp-4-legal-covenant-interpreter/SKILL.md",
        _SKILLS + "cp-4-legal-covenant-interpreter/references/REF_CP-4_STEPS.md",
    ),
    "CP-4C": (
        _SKILLS + "cp-4c-restructuring-fulcrum/SKILL.md",
        _SKILLS + "cp-4c-restructuring-fulcrum/references/REF_CP-4C_STEPS.md",
    ),
    "CP-5": (
        _SKILLS + "cp-5-evidence-trace-validator/SKILL.md",
        _SKILLS + "cp-5-evidence-trace-validator/references/REF_CP-5_STEPS.md",
        _SKILLS + "cp-5-evidence-trace-validator/references/REF_CP-5A_STEPS.md",
    ),
    "CP-6": (
        _SKILLS + "cp-6-ic-debate-challenge/SKILL.md",
        _SKILLS + "cp-6-ic-debate-challenge/references/REF_CP-6_STEPS.md",
    ),
    "CP-DR": (
        _SKILLS + "cp-dr-deep-research/SKILL.md",
        _SKILLS + "cp-dr-deep-research/references/REF_CP-DR_STEPS.md",
        _VII + "cpdr.md",
    ),
}
CP1_STEPS = ("source_context", "financials", "narrative", "readiness", "quality")
# Report sections whose registered producer is the Model or nothing: the first module present in
# the run writes them. Everything else uses the section's registered producers. The order follows
# the routes the retained pathway reports actually published.
BLOCK_OWNERS: dict[str, tuple[str, ...]] = {
    "binding-limitations": ("CP-6",),
    "capital-structure": ("CP-4", "CP-3"),
    "compensation-preference": ("CP-3",),
    "covenant-levers": ("CP-4",),
    "credit-view": ("CP-2", "CP-3"),
    "distress-gate": ("CP-2A",),
    "ebitda-adjustments": ("CP-1D",),
    "funding-gap-lme": ("CP-3C", "CP-2G"),
    "historical-performance": ("CP-1D",),
    "instrument-decision": ("CP-3", "CP-6", "CP-4C"),
    "loan-hy-relative-value": ("CP-3",),
    "portfolio-fit": ("CP-3", "CP-6"),
    "portfolio-recommendation": ("CP-6",),
    "recommendation-portfolio-fit": ("CP-3",),
    "restructuring-paths": ("CP-4C",),
    "thesis-catalysts-challenge": ("CP-6",),
    "transaction-summary": ("CP-1A",),
    "watch-items": ("CP-1B",),
}
# CP-8 owns this section and compares two completed deliveries; a single run has nothing to compare.
SECOND_RUN_ONLY = "what-changed"
# The H3 that opens every module's `## Findings`: prose stating the module's view in plain English
# before any table (owner ruling, 2026-11-05; Deploy V's M365 runs for VMO2 and Wood Mackenzie open
# each module's analysis that way). "Credit view" (CP-1C, CP-2) and "Downside view" (CP-2A) are the
# M365 headings. A module added to METHODS needs an entry here; a test fails otherwise.
# This launcher route only: the owner route (`deploy_vii.cp2_synthesis`, Python-composed
# Markdown) is unchanged.
OPENING: dict[str, str] = {
    "CP-0": "Readiness view",
    "CP-1": "Financial base view",
    "CP-1A": "Business and transaction view",
    "CP-1B": "Earnings delta view",
    "CP-1C": "Credit view",
    "CP-1D": "Earnings quality view",
    "CP-2": "Credit view",
    "CP-2A": "Downside view",
    "CP-2D": "Liquidity view",
    "CP-2E": "Macro and FX view",
    "CP-2G": "Forward model view",
    "CP-2H": "Ratings view",
    "CP-3": "Relative value view",
    "CP-3C": "Funding gap view",
    "CP-3D": "Market-implied view",
    "CP-4": "Covenant view",
    "CP-4C": "Restructuring view",
    "CP-5": "Evidence trace view",
    "CP-6": "Challenge view",
    "CP-DR": "Research view",
}
# Only CP-2 gets READER_STANDARD (owner ruling, 2026-11-05): M365 output did not follow the
# CANON_SHARED rules, so they stay scoped to the one module that had them.
READER_STANDARD_MODULES = frozenset({"CP-2"})
# The user's Microsoft 365 Copilot custom instruction (supplied 2026-11-05, every clause kept):
# a persona that applies to every module (owner ruling, 2026-11-05). ponytail: instructions only.
READER_PERSONA = (
    "You are a senior credit research analyst at a leading credit fund, specialising in high "
    "yield credit and leveraged loans. Your research is used throughout the firm for key "
    "investment decisions; it is presented to senior credit committees and affects portfolio "
    "management. Your findings are institutional-grade, deeply analytical and data-dense, fully "
    "reasoned with explicit links from data to risk to credit implication. Say nothing generic "
    "unless it is tied to issuer-specific mechanics. Write in a detailed, structured style "
    "grounded in the provided data, and say when information is insufficient. State explicitly "
    "when information comes from external sources.\n\n"
)
# For READER_STANDARD_MODULES only: CANON_SHARED.md's reader-facing layer, and two habits of Deploy
# V's M365 handoffs (VMO2 2026-09-20, Wood Mackenzie 2026-08-27): units on amounts, the issuer as
# subject. The checker enforces the opening, not the prose.
READER_STANDARD = (
    "Presentation rules, from the reader-facing standard of Deploy V's CANON_SHARED.md. They "
    "never remove a method duty, category tag, limitation or gap:\n"
    "- In the opening section, state the credit view in plain English in the first sentence. In "
    "90–150 words, give the strongest support, the weakest point and what decides the outcome.\n"
    "- Keep `## Request` to the issuer, as-of date, pathway and scope, in at most three "
    "sentences. Readiness status, revision history and scope disclaimers belong in `## Gaps`.\n"
    "- State each limitation once, where it changes a conclusion, and say what it changes. Do not "
    "repeat a caveat in sentence after sentence.\n"
    "- In prose, give every amount its currency and unit, for example USD 1,250 million, 3.1x "
    "or 61 bp.\n"
    "- Make the issuer, its debt or its creditors the subject of a sentence, not a module. Cite "
    "modules and locators in brackets or tables.\n"
    "- Use plain-English labels. Hashes and raw locators belong in `## Sources` and tables.\n\n"
)


class LaunchRefused(ValueError):
    """The request cannot start; the message says what to change."""


@dataclass(frozen=True)
class Prepared:
    directory: Path
    manifest: Path
    plan: HandoffPlan
    layout: MarkdownLayout
    ordered: tuple[str, ...]
    ignored: tuple[str, ...]  # Files in the folder that no module can read.
    omitted: tuple[str, ...]  # Pathway report sections this run does not produce.
    hold: Decimal  # What one call of the largest module counts against the cap while in flight.


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _html_page_rows(name: str, raw: bytes) -> bytes:
    """An HTML filing's visible text as the page rows ``_pages`` reads, in cp-os's page size and
    headed by the filed document's identity. As raw bytes a filing is mostly markup, and only UTF-8
    decodes at all. Empty when the filing has no visible text."""
    text = convert_html(raw).text
    if not text.strip():
        return b""
    pages: list[str] = []
    page = f"Visible text of {name}, sha256 {_sha(raw)}.\n"
    for line in text.splitlines():
        # convert_html runs prose together on one line, so a line alone can exceed many pages.
        for piece in textwrap.wrap(line, PAGE_CHARS - 1, replace_whitespace=False):
            if len(page) + len(piece) + 1 > PAGE_CHARS:
                pages.append(page)
                page = ""
            page += piece + "\n"
    pages.append(page)
    rows = (json.dumps({"page": n, "text": body}) for n, body in enumerate(pages, 1))
    return "\n".join(rows).encode() + b"\n"


def _issuer_files(
    folder: Path, context: Path, directory: Path
) -> tuple[dict[str, HandoffInput], dict[str, bytes], tuple[str, ...]]:
    """Every readable file in ``folder``, the converted texts to write, and the files left out. A
    file a module could not read stops the launch here, because the same failure during a run
    would come after the module was marked as started and could not be resumed."""
    if not folder.is_dir():
        raise LaunchRefused(f"--sources {folder}: not a folder")
    pinned: dict[str, HandoffInput] = {}
    converted: dict[str, bytes] = {}
    ignored: list[str] = []
    for path in sorted(folder.rglob("*")):
        name = path.relative_to(folder).as_posix()
        parts = path.relative_to(folder).parts
        if any(part.startswith(".") for part in parts) or not path.is_file() or path == context:
            continue
        # "~$" marks Office's lock file beside a document someone has open.
        if path.suffix.lower() not in SOURCE_SUFFIXES or any(
            p.startswith(("_", "~$")) for p in parts
        ):
            ignored.append(name)
            continue
        raw = path.read_bytes()
        is_html = path.suffix.lower() in HTML_SUFFIXES
        key = f"{name}.jsonl" if is_html else name
        try:
            readable = _html_page_rows(name, raw) if is_html else raw
            pages = _pages(key, readable)
        except Exception as error:  # Any parser failure refuses, naming the file.
            raise LaunchRefused(f"--sources: cannot read {name}: {error}") from error
        if not any(page.strip() for page in pages):
            raise LaunchRefused(f"--sources: {name} has no extractable text (scanned image?)")
        if is_html:
            converted[f"source-text/{key}"] = readable
            pinned[key] = HandoffInput(path=f"source-text/{key}", sha256=_sha(readable))
        else:
            pinned[key] = HandoffInput(path=os.path.relpath(path, directory), sha256=_sha(raw))
    if not pinned:
        raise LaunchRefused(f"--sources {folder}: no readable issuer file")
    return pinned, converted, tuple(ignored)


def _layout(
    run: Run, ordered: tuple[str, ...], aliases: tuple[str, ...], config: str
) -> tuple[MarkdownLayout, tuple[str, ...]]:
    preset = next(p for p in pathways() if p.id == run.pathway)
    routes: list[MarkdownRoute] = []
    omitted: list[str] = []
    for block_id in preset.blocks:
        spec = _spec_of(block_id)
        owners = BLOCK_OWNERS.get(block_id, spec.producers)
        owner = next((m for m in owners if m in ordered), None)
        if owner is None or spec.kind == "chart" or block_id == SECOND_RUN_ONLY:
            omitted.append(block_id)
            continue
        routes.append(
            MarkdownRoute(
                module_id=owner,
                heading=spec.title,
                kind="prose" if spec.kind == "prose" else "table",
                block_id=block_id,
            )
        )
    if not routes:
        raise LaunchRefused(
            f"--modules {' '.join(ordered)}: fills no {preset.title} report section"
        )
    scope = (
        f"User-launched {preset.title} run for {run.issuer_name} as of {run.as_of}, using {config} "
        "on the selected issuer folder. Automated checks cover handoff structure, issuer and date "
        "anchors, source and upstream references and report selectors; analytical accuracy has "
        "not been independently reviewed. The HTML Model, charts and calculation JSON are not "
        f"published by this launcher. Sections not produced: {', '.join(omitted) or 'none'}."
    )
    layout = MarkdownLayout(
        blocks=tuple(r.block_id for r in routes),
        routes=tuple(routes),
        scope=scope,
        title=f"{run.issuer_name} — {preset.title}",
        issuer_aliases=aliases,
    )
    return layout, tuple(omitted)


def _instructions(run: Run, module: str, routes: Sequence[MarkdownRoute]) -> bytes:
    selectors = "\n".join(
        f"- `### {r.heading}`: "
        + ("exactly one populated Markdown table under it." if r.kind == "table" else "prose only.")
        for r in routes
        if r.module_id == module
    )
    sections = [(path, (ROOT / path).read_text(encoding="utf-8")) for path in METHODS[module]]
    if module == "CP-1":
        sections += [(f"STEP_CONTRACTS[{step}]", STEP_CONTRACTS[step]) for step in CP1_STEPS]
    method = "\n\n".join(
        f"=== {name} sha256 {_sha(text.encode())} ===\n{text}" for name, text in sections
    )
    opening = OPENING.get(module)
    return (
        f"# {module} for {run.issuer_name} ({run.issuer_id}), as of {run.as_of}\n\n"
        f"Pathway: {run.pathway}. Run the complete selected method below on this issuer's supplied "
        "sources and the current handoffs CP-OS supplies. Markdown transport overrides the "
        "method's JSON, typed-ID, connector and fact-chip mechanics; keep every analytical duty. "
        "Any issuer named in the method is an example, never evidence for this run.\n\n"
        f"Source `{CONTEXT_SOURCE_ID}` holds the user's dated settings and inputs for this run. It "
        "is not issuer evidence. Do not treat a value it leaves blank as zero.\n\n"
        "Find what this module needs with search_source, then read only those pages. Do not read "
        "whole filings: reads stop once this module's context is full.\n\n"
        "Use calculate for all new arithmetic. Keep exact amounts, units, currencies, periods, "
        "source locators and limitations. Absent evidence stays an explicit gap.\n\n"
        "A handoff is rejected unless it does all of this:\n"
        f"- name {run.issuer_name} in `## Request`, and state the as-of date {run.as_of} there;\n"
        "- list each issuer source it relied on in `## Sources`, with its exact name and sha256;\n"
        "- list each supplied handoff in `## Sources`, with its module and exact sha256"
        + (
            f";\n- open `## Findings` with `### {opening}`, once: prose that states the view, "
            "before any table.\n\n"
            if opening
            else ".\n\n"
        )
        + READER_PERSONA
        + (READER_STANDARD if module in READER_STANDARD_MODULES else "")
        + (
            "Report selectors, each exactly once inside `## Findings`, using these exact "
            f"headings. They place content in the report and are not analytical completion:\n"
            f"{selectors}\n\n"
            if selectors
            else ""
        )
        + f"Selected method, verbatim:\n\n{method}\n"
    ).encode()


def prepare(
    context: Path,
    sources: Path,
    out: Path | None,
    *,
    config: str,
    cap: Decimal | str,
    modules: Sequence[str] | None = None,
) -> Prepared:
    """Check everything and write the manifest and instructions; a refusal writes nothing."""
    context_path = Path(context).expanduser().resolve()
    folder = Path(sources).expanduser().resolve()
    raw_context = context_path.read_bytes()
    settings = load_context(raw_context)
    requested = (
        tuple(modules)
        if modules
        else tuple(m for m in PATHWAY_MODULES[settings.run.pathway] if m not in NOT_ANALYTICAL)
    )
    ordered = plan(requested)  # Refuses an unknown module, naming it.
    if unknown := [m for m in ordered if m not in METHODS]:
        raise LaunchRefused(f"--modules: no launchable method for {', '.join(unknown)}")
    run = Run(
        run_id=f"{settings.identity.issuer_id}-{settings.run.as_of}-{settings.run.pathway}-{config}",
        issuer_id=settings.identity.issuer_id,
        issuer_name=settings.identity.issuer_name,
        as_of=date.fromisoformat(settings.run.as_of),
        case_kind=settings.run.case_kind,
        pathway=settings.run.pathway,
        requested_modules=requested,
    )
    directory = (ROOT / "runs" / run.run_id if out is None else Path(out)).expanduser().resolve()
    if directory.is_relative_to(folder):
        raise LaunchRefused(f"--out {directory}: must be outside the issuer folder")
    pinned, converted, ignored = _issuer_files(folder, context_path, directory)
    aliases = tuple(a for a in settings.identity.aliases if a.strip())
    layout, omitted = _layout(run, ordered, aliases, config)
    texts = {m: _instructions(run, m, layout.routes) for m in ordered}
    request = HandoffPlan(
        run=run,
        sources={
            **pinned,
            CONTEXT_SOURCE_ID: HandoffInput(
                path=os.path.relpath(context_path, directory), sha256=_sha(raw_context)
            ),
        },
        instructions={
            m: HandoffInput(path=f"instructions/{m}.md", sha256=_sha(text))
            for m, text in texts.items()
        },
        layout=layout,
        execution="live-provider",
        max_attempts=1,
        provider_cap_usd=Decimal(cap),
    )
    # The loop's own bound for the first call of the largest module; later calls hold more.
    hold = request_reservation_usd(
        price_of(config), max(map(len, texts.values())) + 4096, MAX_OUTPUT_TOKENS
    )
    if request.provider_cap_usd < hold:
        raise LaunchRefused(f"--cap {cap}: one {config} call holds up to USD {hold:.2f}")
    raw = request.model_dump_json(indent=2).encode()
    manifest = directory / "workflow.json"
    if manifest.exists() and manifest.read_bytes() != raw:
        raise LaunchRefused(f"--out {directory}: holds a different request; choose a new --out")
    for relative, content in converted.items():
        _put(directory / relative, content)
    for module, text in texts.items():
        _put(directory / "instructions" / f"{module}.md", text)
    _put(manifest, raw)
    return Prepared(directory, manifest, request, layout, ordered, ignored, omitted, hold)


def checker(layout: MarkdownLayout) -> Check:
    """Anchors and report selectors for one module's answer, so a defect is repaired inside the
    module's loop rather than found at delivery after every module was paid for."""

    def check(task: HandoffTask, raw: bytes) -> tuple[str, ...]:
        text = raw.decode("utf-8")
        issues = []
        if task.run.as_of.isoformat() not in text:
            issues.append(f"State the as-of date {task.run.as_of} in ## Request.")
        for name, handoff in task.handoffs.items():
            if _sha(handoff) not in text:
                issues.append(f"List the current {name} handoff with its exact sha256.")
        evidence = {_sha(v) for k, v in task.sources.items() if k != CONTEXT_SOURCE_ID}
        if not any(digest in text for digest in evidence):
            issues.append("List each issuer source relied on with its exact name and sha256.")
        opening = OPENING.get(task.module_id)
        if opening and not _opens_with(text.splitlines(), opening):
            issues.append(
                f"Open ## Findings with ### {opening}, once: prose that states the view, "
                "before any table."
            )
        routes = tuple(r for r in layout.routes if r.module_id == task.module_id)
        try:
            if routes:
                own = layout.model_copy(
                    update={"blocks": tuple(r.block_id for r in routes), "routes": routes}
                )
                with tempfile.TemporaryDirectory() as temporary:
                    (Path(temporary) / "answer.md").write_bytes(raw)
                    answer = HandoffInput(path="answer.md", sha256=_sha(raw))
                    delivery = DeliveryRequest(
                        run=task.run, handoffs={task.module_id: answer}, layout=own
                    )
                    markdown_files(delivery, Path(temporary))
            else:
                require_issuer(task.run, layout.issuer_aliases, task.module_id, text.splitlines())
                literal_module(task.module_id, raw)
        except ValueError as error:
            issues.append(f"The report adapter refused this handoff: {error}")
        return tuple(issues)

    return check


def _opens_with(lines: list[str], heading: str) -> bool:
    """`## Findings` starts with the one `### heading`, whose first content is a paragraph: a
    line opening with a letter, a quote mark or bold, not a table, list, fence, comment or heading.
    """
    try:
        findings = [line for _, line in section(lines, "Findings") if line.strip()]
        body = [line.strip() for _, line in section(lines, heading) if line.strip()]
    except ValueError:  # Missing or repeated.
        return False
    first = body[0] if body else ""
    return findings[:1] == [f"### {heading}"] and (
        first[:1].isalpha() or first.startswith(("**", '"', "“"))
    )


def _cap(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"{text!r} is not an amount") from None
    if not value.is_finite() or value <= 0:
        raise argparse.ArgumentTypeError("the cap must be a positive amount in USD")
    return value


def _readiness(prepared: Prepared, config: str) -> str:
    selected = CONFIGS[config]
    run = prepared.plan.run
    names = (n for n in prepared.plan.sources if n != CONTEXT_SOURCE_ID)
    return "\n".join(
        (
            f"Run:      {run.run_id}",
            f"Model:    {config} = {selected.provider} {selected.model}, effort {selected.effort}",
            f"Cap:      USD {prepared.plan.provider_cap_usd} (hold per call: {prepared.hold:.2f})",
            f"Modules:  {', '.join(prepared.ordered)}",
            f"Sources:  {', '.join(names)}",
            f"Ignored:  {', '.join(prepared.ignored) or 'none'}",
            f"Report:   {', '.join(prepared.layout.blocks)}",
            f"Omitted:  {', '.join(prepared.omitted) or 'none'}",
            f"Manifest: {prepared.manifest}",
        )
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m deploy_workflow.owners.cpos_launch",
        description="Prepare a CP-OS run; add --live and --ruling to start the paid run.",
    )
    parser.add_argument("--context", type=Path, required=True, help="context/1 JSON file")
    parser.add_argument("--sources", type=Path, required=True, help="folder of issuer files")
    parser.add_argument("--config", choices=tuple(CONFIGS), required=True, help="model and effort")
    parser.add_argument("--cap", type=_cap, required=True, help="USD ceiling for this run folder")
    parser.add_argument("--modules", nargs="+", help="default: the context's pathway preset")
    parser.add_argument("--max-turns", type=int, default=32, help="model turns per module")
    parser.add_argument("--out", type=Path, help="run folder; default runs/<run id>")
    parser.add_argument("--live", action="store_true", help="make paid provider calls")
    parser.add_argument("--ruling", type=Path, help="docs/rulings/<file>.md naming this config")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.live and args.ruling is None:
            raise LaunchRefused(
                f"--live needs --ruling docs/rulings/<file>.md naming {args.config}"
            )
        if args.ruling is not None:
            check_ruling(args.config, args.ruling)
        key = KEY_VARIABLES[CONFIGS[args.config].provider]
        if args.live and not os.environ.get(key):
            raise LaunchRefused(f"--live needs {key} in the launching environment")
        prepared = prepare(
            args.context,
            args.sources,
            args.out,
            config=args.config,
            cap=args.cap,
            modules=args.modules,
        )
    except (ValueError, OSError, LivePauseInForce) as error:
        print(error, file=sys.stderr)
        return 2
    print(_readiness(prepared, args.config), flush=True)
    if not args.live:
        print("No provider was called. Add --live --ruling <file> to start the paid run.")
        return 0
    try:
        report = run_live_handoffs(
            prepared.manifest,
            prepared.directory,
            ruling=args.ruling,
            check=checker(prepared.layout),
            max_turns=args.max_turns,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            on_handoff=lambda task, _: print(f"Accepted: {task.module_id}", flush=True),
            config=args.config,
        )
    except (ValueError, RuntimeError) as error:
        print(f"Stopped: {error}\nRetained work is in {prepared.directory}", file=sys.stderr)
        return 1
    spent = Budget(prepared.plan.provider_cap_usd, prepared.directory / "live").spent
    print(f"Report:   {report}\nCharged:  USD {spent}")
    print("Automated checks only: review the handoffs against the sources before relying on this.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
