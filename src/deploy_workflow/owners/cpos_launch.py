"""Start a CP-OS run from a context file, an issuer folder and a selected model.

Without ``--live`` this only prepares: it pins the inputs, writes ``workflow.json`` with the module
instructions, prints the plan and calls no provider. ``--live`` passes that manifest to
``cpos.run_live_handoffs``, which keeps ordering, retention, resume, budget and delivery.

The generic check here covers handoff structure, issuer/date/source/upstream anchors and report
selectors. It has no independent expected values, so a passing run is not analytical review; every
report says so in its scope. CP-1 fills the chart strip from fixed tables. ponytail: the HTML Model
needs issuer-specific row selectors; add it when a run can derive those from CP-1's actual tables.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import textwrap
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Any

from deploy_vii.contracts import PATHWAY_MODULES, Run
from deploy_vii.cp4_legal import DRAFT_LIMITATION
from deploy_vii.live.prompts import STEP_CONTRACTS
from deploy_vii.registry import modules, plan
from deploy_vii.report_view import _spec_of, pathways
from deploy_workflow.context import CONTEXT_SOURCE_ID, load_context
from deploy_workflow.handoff_delivery import (
    DeliveryRequest,
    HandoffInput,
    MarkdownLayout,
    MarkdownRoute,
    section,
    table_row,
)
from deploy_workflow.handoff_outcome import unfenced
from deploy_workflow.html_text import convert_html
from deploy_workflow.markdown_delivery import (
    STRIP_FIGURES,
    literal_module,
    markdown_files,
    require_issuer,
)
from deploy_workflow.model.adapter import (
    COPILOT_RUNTIME_VARIABLE,
    KEY_VARIABLES,
    LivePauseInForce,
    check_ruling,
)
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.handoff import Check, _pages
from deploy_workflow.model.pricing import price_of, request_reservation_usd
from deploy_workflow.model_testing.configs import CONFIGS
from deploy_workflow.owners.cpos import (
    HandoffPlan,
    HandoffTask,
    RetainedHandoff,
    _checked_handoff,
    run_live_handoffs,
    with_notes,
)
from deploy_workflow.reader_summary import (
    BOTTOM_LINE_WORDS,
    CONFIDENCE,
    FINDING_WORDS,
    LIMITATION_WORDS,
    MAX_FINDINGS,
    reader_issues,
)
from deploy_workflow.run_expectations import Item, edges_for, expectations, guess_kind
from deploy_workflow.workflow import _put

ROOT = Path(__file__).resolve().parents[3]
HTML_SUFFIXES = frozenset({".htm", ".html"})
PAGE_CHARS = 3000  # cp-os's page for an HTML filing: eight pages per read is at most about 24 KB.
SOURCE_SUFFIXES = frozenset(
    {".pdf", ".htm", ".html", ".txt", ".md", ".xlsx", ".csv", ".json", ".jsonl"}
)
NOT_ANALYTICAL = frozenset({"CP-MODEL", "CP-8"})  # In the presets; each has its own route.
FIRST_PAGES = 3  # Pages of each source kept for the offline document guess (page 1 is the cover).
Cover = tuple[str, tuple[str, ...]]  # A source's file name and its first pages.
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
# The H3 that follows the two tables of `### Reader summary` (R-C2-6) and precedes any other
# table: its first content is prose stating the module's view in plain English
# (owner ruling, 2026-11-05; Deploy V's M365 runs for VMO2 and Wood Mackenzie open each module's
# analysis that way). "Credit view" (CP-1C, CP-2) and "Downside view" (CP-2A) are the
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


# Provisional review (Plan 3 Task 10; owner decision 1, 2026-11-08): on a Primary run, or when the
# context declares draft legal documents, CP-4 reviews draft and marketing documents as Provisional
# instead of stopping. The Deploy VII owner path admits drafts the same way (`DRAFT_LIMITATION`).
FINAL_OM_REASON = (
    "After closing, the final offering memorandum is a summary of the executed documents, "
    "not the governing document."
)
BLOCKED_LINE = "Module Status: Blocked"
REGISTER_HEADING = "Legal document register"
REGISTER_HEADER = ["Document", "Kind", "Status", "Authority rank", "Source"]
OTHER_KIND = "other"
MARKETING_KIND = "lender presentation, term sheet or commitment letter"
KIND_RANK = {
    "credit agreement or indenture": "1",
    "intercreditor agreement": "2",
    "compliance certificate": "3",
    "offering memorandum": "4",
    "covenant-review report": "5",
    MARKETING_KIND: "6",
    OTHER_KIND: "not ranked",
}
STATUSES = ("executed", "draft", "indicative", "final", "filed")
PROVISIONAL = "Provisional"
FINAL_OM_DRAFT_WORDING = "may change before signing"
CONSUMERS = ("CP-3", "CP-5", "CP-6")
CONSUMER_SENTENCE = "Label any term taken from a Provisional CP-4 handoff as Provisional."
PROVISIONAL_PARAGRAPH = (
    "Provisional review. This run may hold draft or marketing documents instead of executed ones. "
    "Review them rather than stopping, and mark the result Provisional:\n"
    f"- Under `## Findings`, write `### {REGISTER_HEADING}` with exactly one table headed "
    f"`| {' | '.join(REGISTER_HEADER)} |`, one row per document you read. Kind is one of "
    + "; ".join(f"`{kind}` (rank {rank})" for kind, rank in KIND_RANK.items())
    + ". `other` is not a legal or offering document, for example an annual or quarterly report, "
    "an acquisition agreement, a press release or a current report. Status is one of "
    + ", ".join(f"`{status}`" for status in STATUSES)
    + ": `executed` is signed; `draft` is an unsigned ranked document; `indicative` is a lender "
    "presentation, term sheet or commitment letter; `final` is a final offering memorandum after "
    "closing; `filed` is a regulatory filing that is not itself an agreement. Source is the source "
    "name you relied on.\n"
    "- Never call a draft or a marketing document executed, and never use CP-1D figures as "
    "covenant capacity.\n"
    "- If any ranked document is a draft or indicative, or none is executed and the others are not "
    f"all final, state this sentence word for word: {DRAFT_LIMITATION}\n"
    f"- If any document is a final offering memorandum, state this sentence word for word: "
    f"{FINAL_OM_REASON} Then do not use the draft sentence for it.\n"
    f"- When either sentence applies, write the word {PROVISIONAL} in every report section routed "
    f"to this module and in the Main limitation of the Reader summary, and give {PROVISIONAL} "
    "confidence.\n"
    f"- With no legal document at all, or a register that lists no legal or offering document, "
    f"state `{BLOCKED_LINE}` and the method's Blocked message.\n\n"
)
PROVISIONAL_ISSUES = {
    "register_missing": "Provisional register missing",
    "blocked_line_missing": "Provisional register lists no legal or offering document",
    "register_malformed": "Provisional register row malformed",
    "executed_marketing_document": "Provisional register calls a marketing document executed",
    "draft_limitation_missing": "Provisional draft limitation missing",
    "final_om_reason_missing": "Provisional final offering memorandum reason missing",
    "final_om_draft_wording": "Provisional final offering memorandum carries draft wording",
    "provisional_section_missing": "Provisional label missing in routed section",
    "provisional_main_limitation_missing": "Provisional label missing in Main limitation",
    "consumer_provisional_missing": "Provisional label missing from a Provisional CP-4 term",
}
# R-C2-7: a hand rescale of an amount (x1000 in the model's head) was the cause of most untraced
# numbers in the C2 run. The sentence is in CP-1's instruction in every run type and, through the
# cell rule, in each Primary pro forma instruction.
UNIT_SENTENCE = (
    "Keep the source's reporting unit and state it; do not rescale an amount by hand (no "
    "multiplying or dividing by 1000 in your head); when a different unit is needed, do the "
    "conversion with `calculate` and state the conversion."
)
# R-C2-3: the app exposes none of the scripts a method names (`prepare_invocation.py`,
# `validate_handoff.py` and the like). Without this sentence a module recorded the missing scripts
# as a reason to mark itself Restricted (C2, CP-1D). Composed for every module whose method text
# names a script file.
SCRIPT_NAME = re.compile(r"[\w./-]+\.(?:py|sh)\b")
SCRIPTS_SENTENCE = (
    "The helper scripts this method names (for example `prepare_invocation.py`, "
    "`confidence_score.py`, `completeness_check.py` and `validate_handoff.py`) are not available "
    "in this app and none is run. Record that once, as a limitation; set `qa_status` from the "
    "method's own criteria; the scripts' absence alone does not make the module Restricted."
)
PRO_FORMA_CELL_RULE = (
    "Every amount cell, `Total debt / EBITDA` included, is either a plain number such as `1234.5` "
    "or `-10` (digits, optional thousands commas and decimals, a negative with a leading minus; "
    "a comma is followed by exactly three digits and the first group has one to three digits, as "
    "in `1,234`; the minus is the ASCII hyphen `-`, never the Unicode minus `\u2212`; no brackets, "
    "currency symbol, unit suffix, multiple sign or words) or `Not supplied: <reason>` with a "
    "reason that holds at least one letter or digit. Write a plain number such as `1,234`, `-18` "
    "or `0.5`, with no plus sign and no bare leading point. A `Reporting unit` or `Currency` cell "
    "is never blank. "
    "Take every figure from the sources and handoffs or from `calculate`; plug nothing and "
    f"invent no haircut. {UNIT_SENTENCE}"
)
LADDER_ROWS = (
    "(a) Starting EBITDA",
    "(b) Documented acquisition and disposal adjustments",
    "Base EBITDA, (a) + (b)",
    "(c) Unrealised run-rate savings, not in base",
    "(d) Management add-backs: Supported, not in base",
    "(d) Management add-backs: Challenged, not in base",
    "(d) Management add-backs: Rejected, not in base",
    "(d) Management add-backs: Insufficient Information, not in base",
    "As marketed",
    "(e) Difference from As marketed",
)
LEVERAGE_ROWS = ("Reported", "Pro forma, excluding unrealised add-backs", "As marketed")
SOURCES_USES_HEADING = "Sources and uses"
SOURCES_USES_HEADER = ("Side", "Item", "Amount", "Currency", "Basis", "Source")
ADD_BACK_HEADING = "Add-back LTM register"
ADD_BACK_HEADER = (
    "Add-back",
    "Run-rate claimed",
    "Realised to date",
    "Amount already in LTM",
    "Verdict",
    "Source",
)
VERDICTS = ("Supported", "Challenged", "Rejected", "Insufficient Information")
CAPITALISATION_HEADING = "Pro forma capitalisation"
CAPITALISATION_HEADER = (
    "Instrument",
    "Currency",
    "Balance sheet",
    "Transaction adjustment",
    "Pro forma",
    "Basis",
    "Source",
)
LADDER_HEADING = "EBITDA ladder"
LADDER_HEADER = ("Row", "Amount", "Reporting unit", "Definition or basis", "Source")
LEVERAGE_HEADING = "Pro forma leverage"
LEVERAGE_HEADER = (
    "Basis",
    "Total debt",
    "EBITDA",
    "Total debt / EBITDA",
    "Reporting unit",
    "Source",
)
EBITDA_DEFINITIONS = ("EBIT plus D&A", "Adjusted EBITDA", "As Defined")
BASES = ("documented", "user-entered")


FINDINGS_ONLY = (
    "A table outside `## Findings` is not read, and the answer has one `## Findings` section. "
    "Fenced code under `## Findings` is not read."
)


def _header(header: Sequence[str]) -> str:
    return f"`| {' | '.join(header)} |`"


PRO_FORMA_CP1A = (
    "Pro forma sources and uses (Primary run). Under `## Findings`, write "
    f"`### {SOURCES_USES_HEADING}` once, with one table headed {_header(SOURCES_USES_HEADER)}. "
    "Side is `Source`, `Use` or `Memo`. Basis is `documented` or `user-entered`. A `Source` row "
    "holds a funded amount taken from the source (what is drawn or issued at closing), never a "
    "facility commitment. The user-entered facility size is a commitment: write it on a `Memo` "
    "row whose Item ends with `(commitment)` and whose Basis is `documented` or `user-entered`; "
    "a `Memo` row is not a source or use of funds and is in no total. When the source states no "
    "funded amount for a row, write `Not supplied: <reason>` in Amount. Where documents differ, "
    "log the difference in prose and never resolve it. Source names what the "
    "row came from. Write at least one `Source` row and one `Use` row (a `Memo` row is neither). "
    "For each of Source and Use: when every row of that side holds a number, write exactly one "
    "total row (Item `Total sources` with Side `Source`, Item `Total uses` with Side `Use`); "
    "when any row of that side is `Not supplied`, write no total row for that side. Take each "
    "total from `calculate`; where the source prints a total the rows do not reach, plug "
    "nothing: write the printed total, say so in Source, and log the difference in prose. "
    "Write labels exactly as shown: `Total sources`, not "
    f"`Total Sources`. {FINDINGS_ONLY} {PRO_FORMA_CELL_RULE}\n\n"
)
PRO_FORMA_CP1D = (
    "Pro forma add-back register (Primary run). Under `## Findings`, write "
    f"`### {ADD_BACK_HEADING}` once, with one table headed {_header(ADD_BACK_HEADER)} and at least "
    "one row, one per management add-back. Verdict is one of "
    + ", ".join(f"`{v}`" for v in VERDICTS)
    + ". Source names what the row came from. Write labels exactly as shown: Verdict is "
    f"`Rejected`, not `rejected`. {FINDINGS_ONLY} {PRO_FORMA_CELL_RULE}\n\n"
)
PRO_FORMA_CP2 = (
    "Pro forma capitalisation and leverage (Primary run). Under `## Findings`, write these three "
    "tables, each under its own heading, once. Unrealised and unresolved add-backs are shown and "
    f"never counted in the base. {FINDINGS_ONLY}\n"
    f"- `### {CAPITALISATION_HEADING}`: above the table, one line `Balance-sheet date: "
    "YYYY-MM-DD` and one line `LTM period: <text>`, each once. The table is headed "
    f"{_header(CAPITALISATION_HEADER)}. Currency is a 3-letter code. Basis is `documented` or "
    "`user-entered`. One row has Instrument `Cash`; every other row that is not a total is a debt "
    "instrument, and the table has at least one debt row (a Cash row alone is not enough). For "
    "each currency a debt row uses, one row `Total debt (<CCY>)`, and its Currency must equal the "
    "code in the label; write no total for a currency that no debt row uses. The Cash row and "
    "every total row cite `CP-1A` in Source (cash to balance sheet, fees and OID, and the debt, "
    "per its sources and uses). Write labels exactly as shown, with the currency code in upper "
    "case: `Total debt (USD)`, not `Total debt (usd)` or `Total Debt (USD)`. Write a "
    "`Total debt (all currencies)` row only after a line `FX rate: <rate> (<source>)` under the "
    "heading, above the table. `<rate>` is a plain number, optionally preceded by a currency "
    "pair `AAA/BBB`, as in `FX rate: EUR/USD 1.25 (ECB reference rate, 2014-06-30)`; a line "
    "after the table does not count, and neither does a line above the heading.\n"
    f"- `### {LADDER_HEADING}`: headed {_header(LADDER_HEADER)}, with exactly these rows in this "
    "order: "
    + "; ".join(f"`{row}`" for row in LADDER_ROWS)
    + ". Definition or basis and Source are never blank. Row (a)'s Definition or basis names one "
    "of "
    + ", ".join(f"`{d}`" for d in EBITDA_DEFINITIONS)
    + ". The Base EBITDA and any (e) figure come from the `calculate` tool and their Source says "
    "`calculate`. Row (e) is either that number or `Not supplied: Insufficient Information` "
    "when the management figure is not reconciled; give no other reason. When CP-1D did not run, "
    "rows (c) and (d) carry `Not supplied: <reason>`.\n"
    f"- `### {LEVERAGE_HEADING}`: headed {_header(LEVERAGE_HEADER)}, with exactly these rows in "
    "this order: "
    + ", ".join(f"`{row}`" for row in LEVERAGE_ROWS)
    + ". The `Pro forma, excluding unrealised add-backs` Source cites `CP-1A`. A private deal "
    "with no filings writes `Not supplied: no filed financial statements` in the Reported row.\n"
    f"{PRO_FORMA_CELL_RULE} Nothing is plugged and no haircut is invented; write negatives with a "
    "leading minus.\n\n"
)
PRO_FORMA = {"CP-1A": PRO_FORMA_CP1A, "CP-1D": PRO_FORMA_CP1D, "CP-2": PRO_FORMA_CP2}
PRO_FORMA_ISSUES = {
    "pro_forma_table_missing": "Pro forma table missing",
    "pro_forma_rows": "Pro forma rows wrong",
    "pro_forma_cell": "Pro forma cell invalid",
    "pro_forma_basis": "Pro forma basis or date missing",
    "pro_forma_cp1a_citation": "Pro forma does not cite CP-1A",
    "pro_forma_fx": "Pro forma cross-currency total lacks an FX rate",
}


class LaunchRefused(ValueError):
    """The request cannot start; the message says what to change."""


@dataclass(frozen=True)
class Accepted:
    """A stopped run's accepted answer as CP-OS recorded it: the response bytes, the recorded
    request it answered (run, instructions, source and upstream hashes) and the model selection
    (provider, model, effort) the stopped run was reviewed with; None when unknown."""

    response: bytes
    request: Mapping[str, Any]
    model: tuple[str, str, str] | None
    problem: str = ""  # Why this module's record cannot be replayed, when it cannot.


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
    retained_modules: tuple[str, ...] = ()  # Replayed from a stopped run; no model call.
    retained_stop: tuple[str, str] = ("", "")  # The module the replay stopped before, and why.
    documents: tuple[dict[str, Any], ...] = ()  # Each pinned source's guessed kind (offline).
    expectations: tuple[Item, ...] = ()  # What the run is expected to do (offline forecast).


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
) -> tuple[dict[str, HandoffInput], dict[str, bytes], tuple[str, ...], dict[str, Cover]]:
    """Every readable file in ``folder``, the converted texts to write, the files left out and each
    pinned source's name and first pages (for the offline document guess). A
    file a module could not read stops the launch here, because the same failure during a run
    would come after the module was marked as started and could not be resumed."""
    if not folder.is_dir():
        raise LaunchRefused(f"--sources {folder}: not a folder")
    pinned: dict[str, HandoffInput] = {}
    converted: dict[str, bytes] = {}
    ignored: list[str] = []
    origins: dict[str, str] = {}
    covers: dict[str, Cover] = {}
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
        if key in origins:  # An HTML filing's text is pinned as `<name>.jsonl`, a real file name.
            raise LaunchRefused(
                f"--sources: {origins[key]} and {name} would both be source {key}; "
                "rename or remove one"
            )
        origins[key] = name
        try:
            readable = _html_page_rows(name, raw) if is_html else raw
            pages = _pages(key, readable)
        except Exception as error:  # Any parser failure refuses, naming the file.
            raise LaunchRefused(f"--sources: cannot read {name}: {error}") from error
        if not any(page.strip() for page in pages):
            raise LaunchRefused(f"--sources: {name} has no extractable text (scanned image?)")
        covers[key] = (name, tuple(pages[:FIRST_PAGES]))
        if is_html:
            converted[f"source-text/{key}"] = readable
            pinned[key] = HandoffInput(path=f"source-text/{key}", sha256=_sha(readable))
        else:
            pinned[key] = HandoffInput(path=os.path.relpath(path, directory), sha256=_sha(raw))
    if not pinned:
        raise LaunchRefused(f"--sources {folder}: no readable issuer file")
    return pinned, converted, tuple(ignored), covers


# Fixed so any run's charts can be read without issuer-specific row selectors.
CHART_TABLES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "S.1": ("Chart data: leverage", ("Total debt / EBITDA", "Net debt / EBITDA"), "x"),
    "S.2": ("Chart data: interest cover", ("EBITDA / cash interest",), "x"),
    "S.3": ("Chart data: liquidity", ("Cash", "Undrawn committed facilities"), "US$m"),
    "S.4": ("Chart data: debt maturities", ("Debt maturing",), "US$m"),
}
CHART_BLOCKS = frozenset(STRIP_FIGURES) - {"yield-against-maturity"}
NOT_SUPPLIED = "Not supplied:"
PLAIN_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _chart_route(block_id: str, figure: str) -> MarkdownRoute:
    heading, columns, unit = CHART_TABLES[figure]
    return MarkdownRoute(
        module_id="CP-1",
        heading=heading,
        kind="chart",
        block_id=block_id,
        figure_id=figure,
        value_columns=columns,
        orientation="period-rows",
        chart_unit=unit,
    )


def _chart_header(route: MarkdownRoute) -> list[str]:
    return ["Period", *route.value_columns, "Reporting unit", "Basis and limitation"]


def chart_issues(text: str, route: MarkdownRoute) -> tuple[str, ...]:
    """A chart table's cells reach the report as they are, so each must already be chart-ready."""
    heading = f"### {route.heading}"
    lines = text.splitlines()
    if heading not in lines:
        return (f"Add `{heading}` inside ## Findings, with its table.",)
    rows = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    header = _chart_header(route)
    if not rows or rows[0] != header:
        return (f"`{heading}` needs the table headed `| {' | '.join(header)} |`.",)
    issues = []
    for row in rows[2:]:
        if len(row) != len(header):
            issues.append(f"`{heading}` row needs {len(header)} cells: {' | '.join(row)}")
            continue
        period, *values, unit, basis = row
        if not basis:
            issues.append(f"`{heading}` {period}: Basis and limitation is blank.")
        for value in values:
            if value.startswith(NOT_SUPPLIED) and value.removeprefix(NOT_SUPPLIED).strip():
                continue
            if not PLAIN_NUMBER.fullmatch(value):
                issues.append(
                    f"`{heading}` {period}: `{value} |` must be a plain number "
                    "or `Not supplied: <reason>`."
                )
            elif unit != route.chart_unit:
                issues.append(
                    f"`{heading}` {period}: a number in {unit} cannot be charted as "
                    f"{route.chart_unit}; write `Not supplied: reported in {unit}`."
                )
    return tuple(issues)


# The lines the report states above the call, front-most first: the Reader summary's first table
# (instructed by READER_SECTION_RULES) of each module that is in the run, and CP-6's instructed
# `Final Action Bias:` paragraph. Nothing is read that no instruction asks the module to write.
FRONT_TITLES = {
    "CP-6": "Committee decision",
    "CP-5": "Evidence validation",
    "CP-2": "Fundamental credit",
    "CP-0": "Source readiness",
}
READER_SUMMARY_HEADER = "Bottom line | Confidence | Main limitation"


def _front_routes(ordered: tuple[str, ...]) -> tuple[MarkdownRoute, ...]:
    routes = [
        MarkdownRoute(
            module_id=module_id,
            heading="Reader summary",
            kind="table",
            block_id="front",
            table_header=READER_SUMMARY_HEADER,
            label=title,
        )
        for module_id, title in FRONT_TITLES.items()
        if module_id in ordered
    ]
    if "CP-6" in ordered:
        routes.append(
            MarkdownRoute(
                module_id="CP-6",
                heading="Action Bias Determination",
                kind="prose",
                block_id="front",
                prefix="Final Action Bias:",
                label="Committee action bias",
            )
        )
    return tuple(routes)


PRO_FORMA_BLOCK = "pro-forma"


def _pro_forma_routes(ordered: tuple[str, ...]) -> list[MarkdownRoute]:
    """CP-2's capitalisation table (primary) then leverage table (a tab), then, when CP-1A also
    runs, its Sources and uses table (a further tab, R-C2-2); whole tables unchanged.

    delivery matches `table_header` against the table's first header cell (its `row_header`).
    """
    tables = [
        ("CP-2", CAPITALISATION_HEADING, CAPITALISATION_HEADER),
        ("CP-2", LEVERAGE_HEADING, LEVERAGE_HEADER),
    ]
    if "CP-1A" in ordered:
        tables.append(("CP-1A", SOURCES_USES_HEADING, SOURCES_USES_HEADER))
    return [
        MarkdownRoute(
            module_id=module,
            heading=heading,
            kind="table",
            block_id=PRO_FORMA_BLOCK,
            table_header=header[0],
        )
        for module, heading, header in tables
    ]


def _layout(  # noqa: PLR0913 - signature fixed by the plan: keywords run_type, legal_documents
    run: Run,
    ordered: tuple[str, ...],
    aliases: tuple[str, ...],
    config: str,
    *,
    run_type: str,
    legal_documents: str,
) -> tuple[MarkdownLayout, tuple[str, ...]]:
    # legal_documents is accepted for the Shared names signature: the register stays out of the
    # report, so it changes nothing here.
    del legal_documents
    preset = next(p for p in pathways() if p.id == run.pathway)
    routes: list[MarkdownRoute] = []
    omitted: list[str] = []
    for block_id in preset.blocks:
        if block_id == PRO_FORMA_BLOCK:  # Only a Primary run's CP-2 fills it; else not a section.
            if run_type == "primary" and "CP-2" in ordered:
                routes += _pro_forma_routes(ordered)
            continue
        spec = _spec_of(block_id)
        owners = BLOCK_OWNERS.get(block_id, spec.producers)
        owner = next((m for m in owners if m in ordered), None)
        if owner == "CP-1" and block_id in CHART_BLOCKS:
            routes += [_chart_route(block_id, figure) for figure in STRIP_FIGURES[block_id]]
            continue
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
        "not been independently reviewed. The HTML Model and calculation JSON are not published "
        f"by this launcher. Sections not produced: {', '.join(omitted) or 'none'}."
    )
    layout = MarkdownLayout(
        blocks=tuple(dict.fromkeys(r.block_id for r in routes)),
        routes=tuple(routes),
        scope=scope,
        title=f"{run.issuer_name} — {preset.title}",
        issuer_aliases=aliases,
        front=_front_routes(ordered),
    )
    return layout, tuple(omitted)


READER_SECTION_RULES = (
    "Write `### Reader summary` after the analysis is finished and place it first under "
    "`## Findings`. It restates conclusions already in this handoff in plain language for a "
    "credit analyst: add no new fact, figure or conclusion. Use no module codes, table IDs or "
    "hashes. Every number must match the handoff exactly. Use these two tables, one row in the "
    f"first (bottom line at most {BOTTOM_LINE_WORDS} words, main limitation at most "
    f"{LIMITATION_WORDS}) and 1 to {MAX_FINDINGS} rows in the second (each finding and creditor "
    f"impact at most {FINDING_WORDS} words). Confidence is one of {', '.join(CONFIDENCE)}.\n\n"
    "| Bottom line | Confidence | Main limitation |\n| --- | --- | --- |\n\n"
    "| Finding | Creditor impact | Confidence |\n| --- | --- | --- |\n\n"
)


def _selector(route: MarkdownRoute) -> str:
    if route.kind == "chart":
        return (
            f"- `### {route.heading}`: exactly one Markdown table headed "
            f"`| {' | '.join(_chart_header(route))} |`, one row per period. Value cells are plain "
            f"numbers in {route.chart_unit}, with that as the Reporting unit, or "
            "`Not supplied: <reason>`. An issuer reporting in another currency or scale writes "
            "`Not supplied: reported in <unit>` in monetary cells. Basis and limitation is never "
            "blank."
        )
    what = (
        "exactly one populated Markdown table under it." if route.kind == "table" else "prose only."
    )
    return f"- `### {route.heading}`: {what}"


def _instructions(
    run: Run,
    module: str,
    routes: Sequence[MarkdownRoute],
    *,
    run_type: str,
    legal_documents: str,
) -> bytes:
    provisional = run_type == "primary" or legal_documents == "draft"
    paragraph = PROVISIONAL_PARAGRAPH if provisional and module == "CP-4" else ""
    consumer = f"{CONSUMER_SENTENCE}\n\n" if provisional and module in CONSUMERS else ""
    pro_forma = PRO_FORMA.get(module, "") if run_type == "primary" else ""
    selectors = "\n".join(_selector(r) for r in routes if r.module_id == module)
    sections = [(path, (ROOT / path).read_text(encoding="utf-8")) for path in METHODS[module]]
    if module == "CP-1":
        sections += [(f"STEP_CONTRACTS[{step}]", STEP_CONTRACTS[step]) for step in CP1_STEPS]
    method = "\n\n".join(
        f"=== {name} sha256 {_sha(text.encode())} ===\n{text}" for name, text in sections
    )
    opening = OPENING.get(module)
    units = f"{UNIT_SENTENCE}\n\n" if module == "CP-1" else ""  # R-C2-7, in every run type
    scripts = (  # R-C2-3: the method names a script this app does not expose
        f"{SCRIPTS_SENTENCE}\n\n" if any(SCRIPT_NAME.search(text) for _, text in sections) else ""
    )
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
        + units
        + scripts
        + "A handoff is rejected unless it does all of this:\n"
        f"- name {run.issuer_name} in `## Request`, and state the as-of date {run.as_of} there;\n"
        "- list each issuer source it relied on in `## Sources`, with its exact name and sha256;\n"
        "- list each supplied handoff in `## Sources`, with its module and exact sha256"
        + (
            f";\n- place `### {opening}` once, after the two tables of `### Reader summary` and "
            "before any other table: its first content is prose that states the view.\n\n"
            if opening
            else ".\n\n"
        )
        + READER_SECTION_RULES
        + READER_PERSONA
        + (READER_STANDARD if module in READER_STANDARD_MODULES else "")
        + (
            "Report selectors, each exactly once inside `## Findings`, using these exact "
            f"headings. They place content in the report and are not analytical completion:\n"
            f"{selectors}\n\n"
            if selectors
            else ""
        )
        + paragraph
        + consumer
        + pro_forma
        + f"Selected method, verbatim:\n\n{method}\n"
    ).encode()


@dataclass(frozen=True)
class _Now:
    """What this run will ask: the facts a stopped run's answer is compared with."""

    config: str
    run: Run
    ordered: tuple[str, ...]
    texts: Mapping[str, bytes]
    sources: Mapping[str, bytes]
    layout: MarkdownLayout


def _mismatch(
    record: Accepted | None, module: str, now: _Now, kept: Mapping[str, bytes], position: int
) -> str:
    """Why a stopped run's answer cannot stand for this run's module, or "" when it can."""
    if record is None:
        return "the stopped run did not reach it"
    if record.problem:
        return record.problem
    if record.model is None:
        return "the stopped run's model setting could not be read"
    chosen = CONFIGS[now.config]
    asked = record.request
    upstream = {prior: _sha(kept[prior]) for prior in now.ordered[:position]}
    differences = (
        (
            record.model != (chosen.provider, chosen.model, chosen.effort),
            "the stopped run used a different model setting",
        ),
        (
            asked.get("run") != now.run.model_dump(mode="json"),
            "the run's identity or scope changed",
        ),
        (
            asked.get("sources") != {k: _sha(v) for k, v in now.sources.items()},
            "its sources or context changed since the stopped run",
        ),
        (asked.get("handoffs") != upstream, "the modules before it differ from the stopped run's"),
        (
            asked.get("instructions") != now.texts[module].decode(),
            "its instructions changed since the stopped run",
        ),
    )
    if why := next((reason for differs, reason in differences if differs), ""):
        return why
    task = HandoffTask(
        now.run,
        module,
        now.texts[module],
        MappingProxyType(dict(now.sources)),
        MappingProxyType({prior: kept[prior] for prior in upstream}),
        1,
        (),
    )
    refused = _checked_handoff(task, record.response, checker(now.layout))
    return "the current checks no longer accept it" if refused else ""


def _retained_prefix(
    now: _Now, retained: Mapping[str, Accepted]
) -> tuple[dict[str, Accepted], tuple[str, str]]:
    """The longest prefix of the plan whose answers still stand, and where and why it ended.
    CP-OS needs the whole upstream chain, so the first module that fails ends it."""
    kept: dict[str, Accepted] = {}
    for position, module in enumerate(now.ordered):
        why = _mismatch(
            retained.get(module), module, now, {m: r.response for m, r in kept.items()}, position
        )
        if why:
            return kept, (module, why)
        kept[module] = retained[module]
    return kept, ("", "")


def prepare(  # noqa: PLR0913 - one keyword per run setting; retained is the resume input
    context: Path,
    sources: Path,
    out: Path | None,
    *,
    config: str,
    cap: Decimal | str,
    modules: Sequence[str] | None = None,
    retained: Mapping[str, Accepted] | None = None,
) -> Prepared:
    """Check everything and write the manifest and instructions; a refusal writes nothing.

    `retained` holds a stopped run's accepted answers. The longest prefix of the plan whose
    answers still match this run's sources, instructions and model, and pass the current
    checker, is pinned for replay; the first module that fails ends it and is named."""
    context_path = Path(context).expanduser().resolve()
    folder = Path(sources).expanduser().resolve()
    raw_context = context_path.read_bytes()
    settings = load_context(raw_context)
    defaults = tuple(m for m in PATHWAY_MODULES[settings.run.pathway] if m not in NOT_ANALYTICAL)
    if settings.run.run_type == "primary" and "CP-1D" not in defaults:
        defaults += ("CP-1D",)  # The add-back register CP-2's pro forma ladder reads.
    requested = tuple(modules) if modules else defaults
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
    pinned, converted, ignored, covers = _issuer_files(folder, context_path, directory)
    aliases = tuple(a for a in settings.identity.aliases if a.strip())
    layout, omitted = _layout(
        run,
        ordered,
        aliases,
        config,
        run_type=settings.run.run_type,
        legal_documents=settings.attachments.legal_documents,
    )
    texts = {
        m: _instructions(
            run,
            m,
            layout.routes,
            run_type=settings.run.run_type,
            legal_documents=settings.attachments.legal_documents,
        )
        for m in ordered
    }
    guesses = {key: guess_kind(name, pages) for key, (name, pages) in covers.items()}
    items = expectations(
        ordered, tuple(guesses.values()), settings, edges_for(ordered), omitted=omitted
    )
    documents = tuple(
        {
            "source": key,
            "kind": g.kind,
            "signal": g.signal,
            "executed": g.executed,
            "period_end": g.period_end,
        }
        for key, g in guesses.items()
    )
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
    source_bytes = {
        name: converted[spec.path]
        if spec.path in converted
        else Path(os.path.normpath(directory / spec.path)).read_bytes()
        for name, spec in request.sources.items()
    }
    now = _Now(config, run, ordered, texts, source_bytes, layout)
    kept, stop = _retained_prefix(now, retained or {})
    request = request.model_copy(
        update={
            "retained_handoffs": {
                m: RetainedHandoff(
                    path=f"retained/{m}.md",
                    sha256=_sha(kept[m].response),
                    source_hashes=dict(kept[m].request["sources"]),
                    upstream=dict(kept[m].request["handoffs"]),
                )
                for m in kept
            }
        }
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
    for module, record in kept.items():
        _put(directory / "retained" / f"{module}.md", record.response)
    _put(manifest, raw)
    return Prepared(
        directory,
        manifest,
        request,
        layout,
        ordered,
        ignored,
        omitted,
        hold,
        tuple(kept),
        stop,
        documents,
        tuple(items),
    )


def without_for(ordered: Sequence[str], items: Sequence[Item]) -> dict[str, list[str]]:
    """For each declaration-based Will refuse module: itself and, transitively, every ordered module
    that requires it (a registry required dependency; optional and restricted consumers stay), in
    run order. An inherited Will refuse offers nothing: its producer does."""
    required = {m.module_id: set(m.required) for m in modules()}
    result: dict[str, list[str]] = {}
    for item in items:
        if item["outcome"] != "will_refuse" or item["inherited_from"] or item["scope"] == "run":
            continue
        removed = {item["scope"]}
        grew = True
        while grew:
            grew = False
            for module in ordered:
                if module not in removed and required.get(module, set()) & removed:
                    removed.add(module)
                    grew = True
        result[item["scope"]] = [m for m in ordered if m in removed]
    return result


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _body(lines: list[str], heading: str, level: int) -> list[str]:
    """The lines under one heading, or none when it is missing or repeated. The report adapter
    refuses that itself; here a missing section reads as empty, so the label checks still name it
    as lacking Provisional."""
    try:
        return [line for _, line in section(lines, heading, (level,))]
    except ValueError:
        return []


def _register(lines: list[str]) -> list[list[str]] | None:
    """The register's data rows; None when the heading, the exact header or a row is missing."""
    rows: list[list[str]] = []
    for line in _body(_body(lines, "Findings", 2), REGISTER_HEADING, 3):
        found = table_row(line)
        if found is not None:
            rows.append(_cells(found))
        elif rows:
            break
    if not rows or rows[0] != REGISTER_HEADER or len(rows) < 3:
        return None
    if not all(re.fullmatch(r":?-+:?", cell) for cell in rows[1]):  # No separator: not a table.
        return None
    return rows[2:]


def _main_limitation(lines: list[str]) -> str:
    rows = [_cells(r) for r in map(table_row, _body(lines, "Reader summary", 3)) if r]
    if len(rows) < 3 or "Main limitation" not in rows[0]:
        return ""
    cells = rows[2]
    return cells[rows[0].index("Main limitation")] if len(cells) == len(rows[0]) else ""


def _row_problem(row: list[str]) -> str:
    if len(row) != len(REGISTER_HEADER):
        return f"needs {len(REGISTER_HEADER)} cells"
    document, kind, status, rank, source = row
    if not document.strip() or not source.strip():
        return "Document and Source must both be named"
    if kind not in KIND_RANK:
        return f"Kind `{kind}` is not one of the listed kinds"
    if status not in STATUSES:
        return f"Status `{status}` is not one of {', '.join(STATUSES)}"
    if rank != KIND_RANK[kind]:
        return f"Authority rank for `{kind}` is {KIND_RANK[kind]}"
    return ""


def _problem(category: str, detail: str) -> str:
    return f"{PROVISIONAL_ISSUES[category]}: {detail}"


def _valid_rows(register: list[list[str]]) -> tuple[list[list[str]], list[str]]:
    valid, issues = [], []
    for row in register:
        if problem := _row_problem(row):
            issues.append(_problem("register_malformed", f"`{' | '.join(row)}`: {problem}."))
        elif row[1] == MARKETING_KIND and row[2] == "executed":
            issues.append(
                _problem("executed_marketing_document", f"`{row[0]}` is marketing, never executed.")
            )
        else:
            valid.append(row)
    return valid, issues


def _label_issues(lines: list[str], routes: Sequence[MarkdownRoute]) -> list[str]:
    issues = [
        _problem("provisional_section_missing", f"write {PROVISIONAL} in {route.heading}.")
        for route in routes
        if PROVISIONAL not in "\n".join(_body(lines, route.heading, 3))
    ]
    if PROVISIONAL not in _main_limitation(lines):
        issues.append(
            _problem(
                "provisional_main_limitation_missing",
                f"write {PROVISIONAL} in the Reader summary's Main limitation.",
            )
        )
    return issues


def cp4_issues(task: HandoffTask, text: str, routes: Sequence[MarkdownRoute]) -> tuple[str, ...]:
    """C-1 to C-7: CP-4's register and Provisional labels, for a run whose instructions carry the
    Provisional paragraph. Structure only; the analysis is never judged."""
    if PROVISIONAL_PARAGRAPH.encode() not in task.instructions:
        return ()
    lines = text.splitlines()
    register = _register(lines)
    if register is None:
        if BLOCKED_LINE in text:  # The method's Blocked message stands with no legal document.
            return ()
        return (
            _problem(
                "register_missing",
                f"add `### {REGISTER_HEADING}` inside ## Findings, with one table headed "
                f"`| {' | '.join(REGISTER_HEADER)} |` and a row per document read.",
            ),
        )
    valid, issues = _valid_rows(register)
    ranked = [row for row in valid if row[1] != OTHER_KIND]
    if not ranked:
        if BLOCKED_LINE not in text and not issues:
            issues.append(
                _problem(
                    "blocked_line_missing",
                    f"state `{BLOCKED_LINE}` and the method's Blocked message.",
                )
            )
        return tuple(issues)
    statuses = [row[2] for row in ranked]
    unsigned = [s for s in statuses if s != "executed"]
    all_final = bool(unsigned) and all(s == "final" for s in unsigned)
    has_final = "final" in statuses
    needs_limit = any(s in ("draft", "indicative") for s in statuses) or (
        "executed" not in statuses and not all_final
    )
    if needs_limit and DRAFT_LIMITATION not in text:
        issues.append(_problem("draft_limitation_missing", f"state: {DRAFT_LIMITATION}"))
    if has_final and FINAL_OM_REASON not in text:
        issues.append(_problem("final_om_reason_missing", f"state: {FINAL_OM_REASON}"))
    if all_final and FINAL_OM_DRAFT_WORDING in text:
        issues.append(
            _problem(
                "final_om_draft_wording", "remove the draft sentence; every document is final."
            )
        )
    if needs_limit or has_final:
        issues += _label_issues(lines, routes)
    return tuple(issues)


def consumer_issues(task: HandoffTask, text: str) -> tuple[str, ...]:
    """C-8: a consumer of a Provisional CP-4 handoff says so."""
    upstream = task.handoffs.get("CP-4", b"")
    provisional = DRAFT_LIMITATION.encode() in upstream or FINAL_OM_REASON.encode() in upstream
    if task.module_id in CONSUMERS and provisional and PROVISIONAL not in text:
        return (
            _problem(
                "consumer_provisional_missing",
                f"the CP-4 handoff is {PROVISIONAL}; write {PROVISIONAL} where this module uses "
                "its terms.",
            ),
        )
    return ()


# R-L6, R-L8 and R-L16: with commas the first group has 1 to 3 digits and each later group
# exactly 3;
# the minus is the ASCII hyphen only; there is no plus sign and no bare leading point.
NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
AMOUNT = re.compile(f"-?{NUMBER}")
# R-L7: the reason holds a letter or digit. The lookahead scans once and cannot backtrack.
NOT_SUPPLIED_WITH_REASON = re.compile(r"Not supplied:(?=[\W_]*[^\W_])\s.*")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# R-L12 and R-L15: `FX rate: <rate> (<source>)`; the rate may follow a pair such as EUR/USD.
FX_LINE = re.compile(rf"FX rate: (?:[A-Z]{{3}}/[A-Z]{{3}} )?{NUMBER} \(\s*\S.*\)")
# R-L9: a pair of `**`, `__`, `*` or `_` around text. An opening marker follows a non-word
# character and a closing one precedes a non-space, so `snake_case` and `* item` are left alone.
EMPHASIS_DEPTH = 4
EMPHASIS = re.compile(r"(?<!\w)(\*\*|__|\*|_)(?=\S)((?:(?!\1).)+?)(?<=\S)\1(?!\w)")
TOTAL_DEBT = re.compile(r"Total debt \((.+)\)")
ALL_CURRENCIES_TOTAL = "Total debt (all currencies)"
LIST_MARKER = re.compile(r"[-*]\s+")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
CURRENCY_CODE = re.compile(r"[A-Z]{3}")
Rule = Callable[[str], str]


def _pf(category: str, table: str, detail: str) -> str:
    return f"{PRO_FORMA_ISSUES[category]}: {table}: {detail}"


def _amount(cell: str) -> str:
    if AMOUNT.fullmatch(cell) or NOT_SUPPLIED_WITH_REASON.fullmatch(cell):
        return ""
    base = (
        "write a plain number such as `1,234`, `-18` or `0.5`, with no plus sign (a leading ASCII "
        "minus `-` if negative) or `Not supplied: <reason>`"
    )
    if cell.startswith("Not supplied:"):
        return f"{base}; the reason needs at least one letter or digit"
    if "\u2212" in cell:
        return f"{base}; the minus is the ASCII `-`, never U+2212"
    if "," in cell:
        return (
            f"{base}; a comma must be followed by exactly three digits and the first group has "
            "one to three digits"
        )
    return base


def _named(cell: str) -> str:
    return "" if cell else "must not be blank"


def _currency(cell: str) -> str:
    return "" if CURRENCY_CODE.fullmatch(cell) else "must be a 3-letter currency code"


def _one_of(*words: str) -> Rule:
    return lambda cell: "" if cell in words else f"must be one of {', '.join(words)}"


def _plain(text: str) -> str:
    """R-L9: a heading, label or cell without emphasis (`**`, `__`, `*`, `_`) or surrounding
    whitespace. Read-only: delivery passes the cell on unchanged."""
    text = text.strip()
    for _ in range(EMPHASIS_DEPTH):  # A bounded number of nested layers keeps this linear.
        stripped = EMPHASIS.sub(r"\2", text)
        if stripped == text:
            break
        text = stripped
    return text.strip()


def _label_text(line: str) -> str:
    """R-L9 and R-L10: a label line without emphasis and without a `- ` or `* ` list marker."""
    return LIST_MARKER.sub("", _plain(line), count=1)


def _labelled(line: str, label: str) -> str | None:
    """The value on a `<label> <value>` line, or None when the line does not start with it."""
    text = _label_text(line)
    return text.removeprefix(label).strip() if text.startswith(label) else None


def _under(lines: list[str], title: str, level: int) -> list[str]:
    """The lines under the one heading of this level and title (R-L9: emphasis and surrounding
    whitespace ignored), up to the next heading of the same or a higher level. None or several
    such headings give no lines, so the table reads as missing."""
    wanted = "#" * level + f" {title}"
    starts = [i for i, line in enumerate(lines) if _plain(line) == wanted]
    if len(starts) != 1:
        return []
    stop = tuple("#" * size + " " for size in range(1, level + 1))
    rest = lines[starts[0] + 1 :]
    return next(
        (rest[:i] for i, line in enumerate(rest) if _plain(line).startswith(stop)),
        rest,
    )


def _findings(text: str) -> list[str]:
    """R-L1: the lines under `## Findings`, the only place a pro forma table is read. CRLF and a
    lone CR are read as LF (R-L13; delivery's `physical_lines` also splits on a lone CR). R-L19:
    fenced code is not read, so a heading or table in a fence is neither a pro forma table nor a
    repeat of one. Delivery's own fence reader is simpler (see METHODOLOGY-REVIEW.md, R-L19)."""
    return _under(unfenced(re.sub(r"\r\n?", "\n", text)), "Findings", 2)


def _row_cells(row: str) -> list[str]:
    """R-L11: the cells of a table row; `\\|` is a literal pipe, not a column break."""
    inner = row.removeprefix("|")
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    return [cell.strip().replace("\\|", "|") for cell in UNESCAPED_PIPE.split(inner)]


def _pro_forma_table(
    findings: list[str], heading: str, header: Sequence[str]
) -> list[list[str]] | None:
    """The data rows of one pro forma table under `## Findings`; None when its heading is missing
    or repeated, its exact header is absent or it has no separator row. A row label is read
    without emphasis (R-L9)."""
    rows: list[list[str]] = []
    for line in _under(findings, heading, 3):
        found = table_row(line)
        if found is not None:
            rows.append(_row_cells(found))
        elif rows:
            break
    if len(rows) < 2 or [_plain(c) for c in rows[0]] != list(header):
        return None
    if len(rows[1]) != len(header) or not all(re.fullmatch(r":?-+:?", c) for c in rows[1]):
        return None
    return [[_plain(cell) for cell in row] for row in rows[2:]]


def _missing(heading: str, header: Sequence[str]) -> str:
    detail = (
        f"write `### {heading}` once inside the one `## Findings` section (a table outside "
        f"`## Findings` is not read; headings are written exactly as shown), a table headed "
        f"{_header(header)}"
    )
    return _pf("pro_forma_table_missing", heading, detail + " and a separator row.")


def _whole_rows(
    heading: str, header: Sequence[str], rows: list[list[str]]
) -> tuple[list[list[str]], list[str]]:
    """The rows with the right number of cells, and one cell issue for each other row."""
    issues = [
        _pf("pro_forma_cell", heading, f"`{' | '.join(row)}` needs {len(header)} cells.")
        for row in rows
        if len(row) != len(header)
    ]
    return [row for row in rows if len(row) == len(header)], issues


def _cell_issues(
    heading: str,
    header: Sequence[str],
    rows: list[list[str]],
    rules: Mapping[str, Rule],
    label: Callable[[list[str]], str] = lambda row: row[0],
) -> list[str]:
    return [
        _pf("pro_forma_cell", heading, f"row `{label(row)}`, column {column}: {problem}.")
        for row in rows
        for column, rule in rules.items()
        if (problem := rule(row[header.index(column)]))
    ]


def _fixed_rows(heading: str, labels: Sequence[str], rows: list[list[str]]) -> list[str]:
    """Rows that must be exactly these labels, each once, in this order."""
    found = [row[0] for row in rows]
    if found == list(labels):
        return []
    lacking = [label for label in labels if label not in found]
    repeated = [label for label in labels if found.count(label) > 1]
    extra = [label for label in found if label not in labels]
    if lacking or repeated or extra:
        detail = (
            f"missing {lacking}; repeated {repeated}; not allowed {extra}; "
            f"write exactly these rows once each: {list(labels)}."
        )
    else:
        detail = f"rows are out of order; write them in this order: {list(labels)}."
    return [_pf("pro_forma_rows", heading, detail)]


def _by_label(rows: list[list[str]]) -> dict[str, list[str]]:
    return {row[0]: row for row in reversed(rows)}  # The first of any repeat wins.


COMMITMENT = "(commitment)"


def _sources_uses_total_issues(heading: str, rows: list[list[str]]) -> list[str]:
    """R-C2-1 fail closed. A side's total is written only when every row of that side holds a
    number: one `Not supplied` row means no total for that side. A `Memo` row is neither a Source
    nor a Use row, so it is in no count and no total. Nothing is summed (a commitment inside a
    total is told by the instruction only)."""
    totals = {"Total sources": "Source", "Total uses": "Use"}
    plain = [row for row in rows if row[1] not in totals]
    issues = []
    for side in ("Source", "Use"):
        item = next(i for i, s in totals.items() if s == side)
        side_rows = [row for row in plain if row[0] == side]
        if not side_rows:
            issues.append(_pf("pro_forma_rows", heading, f"write at least one {side} row."))
        written = sum(1 for row in rows if (row[0], row[1]) == (side, item))
        if any(NOT_SUPPLIED_WITH_REASON.fullmatch(row[2]) for row in side_rows):
            if written:
                issues.append(
                    _pf(
                        "pro_forma_rows",
                        heading,
                        f"write no `{item}` row: a {side} row is `Not supplied`, and a total is "
                        f"written only when every {side} row holds a number.",
                    )
                )
        elif written != 1:
            issues.append(
                _pf("pro_forma_rows", heading, f"write exactly one `{item}` row with Side {side}.")
            )
    return issues


def _sources_uses_issues(lines: list[str]) -> list[str]:
    heading, header = SOURCES_USES_HEADING, SOURCES_USES_HEADER
    table = _pro_forma_table(lines, heading, header)
    if table is None:
        return [_missing(heading, header)]
    rows, issues = _whole_rows(heading, header, table)
    rules = {
        "Side": _one_of("Source", "Use", "Memo"),
        "Item": _named,
        "Amount": _amount,
        "Currency": _named,
        "Basis": _one_of(*BASES),
        "Source": _named,
    }
    issues += _cell_issues(heading, header, rows, rules, lambda row: f"{row[0]} / {row[1]}")
    issues += [
        _pf(
            "pro_forma_cell",
            heading,
            f"row `{row[0]} / {row[1]}`, column Item: a Memo row holds a commitment, so its "
            f"Item ends with `{COMMITMENT}`.",
        )
        for row in rows
        if row[0] == "Memo" and not row[1].endswith(COMMITMENT)
    ]
    return issues + _sources_uses_total_issues(heading, rows)


def _add_back_issues(lines: list[str]) -> list[str]:
    heading, header = ADD_BACK_HEADING, ADD_BACK_HEADER
    table = _pro_forma_table(lines, heading, header)
    if table is None:
        return [_missing(heading, header)]
    if not table:
        return [_pf("pro_forma_rows", heading, "write at least one add-back row.")]
    rows, issues = _whole_rows(heading, header, table)
    rules = {
        "Add-back": _named,
        "Run-rate claimed": _amount,
        "Realised to date": _amount,
        "Amount already in LTM": _amount,
        "Verdict": _one_of(*VERDICTS),
        "Source": _named,
    }
    return issues + _cell_issues(heading, header, rows, rules)


def _above_table(body: list[str]) -> list[str]:
    above = []
    for line in body:
        if table_row(line) is not None:
            break
        above.append(line)
    return above


def _capitalisation_issues(lines: list[str]) -> list[str]:
    heading, header = CAPITALISATION_HEADING, CAPITALISATION_HEADER
    table = _pro_forma_table(lines, heading, header)
    if table is None:
        return [_missing(heading, header)]
    rows, issues = _whole_rows(heading, header, table)
    body = _under(lines, heading, 3)
    dates = [v for line in body if (v := _labelled(line, "Balance-sheet date:")) is not None]
    periods = [v for line in body if (v := _labelled(line, "LTM period:")) is not None]
    if len(dates) != 1 or not ISO_DATE.fullmatch(dates[0]):
        issues.append(
            _pf("pro_forma_basis", heading, "write one line `Balance-sheet date: YYYY-MM-DD`.")
        )
    if len(periods) != 1 or not periods[0]:
        issues.append(_pf("pro_forma_basis", heading, "write one line `LTM period: <text>`."))
    rules = {
        "Instrument": _named,
        "Currency": _currency,
        "Balance sheet": _amount,
        "Transaction adjustment": _amount,
        "Pro forma": _amount,
        "Basis": _one_of(*BASES),
        "Source": _named,
    }
    issues += _cell_issues(heading, header, rows, rules)
    has_fx = any(FX_LINE.fullmatch(_label_text(line)) for line in _above_table(body))  # R-L2
    return issues + _capitalisation_rows(heading, rows, has_fx)


def _total_issues(heading: str, totals: list[list[str]], used: set[str]) -> list[str]:
    """R-L4 and R-L5: each `Total debt (CCY)` row is in the currency its label names, and names a
    currency some debt row uses."""
    issues = []
    for row in totals:
        ccy = TOTAL_DEBT.fullmatch(row[0])
        if ccy is None or row[0] == ALL_CURRENCIES_TOTAL:
            continue
        if ccy[1] not in used:
            detail = (
                f"row `{row[0]}`: no debt row uses {ccy[1]}; write no total for a currency "
                "that no debt row uses."
            )
            if ccy[1].upper() in used:  # R-L17: the label is exact, the code in upper case.
                detail = (
                    f"row `{row[0]}`: write the label exactly as shown, expected "
                    f"`Total debt ({ccy[1].upper()})`, with the currency code in upper case."
                )
            issues.append(_pf("pro_forma_rows", heading, detail))
        elif row[1] != ccy[1]:
            issues.append(
                _pf(
                    "pro_forma_cell",
                    heading,
                    f"row `{row[0]}`: Currency must equal the code in the label ({ccy[1]}).",
                )
            )
    return issues


def _capitalisation_rows(heading: str, rows: list[list[str]], has_fx: bool) -> list[str]:
    """P-2, P-5 and P-6 for the capitalisation table: Cash, debt, per-currency totals, citations,
    FX."""
    issues = []
    cash = [row for row in rows if row[0] == "Cash"]
    if len(cash) != 1:
        issues.append(_pf("pro_forma_rows", heading, "write exactly one `Cash` row."))
    totals = [row for row in rows if TOTAL_DEBT.fullmatch(row[0])]
    debt = [row for row in rows if row[0] != "Cash" and row not in totals]
    if not debt:  # R-L3: with no debt row the CP-1A citation would be vacuous.
        issues.append(
            _pf(
                "pro_forma_rows",
                heading,
                "write at least one debt row (a Cash row alone is not enough).",
            )
        )
    used = {row[1] for row in debt if CURRENCY_CODE.fullmatch(row[1])}
    for ccy in sorted(used):
        if sum(1 for row in totals if row[0] == f"Total debt ({ccy})") != 1:
            issues.append(
                _pf(
                    "pro_forma_rows",
                    heading,
                    f"write exactly one `Total debt ({ccy})` row, with the label exactly as "
                    "shown and the currency code in upper case.",
                )
            )
    issues += _total_issues(heading, totals, used)
    if any(row[0] == ALL_CURRENCIES_TOTAL for row in totals) and not has_fx:
        issues.append(
            _pf(
                "pro_forma_fx",
                heading,
                "write the line `FX rate: <rate> (<source>)` (an optional pair `AAA/BBB` before "
                "the rate) under the heading, above the table, before a cross-currency total; a "
                "line after the table does not count, and neither does a line above the heading.",
            )
        )
    issues += [
        _pf("pro_forma_cp1a_citation", heading, f"row `{row[0]}`: Source must cite CP-1A.")
        for row in [*cash, *totals]
        if row[6] and "CP-1A" not in row[6]
    ]
    return issues


def _ladder_basis(heading: str, row: Mapping[str, list[str]]) -> list[str]:
    """P-4 for the ladder: a named definition for (a), `calculate` for Base and (e). A blank cell
    is reported as a cell issue instead."""
    issues = []
    start = row.get(LADDER_ROWS[0])
    if start and start[3] and not any(d in start[3] for d in EBITDA_DEFINITIONS):
        issues.append(
            _pf(
                "pro_forma_basis",
                heading,
                f"row (a) Definition or basis must name one of {', '.join(EBITDA_DEFINITIONS)}.",
            )
        )
    base = row.get(LADDER_ROWS[2])
    if base and base[4] and "calculate" not in base[4]:
        issues.append(
            _pf("pro_forma_basis", heading, "the Base EBITDA Source must cite calculate.")
        )
    diff = row.get(LADDER_ROWS[9])
    if diff and diff[4] and not _amount(diff[1]):
        number = AMOUNT.fullmatch(diff[1]) is not None
        if number and "calculate" not in diff[4]:
            issues.append(
                _pf("pro_forma_basis", heading, "row (e) with a number must cite calculate.")
            )
        if not number and not diff[1].startswith("Not supplied: Insufficient Information"):
            issues.append(
                _pf(
                    "pro_forma_basis",
                    heading,
                    "row (e) is a calculate result or `Not supplied: Insufficient Information`.",
                )
            )
    return issues


def _ladder_issues(lines: list[str]) -> list[str]:
    heading, header = LADDER_HEADING, LADDER_HEADER
    table = _pro_forma_table(lines, heading, header)
    if table is None:
        return [_missing(heading, header)]
    rows, issues = _whole_rows(heading, header, table)
    rules = {
        "Row": _named,
        "Amount": _amount,
        "Reporting unit": _named,
        "Definition or basis": _named,
        "Source": _named,
    }
    issues += _cell_issues(heading, header, rows, rules)
    issues += _fixed_rows(heading, LADDER_ROWS, rows)
    return issues + _ladder_basis(heading, _by_label(rows))


def _leverage_issues(lines: list[str]) -> list[str]:
    heading, header = LEVERAGE_HEADING, LEVERAGE_HEADER
    table = _pro_forma_table(lines, heading, header)
    if table is None:
        return [_missing(heading, header)]
    rows, issues = _whole_rows(heading, header, table)
    rules = {
        "Basis": _named,
        "Total debt": _amount,
        "EBITDA": _amount,
        "Total debt / EBITDA": _amount,
        "Reporting unit": _named,
        "Source": _named,
    }
    issues += _cell_issues(heading, header, rows, rules)
    issues += _fixed_rows(heading, LEVERAGE_ROWS, rows)
    pro_forma = _by_label(rows).get(LEVERAGE_ROWS[1])
    if pro_forma and pro_forma[5] and "CP-1A" not in pro_forma[5]:
        issues.append(
            _pf(
                "pro_forma_cp1a_citation", heading, f"row `{pro_forma[0]}`: Source must cite CP-1A."
            )
        )
    return issues


def _cp2_pro_forma_issues(lines: list[str]) -> list[str]:
    return _capitalisation_issues(lines) + _ladder_issues(lines) + _leverage_issues(lines)


PRO_FORMA_CHECKS: tuple[tuple[str, Callable[[list[str]], list[str]]], ...] = (
    (PRO_FORMA_CP1A, _sources_uses_issues),
    (PRO_FORMA_CP1D, _add_back_issues),
    (PRO_FORMA_CP2, _cp2_pro_forma_issues),
)


def pro_forma_issues(task: HandoffTask, text: str) -> tuple[str, ...]:
    """P-1 to P-7: the pro forma tables of a module whose instructions carry its constant, and
    nothing elsewhere. Structure only: no number is summed or compared."""
    lines = _findings(text)
    issues: list[str] = []
    for constant, check in PRO_FORMA_CHECKS:
        if constant.encode() in task.instructions:
            issues += check(lines)
    return tuple(issues)


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
        issues += reader_issues(text)
        opening = OPENING.get(task.module_id)
        if opening and not _opens_with(text.splitlines(), opening):
            issues.append(
                f"Place ### {opening} once, after the two tables of ### Reader summary and "
                "before any other table: its first content is prose that states the view."
            )
        routes = tuple(r for r in layout.routes if r.module_id == task.module_id)
        try:
            if routes:
                own = layout.model_copy(
                    update={
                        "blocks": tuple(dict.fromkeys(r.block_id for r in routes)),
                        "routes": routes,
                        "front": tuple(r for r in layout.front if r.module_id == task.module_id),
                    }
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
        for route in routes:
            if route.kind == "chart":
                issues += chart_issues(text, route)
        issues += cp4_issues(task, text, routes) + consumer_issues(task, text)
        issues += pro_forma_issues(task, text)
        return tuple(issues)

    return check


def _opens_with(lines: list[str], heading: str) -> bool:
    """`## Findings` starts with `### Reader summary`, then the one `### heading`, whose first
    content is a paragraph: a line opening with a letter, a quote mark or bold, not a table, list,
    fence, comment or heading.
    """
    try:
        findings = [line for _, line in section(lines, "Findings") if line.strip()]
        body = [line.strip() for _, line in section(lines, heading) if line.strip()]
    except ValueError:  # Missing or repeated.
        return False
    first = body[0] if body else ""
    headings = [line for line in findings if line.startswith("### ")]
    return (
        findings[:1] == ["### Reader summary"]
        and headings[1:2] == [f"### {heading}"]
        and (first[:1].isalpha() or first.startswith(("**", '"', "“")))
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
        copilot_live = args.live and CONFIGS[args.config].provider == "copilot"
        if copilot_live and not Path(os.environ.get(COPILOT_RUNTIME_VARIABLE, "")).is_file():
            raise LaunchRefused(f"--live needs {COPILOT_RUNTIME_VARIABLE} to name an existing file")
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
        print(
            f"Stopped: {with_notes(error)}\nRetained work is in {prepared.directory}",
            file=sys.stderr,
        )
        return 1
    spent = Budget(prepared.plan.provider_cap_usd, prepared.directory / "live").spent
    print(f"Report:   {report}\nCharged:  USD {spent}")
    print("Automated checks only: review the handoffs against the sources before relying on this.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
