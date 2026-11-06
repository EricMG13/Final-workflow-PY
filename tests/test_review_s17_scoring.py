"""S17 review regressions for the module scorer: currency and quantity family, inherited
dependencies inside one module and down a chain of modules."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from deploy_vii.contracts import Citation, Fact, Module
from deploy_workflow.model_testing.cases import GoldenCase
from deploy_workflow.model_testing.mapping import Locator, Mapping, MappingEntry
from deploy_workflow.model_testing.scoring import ModuleScore, score_module, upstream_ids

_CITE = (Citation(source_id="s", source_sha256="b" * 64, locator="p1", quote="q"),)


def _golden(
    fid: str, module: str, value: str, unit: str | None, scale: str | None
) -> dict[str, Any]:
    return {
        "fact_id": fid,
        "module": module,
        "topic": "t",
        "subject": fid,
        "field": "f",
        "period_end": "2025-06-30",
        "status": "known",
        "value": value,
        "value_type": "decimal",
        "unit": unit,
        "scale": scale,
        "evidence": [],
        "derivation": None,
        "gap_reason": None,
    }


def _case(*facts: dict[str, Any]) -> GoldenCase:
    return GoldenCase(
        case_id="synthetic",
        pathway="credit_snapshot",
        case_dir=Path("."),
        context_path=Path("context.json"),
        facts=MappingProxyType({f["fact_id"]: f for f in facts}),
        out_of_plan=MappingProxyType({}),
        financial_gold_path=Path("g.json"),
        financial_gold_sha256="0" * 64,
    )


def _entry(fid: str, module: str, row: str, depends_on: tuple[str, ...] = ()) -> MappingEntry:
    loc = Locator(table_id="t", row_id=row, field="f", period="2025-06-30")
    return MappingEntry(fact_id=fid, module=module, locator=loc, depends_on=depends_on)


def _mapping(case: GoldenCase, entries: list[MappingEntry], modules: tuple[str, ...]) -> Mapping:
    return Mapping(
        schema_version="golden-mapping/1",
        case_id=case.case_id,
        preparer="alice",
        reviewer="bob",
        module_commits={m: "a" * 40 for m in modules},
        entries=tuple(entries),
        unmapped=(),
    )


def _fact(row: str, amount: str, **kw: Any) -> Fact:
    base: dict[str, Any] = {
        "fact_id": f"f-{row}",
        "label": "x",
        "table_id": "t",
        "row_id": row,
        "field": "f",
        "period": "2025-06-30",
        "amount": Decimal(amount),
        "citations": _CITE,
    }
    base.update(kw)
    return Fact(**base)


def _module(module_id: str, facts: list[Fact]) -> Module:
    return Module(
        run_id="r", issuer_id="i", as_of=date(2025, 1, 1), module_id=module_id, facts=tuple(facts)
    )


def _score_one(golden: dict[str, Any], fact: Fact) -> tuple[str, str | None]:
    case = _case(golden)
    entry = _entry(golden["fact_id"], "CP-1", fact.row_id)
    mapping = _mapping(case, [entry], ("CP-1",))
    score = score_module(_module("CP-1", [fact]), "CP-1", "accepted", case, mapping, frozenset())
    return score.facts[0].outcome, score.facts[0].observed


USD_100M = _golden("CP-1.fin.rev", "CP-1", "100", "USD", "millions")
USD_5_25 = _golden("CP-1.fin.eps", "CP-1", "5.25", "USD", "units")


# ---- currency and quantity family (adv S17 scoring.py:100, high) -------------------------


def test_matching_currency_amount_still_matches() -> None:
    fact = _fact("r1", "100", unit="MILLIONS", scale=Decimal(1000000), currency="USD")
    assert _score_one(USD_100M, fact) == ("match", "100000000")
    # a currency code as the unit names the currency itself
    coded = _fact("r1", "100000000", unit="USD")
    assert _score_one(USD_100M, coded)[0] == "match"


def test_wrong_currency_is_a_mismatch() -> None:
    fact = _fact("r1", "100", unit="MILLIONS", scale=Decimal(1000000), currency="EUR")
    assert _score_one(USD_100M, fact) == ("mismatch", "currency EUR is not USD")
    clash = _fact("r1", "100000000", unit="USD", currency="EUR")
    assert _score_one(USD_100M, clash) == ("mismatch", "currency EUR/USD is not USD")
    euro_unit = _fact("r1", "100000000", unit="EUR")
    assert _score_one(USD_100M, euro_unit) == ("mismatch", "currency EUR is not USD")


def test_amount_without_a_currency_is_a_mismatch() -> None:
    fact = _fact("r1", "100", unit="MILLIONS", scale=Decimal(1000000))
    assert _score_one(USD_100M, fact) == ("mismatch", "currency none is not USD")


@pytest.mark.parametrize("unit", ["MULTIPLE", "x", "records", "months"])
def test_other_quantity_family_is_a_mismatch(unit: str) -> None:
    fact = _fact("r1", "5.25", unit=unit)
    assert _score_one(USD_5_25, fact) == ("mismatch", f"unit {unit} is not a USD amount")


def test_unitless_decimal_golden_still_takes_a_multiple() -> None:
    ratio = _golden("CP-1.lev", "CP-1", "5.25", None, None)
    assert _score_one(ratio, _fact("r1", "5.25", unit="MULTIPLE"))[0] == "match"


def test_statement_currency_unit_is_an_amount() -> None:
    # unit "currency" (statement registers, written at scale 1e6) is a currency amount
    fact = _fact("r1", "100", unit="currency", scale=Decimal(1000000), currency="USD")
    assert _score_one(USD_100M, fact)[0] == "match"


# ---- inherited (cr S17 scoring.py:335 and pathway.py:143) ---------------------------------


def _chain_case() -> GoldenCase:
    return _case(
        _golden("A", "CP-1", "10", "USD", "units"),
        _golden("B", "CP-1", "20", "USD", "units"),
        _golden("C", "CP-1", "30", "USD", "units"),
    )


def test_same_module_dependency_scores_inherited() -> None:
    case = _chain_case()
    # C depends on B, B on A; the entries are listed dependents first on purpose
    entries = [
        _entry("C", "CP-1", "rc", ("B",)),
        _entry("B", "CP-1", "rb", ("A",)),
        _entry("A", "CP-1", "ra"),
    ]
    mapping = _mapping(case, entries, ("CP-1",))
    facts = [
        _fact("ra", "11", unit="USD"),  # wrong at the root
        _fact("rb", "21", unit="USD"),  # wrong because A is
        _fact("rc", "31", unit="USD"),  # wrong because B is
    ]
    score = score_module(_module("CP-1", facts), "CP-1", "accepted", case, mapping, frozenset())
    outcomes = {f.fact_id: f.outcome for f in score.facts}
    assert outcomes == {"A": "mismatch", "B": "inherited", "C": "inherited"}
    assert [f.fact_id for f in score.facts] == ["C", "B", "A"]  # mapping order kept
    assert score.passed is False


def test_same_module_dependency_on_a_match_stays_mismatch() -> None:
    case = _chain_case()
    entries = [_entry("A", "CP-1", "ra"), _entry("B", "CP-1", "rb", ("A",))]
    mapping = _mapping(case, entries, ("CP-1",))
    facts = [_fact("ra", "10", unit="USD"), _fact("rb", "21", unit="USD")]
    score = score_module(_module("CP-1", facts), "CP-1", "accepted", case, mapping, frozenset())
    assert [f.outcome for f in score.facts] == ["match", "mismatch"]


def test_unit_problem_is_never_inherited() -> None:
    case = _chain_case()
    entries = [_entry("A", "CP-1", "ra"), _entry("B", "CP-1", "rb", ("A",))]
    mapping = _mapping(case, entries, ("CP-1",))
    facts = [_fact("ra", "11", unit="USD"), _fact("rb", "20", unit="EUR")]
    score = score_module(_module("CP-1", facts), "CP-1", "accepted", case, mapping, frozenset())
    assert [(f.outcome, f.observed) for f in score.facts] == [
        ("mismatch", "11"),
        ("mismatch", "currency EUR is not USD"),
    ]


def test_inherited_passes_down_a_chain_of_modules() -> None:
    case = _case(
        _golden("A", "CP-1", "10", "USD", "units"),
        _golden("B", "CP-2", "20", "USD", "units"),
        _golden("C", "CP-5", "30", "USD", "units"),
    )
    entries = [
        _entry("A", "CP-1", "ra"),
        _entry("B", "CP-2", "rb", ("A",)),
        _entry("C", "CP-5", "rc", ("B",)),
    ]
    mapping = _mapping(case, entries, ("CP-1", "CP-2", "CP-5"))
    results = {
        "CP-1": _module("CP-1", [_fact("ra", "11", unit="USD")]),
        "CP-2": _module("CP-2", [_fact("rb", "21", unit="USD")]),
        "CP-5": _module("CP-5", [_fact("rc", "31", unit="USD")]),
    }
    upstream: set[str] = set()
    outcomes: dict[str, str] = {}
    for module_id in ("CP-1", "CP-2", "CP-5"):
        score: ModuleScore = score_module(
            results[module_id], module_id, "accepted", case, mapping, frozenset(upstream)
        )
        upstream |= upstream_ids(score)
        outcomes.update({f.fact_id: f.outcome for f in score.facts})
    assert outcomes == {"A": "mismatch", "B": "inherited", "C": "inherited"}
