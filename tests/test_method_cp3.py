"""Stage 1 proof for CP-3 (relative value): the reused engine, called through
`deploy_workflow.owners.cp3.compute`, equals the frozen oracle `cases/cp3-cp6-owner/expected.json`
on the positive and gap literals, the blocked-CP-1A variant and the CP-3 validator refusals.

Every expected value is read from the oracle. Inputs come from the oracle's own sources:
the pack from the source manifests, CP-0 authority from `upstream.CP-0.R3.facts`, CP-2 rows from
the S1 oracle (`cases/snapshot/expected.json#positive.CP-2`, which the CP-3 oracle names as
unchanged) and CP-1 figures from `cases/financial/manifest.json` `q4_ltm_metric_oracle`. CP-1
fact ids, labels and periods are run-time bindings in the oracle (`run_time_bindings`); this
Stage 1 fixture fixes them once and substitutes them into the oracle's placeholders.
"""

import copy
import dataclasses
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any

import pytest

from deploy_vii.contracts import (
    Fact,
    Input,
    Module,
    ReportTable,
    Run,
    Source,
    Span,
    TableColumn,
    TableRow,
)
from deploy_vii.cp3_relative_value import RelativeValueSubmission, _sentences_of
from deploy_vii.cp6_committee import cp3_catalogue
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners.cp3 import CP3Inputs, CP3Result, candidate, compute, context

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp3-cp6-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
FINANCIAL: dict[str, Any] = json.loads((ROOT / "cases/financial/manifest.json").read_text())
SNAPSHOT: dict[str, Any] = json.loads((ROOT / "cases/snapshot/manifest.json").read_text())
S1_EXPECTED: dict[str, Any] = json.loads((ROOT / "cases/snapshot/expected.json").read_text())

CASE_IDS = {"positive": "cp3-cp6-positive", "gap": "cp3-cp6-gap"}
CP2_REGISTERS = ("T2.1", "T2.7", "T2.10", "T2.11", "T2.12")
FIG_RE = re.compile(r"\{\{FIG:([a-z_]+)\}\}")
PLACEHOLDER_RE = re.compile(r"<label and period of FIG:([a-z_]+)>")


# Oracle pins: cases/PINS.json, the shared manifest LEAD regenerates (python3 -I cases/pins.py).
PINS: dict[str, str] = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
PINNED = ("manifest.json", "submissions.json", "expected.json", "builder/build.py")


def test_oracle_files_are_the_pinned_revision() -> None:
    for name in PINNED:
        digest = hashlib.sha256((CASE / name).read_bytes()).hexdigest()
        assert digest == PINS[f"cases/cp3-cp6-owner/{name}"], name


# --- inputs from the oracle's sources ------------------------------------------------------------


def _pages(source_id: str) -> tuple[list[dict[str, str]], str]:
    if source_id == "market":
        market = MANIFEST["market_source"]
        return market["pages"], market["sha256"]
    if source_id == "business":
        business = SNAPSHOT["business_source"]["positive"]
        return business["pages"], business["sha256"]
    item = next(s for s in FINANCIAL["sources"] if s["source_id"] == source_id)
    return item["pages"], item["sha256"]


def make_pack(case: str) -> PreparedPack:
    entry = next(c for c in MANIFEST["cases"] if c["case_id"] == CASE_IDS[case])
    sources = []
    for item in entry["pack_sources"]:
        pages, sha = _pages(item["source_id"])
        spans = tuple(Span(locator=p["locator"], text=p["text"]) for p in pages)
        assert hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest() == sha
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["name"],
                status=item["status"],
                sha256=sha,
                spans=spans,
                extraction_status="complete",
                limitation=item["limitation"],
            )
        )
    run = Run.model_validate_json(json.dumps(entry["runs"]["R3"]["run"]))
    return PreparedPack(run=run, sources=tuple(sources))


def _module(pack: PreparedPack, module_id: str, **fields: Any) -> Module:
    run = pack.run
    fields.setdefault("status", "restricted")
    fields.setdefault("limitations", ("Synthetic case; not real issuer qualification",))
    return Module(
        run_id=run.run_id, issuer_id=run.issuer_id, as_of=run.as_of, module_id=module_id, **fields
    )


def make_cp0(pack: PreparedPack, case: str) -> Module:
    """CP-0's T3 authority cells, from `upstream.CP-0.R3.facts` (the cells CP-3 reads)."""
    facts = []
    for item in EXPECTED[case]["upstream"]["CP-0"]["R3"]["facts"]:
        table_id, row_id, field = item["fact_id"].split(".")
        if table_id == "T3" and field == "authority":
            facts.append(
                Fact(
                    fact_id=item["fact_id"],
                    label="Authority",
                    table_id=table_id,
                    row_id=row_id,
                    field=field,
                    text=item["text"],
                )
            )
    return _module(pack, "CP-0", facts=tuple(facts))


def fig_fact(name: str) -> Fact:
    """The CP-1 T4.10 LTM Q4 2025 fact for a figure: amount from the financial oracle; id, label,
    period and calculation id are this fixture's run-time binding."""
    ratio = FINANCIAL["q4_ltm_metric_oracle"][name]
    coordinate = SUBMISSIONS["figures"][name]["cp1_coordinate"]
    basis, start_end = coordinate.split(", ", 1)[1].rsplit(", ", 1)
    start, end = start_end.split(" to ")
    return Fact(
        fact_id=f"T4.10.{name}.ltm_q4_2025",
        label=name,
        table_id="T4.10",
        row_id=name,
        field="ltm_q4_2025",
        amount=Decimal(ratio["numerator"]) / Decimal(ratio["denominator"]),
        unit=ratio["unit"],
        period=f"{basis}: {start} to {end}",
        calculation_id=f"calc.{name}.ltm_q4_2025",
        value_class="calculated",
    )


FIGS = {name: fig_fact(name) for name in SUBMISSIONS["figures"]}


def make_cp1(pack: PreparedPack) -> Module:
    """CP-1's referencable figures and the T4.18 facility cells (`run_time_bindings.facility`)."""
    facility = tuple(
        Fact(
            fact_id=f"T4.18.term-loan.fy2025.{field}",
            label=field,
            table_id="T4.18",
            row_id="term-loan.fy2025",
            field=field,
            text=text,
        )
        for field, text in (
            ("facility_id", "term-loan"),
            ("facility_name", "Northbridge Term Loan"),
        )
    )
    return _module(pack, "CP-1", facts=(*FIGS.values(), *facility))


def make_cp2(pack: PreparedPack) -> Module:
    """The CP-2 register tables of the S1 positive oracle (unchanged for CP-3)."""
    tables, facts = [], []
    for table in S1_EXPECTED["positive"]["CP-2"]["tables"]:
        if table["table_id"] not in CP2_REGISTERS:
            continue
        rows = []
        for row in table["rows"]:
            for cell, column in zip(row["facts"], table["columns"], strict=True):
                known = cell["status"] == "known"
                facts.append(
                    Fact(
                        fact_id=cell["fact_id"],
                        label=cell["column"],
                        table_id=table["table_id"],
                        row_id=row["row_id"],
                        field=column["field"],
                        text=cell["text"] if known else None,
                        status=cell["status"],
                        value_class=cell["value_class"],
                        limitation=cell["limitation"],
                    )
                )
            rows.append(
                TableRow(
                    row_id=row["row_id"],
                    label=row["label"],
                    fact_ids=tuple(c["fact_id"] for c in row["facts"]),
                )
            )
        tables.append(
            ReportTable(
                table_id=table["table_id"],
                title=table["title"],
                columns=tuple(TableColumn(**c) for c in table["columns"]),
                rows=tuple(rows),
                row_header=table["row_header"],
            )
        )
    return _module(pack, "CP-2", facts=tuple(facts), tables=tuple(tables))


def make_cp1a(pack: PreparedPack, case: str, *, blocked: bool) -> Module:
    """What CP-3 reads of CP-1A: status and limitations (CONTEXT `optional_upstream`). A blocked
    head's limitations are bound at run time; the fixture marks that."""
    if blocked:
        return _module(
            pack,
            "CP-1A",
            status="blocked",
            limitations=("Stage 1 fixture: the blocked CP-1A head's issue texts bind at run time",),
        )
    optional = EXPECTED[case]["CP-3"]["context_block_checks"]["optional_upstream"]
    limits = next(o["limitations"] for o in optional if o["module_id"] == "CP-1A")
    return _module(pack, "CP-1A", limitations=tuple(limits))


def _instantiate(value: Any) -> str:
    """The literal as JSON, each `{{FIG:name}}` replaced by `{<fact_id>|<unit_token>}`
    (submissions.json note)."""

    def ref(match: re.Match[str]) -> str:
        name = match[1]
        unit = str(SUBMISSIONS["figures"][name]["unit_token"])
        return "{" + FIGS[name].fact_id + "|" + unit + "}"

    return FIG_RE.sub(ref, json.dumps(value))


def make_inputs(case: str, literal: Any = None, *, blocked_cp1a: bool = False) -> CP3Inputs:
    pack = make_pack(case)
    heads = {
        "CP-0": make_cp0(pack, case),
        "CP-1": make_cp1(pack),
        "CP-1A": make_cp1a(pack, case, blocked=blocked_cp1a),
        "CP-2": make_cp2(pack),
    }
    bound = (
        Input(input_id="prepared-pack", sha256=pack.content_hash(), status="accepted"),
        *(
            Input(
                input_id=module_id,
                sha256=head.content_hash(),
                status="blocked" if module_id == "CP-1A" and blocked_cp1a else "restricted",
            )
            for module_id, head in heads.items()
        ),
    )
    if literal is None:
        literal = SUBMISSIONS[case]["relative_value"]
    return CP3Inputs(
        pack=pack,
        submission=RelativeValueSubmission.model_validate_json(_instantiate(literal)),
        bound=bound,
        current=bound,
        cp0=heads["CP-0"],
        cp1=heads["CP-1"],
        cp2=heads["CP-2"],
        optional={"CP-1A": heads["CP-1A"]},
        inherited=(),
    )


# --- oracle comparison ---------------------------------------------------------------------------


def _bound_text(text: str | None) -> str | None:
    """Substitute the oracle's CP-1 label placeholders with the fixture binding."""
    if text is None:
        return None

    def label(match: re.Match[str]) -> str:
        fact = FIGS[match[1]]
        return f"{fact.label} · {fact.period}"

    return PLACEHOLDER_RE.sub(label, text)


def _cell(fact: Fact) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "column": fact.label,
        "text": fact.text,
        "status": fact.status,
        "cites": [[c.source_id, c.locator] for c in fact.citations],
        "value_class": fact.value_class,
        "limitation": fact.limitation,
    }


def _actual_tables(result: CP3Result) -> list[dict[str, Any]]:
    assert result.report is not None
    facts = {fact.fact_id: fact for fact in result.report.facts}
    out = []
    for table in result.report.tables:
        rows: list[dict[str, Any]] = []
        for row in table.rows:
            item: dict[str, Any] = {"row_id": row.row_id, "label": row.label}
            if table.table_id != "cp1_references":  # the oracle binds these facts at run time
                item["facts"] = [_cell(facts[i]) for i in row.fact_ids]
            rows.append(item)
        out.append(
            {
                "table_id": table.table_id,
                "title": table.title,
                "row_header": table.row_header,
                "columns": [c.model_dump() for c in table.columns],
                "rows": rows,
            }
        )
    return out


def _expected_tables(case: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = copy.deepcopy(EXPECTED[case]["CP-3"]["tables"])
    for table in tables:
        for row in table["rows"]:
            row["label"] = _bound_text(row["label"])
            row.pop("fact_binding", None)
            for fact in row.get("facts", []):
                fact["text"] = _bound_text(fact["text"])
    return tables


@pytest.fixture(scope="module", params=["positive", "gap"])
def settled(request: pytest.FixtureRequest) -> tuple[str, CP3Inputs, CP3Result]:
    inputs = make_inputs(request.param)
    return request.param, inputs, compute(inputs)


def test_composes_without_issues(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    _, _, result = settled
    assert result.issues == ()
    assert result.report is not None


def test_tables_equal_oracle(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert _actual_tables(result) == _expected_tables(case)


def test_cp1_references_bind_cp1_facts(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert result.report is not None
    order = EXPECTED[case]["CP-3"]["cp1_references_order"]
    table = next(t for t in result.report.tables if t.table_id == "cp1_references")
    facts = {fact.fact_id: fact for fact in result.report.facts}
    assert [r.row_id for r in table.rows] == [f"ref{i:02d}" for i in range(1, len(order) + 1)]
    for row, name in zip(table.rows, order, strict=True):
        (fact_id,) = row.fact_ids
        fact, source = facts[fact_id], FIGS[name]
        assert fact.fact_id == source.fact_id
        assert fact.value_class == "calculated"
        assert fact.citations == source.citations
        assert (fact.table_id, fact.row_id, fact.field) == ("cp1_references", row.row_id, "value")
        moved = {"table_id", "row_id", "field"}
        assert fact.model_dump(exclude=moved) == source.model_dump(exclude=moved)


def test_figures_spelled_as_pinned(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    _, _, result = settled
    assert result.report is not None
    view = next(f for f in result.report.facts if f.fact_id == "T3.1.i01.fundamental_view")
    for name in ("total_leverage_reported", "net_leverage_reported", "interest_coverage_reported"):
        assert SUBMISSIONS["figures"][name]["spelled"] in (view.text or "")


def test_claims_equal_oracle(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert result.report is not None
    actual = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "limitation": c.limitation,
            "cites": [[x.source_id, x.locator] for x in c.citations],
        }
        for c in result.report.claims
    ]
    assert actual == EXPECTED[case]["CP-3"]["claims"]


def test_own_limitations_equal_oracle(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, _, result = settled
    assert result.report is not None
    assert list(result.report.limitations) == EXPECTED[case]["CP-3"]["own_limitations"]


def test_catalogue_for_cp6(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    """The CP-3 rows CP-6 may cite (`cp6_committee.cp3_catalogue` over the candidate), by ref
    and row label, equal the oracle's catalogue in order."""
    case, inputs, result = settled
    catalogue = cp3_catalogue(candidate(result, inputs, attempt=0))
    actual = [(ref, row.label) for ref, row in catalogue.items()]
    assert actual == list(EXPECTED[case]["CP-3"]["catalogue_for_CP-6"].items())


def test_module_inputs(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, inputs, result = settled
    module = candidate(result, inputs, attempt=0)
    assert [i.input_id for i in module.inputs] == EXPECTED[case]["CP-3"]["module_inputs"]
    assert module.module_id == "CP-3"


def _rows(block: dict[str, object], key: str) -> list[dict[str, Any]]:
    """A list-valued CONTEXT entry, typed for the comparisons below."""
    value = block[key]
    assert isinstance(value, list)
    return value


def _upstream_statuses(block: dict[str, object]) -> dict[str, str]:
    return {u["module_id"]: u["status"] for u in _rows(block, "upstream")}


def test_context_block_checks(settled: tuple[str, CP3Inputs, CP3Result]) -> None:
    case, inputs, _ = settled
    checks = EXPECTED[case]["CP-3"]["context_block_checks"]
    block = context(inputs)
    assert _upstream_statuses(block) == checks["upstream_statuses"]
    assert [(f["facility_id"], f["name"]) for f in _rows(block, "cp1_facilities")] == [
        (f["facility_id"], f["name"]) for f in checks["cp1_facilities"]
    ]
    assert [r["ref"] for r in _rows(block, "cp2_rows")] == checks["cp2_rows"]
    assert block["optional_upstream"] == checks["optional_upstream"]
    assert block["market_evidence_sources"] == checks["market_evidence_sources"]
    assert block["market_evidence_note"] == checks["market_evidence_note"]
    assert block["confidence_caps"] == checks["confidence_caps"]
    authority = {s["source_id"]: s["authority"] for s in _rows(block, "pack_sources")}
    assert authority == checks["pack_source_authority"]


# --- blocked CP-1A variant (oracle positive.CP-3.blocked_cp1a_variant) ---------------------------


def test_blocked_cp1a_variant() -> None:
    variant = EXPECTED["positive"]["CP-3"]["blocked_cp1a_variant"]
    inputs = make_inputs("positive", blocked_cp1a=True)
    result = compute(inputs)
    assert result.issues == ()
    assert result.report is not None
    assert list(result.report.limitations) == variant["own_limitations"]
    assert _actual_tables(result) == _expected_tables("positive")
    module = candidate(result, inputs, attempt=0)
    assert [i.input_id for i in module.inputs] == variant["module_inputs"]
    statuses = {i.input_id: i.status for i in inputs.bound if i.input_id.startswith("CP-")}
    assert statuses == variant["input_statuses"]
    checks = variant["context_block_checks"]
    block = context(inputs)
    assert _upstream_statuses(block) == checks["upstream_statuses"]
    assert [(o["module_id"], o["status"]) for o in _rows(block, "optional_upstream")] == [
        (o["module_id"], o["status"]) for o in checks["optional_upstream"]
    ]
    assert block["confidence_caps"] == checks["confidence_caps"]


# --- validator refusals (oracle refusals.validator_refusals, CP-3 entries) -----------------------

CP3_REFUSALS = [e for e in EXPECTED["refusals"]["validator_refusals"] if e["owner"] == "CP-3"]
MUTATIONS = {e["id"]: e for e in SUBMISSIONS["refusal_mutations"]["entries"]}
PATH_RE = re.compile(r"([a-z0-9_]+)(?:\[(\d+)\])?")


def _walk(root: Any, path: str) -> tuple[Any, str | int]:
    parts: list[str | int] = []
    for segment in path.split("."):
        match = PATH_RE.fullmatch(segment)
        assert match is not None, segment
        parts.append(match[1])
        if match[2] is not None:
            parts.append(int(match[2]))
    node = root
    for part in parts[:-1]:
        node = node[part]
    return node, parts[-1]


def mutate(literal: Any, edits: list[list[Any]]) -> Any:
    out = copy.deepcopy(literal)
    for op, path, value in edits:
        node, key = _walk(out, path)
        if op == "set":
            node[key] = [node[key][1]] if value == "ROW1_ONLY" else copy.deepcopy(value)
        elif op == "append_text":
            node[key] = node[key] + value
        else:
            raise AssertionError(f"unknown edit {op}")
    return out


def test_every_cp3_refusal_has_a_mutation() -> None:
    assert len(CP3_REFUSALS) == 10
    owned = {m["id"] for m in MUTATIONS.values() if m["owner"] == "CP-3"}
    assert {e["id"] for e in CP3_REFUSALS} == owned


@pytest.mark.parametrize("entry", CP3_REFUSALS, ids=[e["id"] for e in CP3_REFUSALS])
def test_validator_refusal(entry: dict[str, Any]) -> None:
    mutation = MUTATIONS[entry["id"]]
    assert mutation["case"] == entry["case"]
    literal = mutate(SUBMISSIONS[entry["case"]]["relative_value"], mutation["edits"])
    result = compute(make_inputs(entry["case"], literal))
    assert result.report is None
    assert any(entry["issue_contains"] in issue for issue in result.issues), result.issues


def test_current_inputs_reach_the_engine() -> None:
    """`current` is an operand, not decoration: a current input set that differs from the bound
    one refuses the submission (wording is the engine's; not an oracle value, so not pinned)."""
    inputs = make_inputs("positive")
    stale = dataclasses.replace(inputs, current=inputs.bound[:-1])
    result = compute(stale)
    assert result.report is None


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_explicit_insufficient_evidence_can_withhold_ranking(case: str) -> None:
    """Synthetic transport regression, motivated by the actual ARCC pair review."""
    inputs = make_inputs(case)
    preference = inputs.submission.preference.model_copy(
        update={
            "ordering": (),
            "rationale": "No supported preference while valuation conventions remain unresolved.",
            "confidence": "Insufficient Information",
            "limitation": "Matched price basis and precision do not support a ranking.",
        }
    )
    submission = inputs.submission.model_copy(update={"preference": preference})
    result = compute(dataclasses.replace(inputs, submission=submission))
    assert result.issues == ()
    assert result.report is not None
    ordering = next(
        fact for fact in result.report.facts if fact.table_id == "T3.4" and fact.field == "ordering"
    )
    assert ordering.text == "No ordering"
    assert any("Insufficient Information" in value for value in result.report.limitations)
    consumed = dict(cp3_catalogue(candidate(result, inputs, attempt=0))["T3.4.preference"].cells)
    assert consumed["ordering"] == "No ordering"
    assert consumed["confidence"] == "Insufficient Information"
    assert consumed["limitation"] == preference.limitation


@pytest.mark.parametrize(
    ("confidence", "limitation", "issue"),
    [
        ("Medium", "Basis unresolved.", "preference.ordering: term-loan is missing"),
        (
            "Insufficient Information",
            None,
            "preference: an Insufficient Information preference states its limitation",
        ),
    ],
)
def test_withheld_ranking_requires_explicit_insufficiency_and_limitation(
    confidence: str, limitation: str | None, issue: str
) -> None:
    inputs = make_inputs("positive")
    preference = inputs.submission.preference.model_copy(
        update={"ordering": (), "confidence": confidence, "limitation": limitation}
    )
    submission = inputs.submission.model_copy(update={"preference": preference})
    result = compute(dataclasses.replace(inputs, submission=submission))
    assert issue in result.issues
    assert result.report is None
    assert result.issues


# --- ruling S08-cp3-C09: an Insufficient Information preference has an empty ordering ----------

# Hand-written from the ruling: the refusal names both repairs the model can make.
INSUFFICIENT_ORDERING = (
    "preference.ordering: an Insufficient Information preference has an empty ordering; empty it, "
    "or cite observed or indicative market evidence and state a confidence other than "
    "Insufficient Information"
)
MISSING = "preference.ordering: term-loan is missing"


def _with_preference(case: str, ordering: tuple[str, ...], confidence: str) -> CP3Result:
    inputs = make_inputs(case)
    preference = inputs.submission.preference.model_copy(
        update={
            "ordering": ordering,
            "confidence": confidence,
            "limitation": "Evidence does not support a ranking.",
        }
    )
    submission = inputs.submission.model_copy(update={"preference": preference})
    return compute(dataclasses.replace(inputs, submission=submission))


@pytest.mark.parametrize("case", ["positive", "gap"])
@pytest.mark.parametrize(
    "ordering",
    [("term-loan",), ("term-loan", "term-loan"), ("other",), (" ",), ("",)],
    ids=["one-instrument", "repeated", "unknown", "whitespace", "empty-entry"],
)
def test_s08_c09_an_insufficient_preference_with_an_ordering_is_refused(
    case: str, ordering: tuple[str, ...]
) -> None:
    """Any non-empty ordering, even the trivial one-instrument one or a blank entry, is refused
    with the repairable issue; completeness ("is missing") is not asked of it. Before the ruling
    the one-instrument ordering composed (repro cr_c06: issues ())."""
    result = _with_preference(case, ordering, "Insufficient Information")
    assert result.report is None
    assert INSUFFICIENT_ORDERING in result.issues
    assert MISSING not in result.issues


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_s08_c09_an_insufficient_preference_with_no_ordering_composes(case: str) -> None:
    result = _with_preference(case, (), "Insufficient Information")
    assert result.issues == ()
    assert result.report is not None


@pytest.mark.parametrize("confidence", ["High", "Medium", "Low"])
def test_s08_c09_other_confidences_keep_the_ordering_rules(confidence: str) -> None:
    """Positive case (one instrument, observed and talk quotes): the full ordering raises no
    ordering issue (High is still capped: CP-2 is restricted); an empty one is "term-loan is
    missing"; neither gets the Insufficient Information refusal."""
    full = _with_preference("positive", ("term-loan",), confidence)
    empty = _with_preference("positive", (), confidence)
    assert not [i for i in full.issues if i.startswith("preference.ordering")]
    assert MISSING in empty.issues
    assert INSUFFICIENT_ORDERING not in full.issues + empty.issues
    assert (full.report is not None) == (confidence != "High")


# --- review fixes S08-cp3: a model-cited quote's `as_of` is a stated date, dated before the run ---


def _as_of_issues(as_of: str) -> tuple[str, ...]:
    literal = copy.deepcopy(SUBMISSIONS["positive"]["relative_value"])
    literal["market_evidence"][0]["as_of"] = as_of
    return compute(make_inputs("positive", literal)).issues


@pytest.mark.parametrize(
    "as_of",
    ("January 9, 2031", "the close", "March 1, 2019", "2026-01-09", "January 10, 2026"),
)
def test_s08_a06_an_as_of_the_quote_does_not_state_is_refused(as_of: str) -> None:
    """S08-cp3-A06/C02: the observed row's quote states January 9, 2026 only, so a later, earlier,
    reworded, ISO or non-date as_of is refused, and so is the page's own Published date
    (January 10, 2026): a quote that prints a date is dated by it."""
    assert _as_of_issues(as_of) == (
        f"market_evidence[0].as_of {as_of!r} is not a date its quote states (January 9, 2026)",
    )


def _talk_as_of_issues(as_of: str) -> tuple[str, ...]:
    literal = copy.deepcopy(SUBMISSIONS["positive"]["relative_value"])
    literal["market_evidence"][1]["as_of"] = as_of
    return compute(make_inputs("positive", literal)).issues


@pytest.mark.parametrize(
    "as_of", ("January 9, 2031", "the close", "2026-01-10", "January 11, 2026")
)
def test_s08_a06_an_undated_quote_is_dated_by_a_date_its_page_states(as_of: str) -> None:
    """The talk row's quote prints no date: its page states January 9 and 10, 2026 and December 31,
    2029 only, so any other as_of is refused."""
    assert _talk_as_of_issues(as_of) == (
        f"market_evidence[1].as_of {as_of!r} is not a date stated on its page",
    )


def test_s08_a06_the_page_date_is_accepted_for_an_undated_quote() -> None:
    """The positive talk row uses its page's Published date, which is not after the run as-of."""
    assert _talk_as_of_issues("January 10, 2026") == ()


def _shifted_inputs(monkeypatch: pytest.MonkeyPatch, as_of: str, literal: Any) -> CP3Inputs:
    """The positive inputs with the run as-of moved to `as_of` (every module follows the pack)."""
    original = make_pack

    def shifted(case: str) -> PreparedPack:
        pack = original(case)
        run = pack.run.model_copy(update={"as_of": date.fromisoformat(as_of)})
        return pack.model_copy(update={"run": run})

    monkeypatch.setitem(globals(), "make_pack", shifted)
    return make_inputs("positive", literal)


def test_s08_a06_a_quote_dated_after_the_run_as_of_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run as-of 2026-01-09: the talk row's January 10, 2026 is one day after it."""
    literal = SUBMISSIONS["positive"]["relative_value"]
    issues = compute(_shifted_inputs(monkeypatch, "2026-01-09", literal)).issues
    assert "market_evidence[1].as_of January 10, 2026 is after the run as-of 2026-01-09" in issues


def test_s08_a06_a_stale_quote_gets_the_line_and_caps_the_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run as-of 2026-03-01: January 9 -> March 1 is 22 + 28 + 1 = 51 days and January 10 is 50,
    both more than STALE_DAYS (30). Each row gets the stale line; High is capped."""
    literal = copy.deepcopy(SUBMISSIONS["positive"]["relative_value"])
    result = compute(_shifted_inputs(monkeypatch, "2026-03-01", literal))
    assert result.issues == ()
    assert result.report is not None
    stale = [x for x in result.report.limitations if x.startswith("Stale quote")]
    assert stale == [
        (
            "Stale quote: market page:1 quote dated January 9, 2026 is 51 days before the run "
            "as-of 2026-03-01 (limit 30)"
        ),
        (
            "Stale quote: market page:2 quote dated January 10, 2026 is 50 days before the run "
            "as-of 2026-03-01 (limit 30)"
        ),
    ]
    literal["preference"]["confidence"] = "High"
    issues = compute(_shifted_inputs(monkeypatch, "2026-03-01", literal)).issues
    capped = [x for x in issues if x.startswith("preference.confidence: capped below High")]
    assert len(capped) == 1
    assert capped[0].endswith("a market_evidence quote is more than 30 days old")


def test_review_s08_a06_a_newer_page_date_does_not_stand_for_an_older_quotes() -> None:
    """The sheet is published January 10, 2026 but the quotation is dated March 1, 2025: the row
    is dated by its quote, never by the Published date. March 1, 2025 to March 1, 2026 is 365 days
    and March 1 is 50 days after the run as-of (January 10), so the quote is 315 days old."""
    old = "Dealer quotation on January 9, 2026: bid 98.50 and offer 99.25"
    new = "Dealer quotation on March 1, 2025: bid 98.50 and offer 99.25"
    original = make_pack

    def older(case: str) -> PreparedPack:
        pack = original(case)
        sources = tuple(
            s.model_copy(
                update={
                    "spans": tuple(
                        Span(locator=x.locator, text=x.text.replace(old, new)) for x in s.spans
                    )
                }
            )
            if s.source_id == "market"
            else s
            for s in pack.sources
        )
        return pack.model_copy(update={"sources": sources})

    literal = json.loads(json.dumps(SUBMISSIONS["positive"]["relative_value"]).replace(old, new))
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(globals(), "make_pack", older)
        literal["market_evidence"][0]["as_of"] = "January 10, 2026"
        issues = compute(make_inputs("positive", literal)).issues
        assert issues == (
            (
                "market_evidence[0].as_of 'January 10, 2026' is not a date its quote states "
                "(March 1, 2025)"
            ),
        )
        literal["market_evidence"][0]["as_of"] = "March 1, 2025"
        result = compute(make_inputs("positive", literal))
    assert result.issues == ()
    assert result.report is not None
    assert [x for x in result.report.limitations if x.startswith("Stale quote")] == [
        (
            "Stale quote: market page:1 quote dated March 1, 2025 is 315 days before the run "
            "as-of 2026-01-10 (limit 30)"
        )
    ]


# --- S08-cp3-A08: an observed row's quote is read with its whole sentence -------------------------
def _talk_sub_span_as_observed(sub: str) -> CP3Inputs:
    """The positive literal with only its page:2 row, re-quoted as `sub` and called observed."""
    lit = copy.deepcopy(SUBMISSIONS["positive"]["relative_value"])
    row = lit["market_evidence"][1]
    row.update(kind="observed", limitation=None)
    row["quote"]["quote"] = sub
    lit["market_evidence"] = [row]
    for item in (*lit["instruments"], lit["preference"]):
        quotes = [q for q in item["basis"]["quotes"] if q["locator"] == "page:2"]
        for q in quotes:
            q["quote"] = sub
        item["basis"]["quotes"] = quotes
    return make_inputs("positive", lit)


def test_an_observed_sub_span_of_a_talk_sentence_is_refused() -> None:
    """page:2 reads "Dealers describe the indicative fair value of the Northbridge Term Loan as
    around 99.75. This is talk ...". Quoting only "the Northbridge Term Loan as around 99.75"
    held no marker, so it published as Observed; its sentence holds "indicative"."""
    result = compute(_talk_sub_span_as_observed("the Northbridge Term Loan as around 99.75"))
    assert result.issues == (
        'market_evidence[0]: an observed row quotes a sentence of indicative talk: "indicative"',
    )


def test_an_observed_quote_with_the_marker_keeps_the_quote_issue_once() -> None:
    whole = (
        "Dealers describe the indicative fair value of the Northbridge Term Loan as around 99.75."
    )
    result = compute(_talk_sub_span_as_observed(whole))
    assert result.issues == (
        'market_evidence[0]: an observed row quotes indicative talk: "indicative"',
    )


# --- S08-cp3-C03: a preference whose basis is talk only is capped and limited -----------------
def _accepted_cp2(inputs: CP3Inputs) -> CP3Inputs:
    bound = tuple(
        i.model_copy(update={"status": "accepted"}) if i.input_id == "CP-2" else i
        for i in inputs.bound
    )
    return dataclasses.replace(inputs, bound=bound, current=bound)


def _preference_on(locator: str, confidence: str) -> CP3Inputs:
    """CP-2 accepted (no upstream cap); the preference cites only the `locator` quote, while
    market_evidence still lists the page:1 observed and the page:2 indicative_talk rows."""
    inputs = _accepted_cp2(make_inputs("positive"))
    pref = inputs.submission.preference
    quotes = tuple(q for q in pref.basis.quotes if q.locator == locator)
    basis = pref.basis.model_copy(update={"quotes": quotes})
    pref = pref.model_copy(update={"basis": basis, "confidence": confidence})
    submission = inputs.submission.model_copy(update={"preference": pref})
    return dataclasses.replace(inputs, submission=submission)


def test_a_talk_only_preference_basis_is_capped_below_high() -> None:
    """Before the fix the cap read all market evidence ({observed, indicative_talk}), so this
    validated at High with no talk-only limitation."""
    assert compute(_preference_on("page:2", "High")).issues == (
        (
            "preference.confidence: capped below High because the preference's market basis is "
            "indicative talk only"
        ),
    )
    assert compute(_preference_on("page:1", "High")).issues == ()


def test_a_talk_only_preference_basis_states_its_limitation() -> None:
    result = compute(_preference_on("page:2", "Medium"))
    assert result.report is not None
    assert (
        "The preference's market basis is indicative talk only, not an observed market level"
        in result.report.limitations
    )
    observed = compute(_preference_on("page:1", "Medium")).report
    assert observed is not None
    assert all("indicative talk only" not in text for text in observed.limitations)


# --- confidence review of S08-cp3-A08 and C03 ----------------------------------------------------
def _sentences(page: str, quote: str) -> str:
    pack = NS(sources=[NS(source_id="market", spans=[NS(locator="page:1", text=page)])])
    return _sentences_of(NS(source_id="market", locator="page:1", quote=quote), pack).strip()  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("page", "quote", "expected"),
    [
        # a decimal point is not a boundary: the sentence runs to the "." before a space
        (
            "Bid 99.50 observed. Dealers see indicative value around 99.75 for the loan. Done.",
            "around 99.75 for",
            "Dealers see indicative value around 99.75 for the loan.",
        ),
        # the neighbouring sentences are not read
        (
            "Indicative IPT is 100. Bid 99.50 observed. Guidance is wide.",
            "Bid 99.50 observed",
            "Bid 99.50 observed.",
        ),
        # every occurrence of the quote is read with its own sentence
        (
            "Bid 99.50 is firm. Bid 99.50 is talk.",
            "Bid 99.50",
            "Bid 99.50 is firm.  Bid 99.50 is talk.",
        ),
        # a quote the page does not hold falls back to the quote
        ("Something else entirely.", "Bid 99.50", "Bid 99.50"),
    ],
)
def test_confidence_review_s08_a08_the_sentence_of_a_quote(
    page: str, quote: str, expected: str
) -> None:
    assert _sentences(page, quote) == expected


def test_confidence_review_s08_c03_a_basis_of_talk_and_observed_is_not_capped() -> None:
    """The preference cites both the observed page:1 quote and the talk page:2 quote: not talk
    only, so High is allowed (before and after the fix) and no talk-only limitation appears."""
    inputs = _accepted_cp2(make_inputs("positive"))
    pref = inputs.submission.preference
    locators = {q.locator for q in pref.basis.quotes}
    assert locators == {"page:1", "page:2"}  # the literal's own basis holds both
    pref = pref.model_copy(update={"confidence": "High"})
    inputs = dataclasses.replace(
        inputs, submission=inputs.submission.model_copy(update={"preference": pref})
    )
    result = compute(inputs)
    assert result.issues == ()
    assert result.report is not None
    assert all("indicative talk only" not in text for text in result.report.limitations)


def test_s08_c09_review_repair_paths_in_the_gap_case() -> None:
    """Gap case (no market evidence), hand-derived from the ruling and the evidence rule. The two
    repairs the issue offers do not loop: emptying the ordering composes (tested above); keeping
    the ordering and claiming Medium is refused for the missing market evidence only, never for
    the ordering. An Insufficient Information preference with an ordering and no limitation gets
    both issues, the ordering one once."""
    medium = _with_preference("gap", ("term-loan",), "Medium")
    assert medium.report is None
    assert (
        "preference.confidence: Insufficient Information without observed or indicative "
        "market evidence"
    ) in medium.issues
    assert INSUFFICIENT_ORDERING not in medium.issues
    assert not [i for i in medium.issues if i.startswith("preference.ordering")]
    inputs = make_inputs("gap")
    preference = inputs.submission.preference.model_copy(
        update={"ordering": ("term-loan",), "limitation": ""}
    )
    both = compute(
        dataclasses.replace(
            inputs, submission=inputs.submission.model_copy(update={"preference": preference})
        )
    )
    assert both.issues.count(INSUFFICIENT_ORDERING) == 1
    assert "preference: an Insufficient Information preference states its limitation" in both.issues
