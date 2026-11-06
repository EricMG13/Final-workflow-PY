"""Review S12 (CP-1C): the user multiple is stored as supplied, the single-value statistics row
holds the value the CP-4C limit refuses, context values are cited by their own text, a peers
source that is not ready does not conflict with the CP-DR pack, and the High refusal names the
pack's provenance."""

import copy
import json
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
import test_cp1c_valuation_context as valuation
import test_method_cp1c as stage1
import test_owner_cpdr_peers as cpdr

from deploy_vii.contracts import Source
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.context import load_context
from deploy_workflow.owners import cp1c

LIMIT_LOW = (
    "the selected multiple 0.00 is below the 0.01 limit of the CP-4C field; no multiple is selected"
)
LIMIT_HIGH = (
    "the selected multiple 100.00 is above the 99.99 limit of the CP-4C field; "
    "no multiple is selected"
)


def _facts(name: str, edit: Any) -> dict[str, Any]:
    result = valuation.derived_result(name, edit)
    return {fact_id: item.fact for fact_id, item in valuation.by_id(result).items()}


def _user_value(value: str) -> Any:
    return lambda doc: doc["valuation"]["user_multiple"].__setitem__("value", value)


def test_user_multiple_is_stored_as_supplied_and_the_selection_rounds() -> None:
    facts = _facts("user-multiple", _user_value("7.255"))
    for field in ("min", "median", "max"):
        cell = facts[f"T1C.10.user_multiple.{field}"]
        assert (cell.status, cell.amount, cell.value_class) == ("known", Decimal("7.255"), "source")
        assert [c.quote for c in cell.citations] == ['"value": "7.255",']
    selected = facts["T1C.11.selection.selected_multiple"]
    assert (selected.amount, selected.value_class) == (Decimal("7.26"), "calculated")
    assert selected.formula == "user-supplied multiple, rounded half-even to 2 dp"
    assert facts["T1C.11.selection.implied_ev"].amount == Decimal("217.80")


def test_user_multiple_with_two_places_stays_the_source() -> None:
    selected = _facts("user-multiple", _user_value("7.25"))["T1C.11.selection.selected_multiple"]
    assert (selected.amount, selected.value_class) == (Decimal("7.25"), "source")
    assert selected.formula == "user-supplied multiple"


def test_single_value_row_holds_a_user_multiple_the_limit_refuses() -> None:
    facts = _facts("user-multiple", _user_value("0.004"))
    assert facts["T1C.10.user_multiple.n_admitted"].amount == Decimal(1)
    median = facts["T1C.10.user_multiple.median"]
    assert (median.status, median.amount, median.limitation) == ("known", Decimal("0.004"), None)
    selected = facts["T1C.11.selection.selected_multiple"]
    assert (selected.status, selected.amount, selected.limitation) == ("missing", None, LIMIT_LOW)


def test_single_value_row_holds_an_issuer_multiple_the_limit_refuses() -> None:
    def edit(doc: dict[str, Any]) -> None:
        doc["valuation"]["issuer_market"].update({"market_cap_m": "3000", "net_debt_m": "0"})

    facts = _facts("issuer-trading", edit)
    assert facts["T1C.10.issuer_trading.n_admitted"].amount == Decimal(1)
    median = facts["T1C.10.issuer_trading.median"]
    assert (median.status, median.amount, median.value_class) == (
        "known",
        Decimal(100),
        "calculated",
    )
    selected = facts["T1C.11.selection.selected_multiple"]
    assert (selected.status, selected.limitation) == ("missing", LIMIT_HIGH)


def test_issuer_single_value_uses_market_cap_plus_net_debt() -> None:
    median = _facts("issuer-trading", lambda doc: None)["T1C.10.issuer_trading.median"]
    assert median.amount == Decimal(9)  # (200 + 70) / 30


def _compact_source() -> tuple[bytes, Source]:
    document = json.loads(valuation.context_bytes("auto-public"))
    raw = (json.dumps(document, separators=(",", ":")) + "\n").encode()
    return raw, valuation.context_source("auto-public", raw)


def test_compact_context_cites_each_figure_by_its_own_text() -> None:
    raw, source = _compact_source()
    cite = cp1c._line_citer(source)
    (ev,) = cite(("valuation", "peers", 0, "ev_m"))
    (ebitda,) = cite(("valuation", "peers", 1, "ebitda_m"))
    assert ev.locator == ebitda.locator == "line:1"
    assert ev.quote.startswith('{"name":"Synthetic Peer A (invented)"')
    assert ev.quote.endswith('"ev_m":"540"')
    assert ebitda.quote.startswith('{"name":"Synthetic Peer B (invented)"')
    assert ebitda.quote.endswith('"ebitda_m":"55"')
    # The compact file still composes, and no two figures share one whole-line quote.
    inputs = replace(
        stage1.inputs(valuation.base_case("auto-public")),
        context=load_context(raw),
        context_source=source,
        cp1_ebitda=valuation.cp1_ebitda(),
    )
    cited = [
        c.quote
        for item in cp1c.compute(inputs).facts
        if item.fact.table_id == "T1C.9" and item.fact.field in ("ev", "ebitda")
        for c in item.fact.citations
    ]
    assert cited and len(set(cited)) == len(cited)
    assert all(len(q) < len(raw) // 2 for q in cited)


def test_pretty_context_keeps_the_line_as_written() -> None:
    cite = cp1c._line_citer(valuation.context_source("auto-public"))
    assert cite(("valuation", "peers", 0, "ev_m"))[0].quote == '"ev_m": "540",'


def test_a_figure_that_is_not_unique_on_its_line_is_not_cited() -> None:
    raw = b'{"a": [{"x": "1"}, {"x": "1"}]}\n'
    source = prepare_source(
        SourceRequest(source_id="context", path="context.json", media_type="text/plain"), raw
    )
    with pytest.raises(ValueError, match="no citable value"):
        cp1c._line_citer(source)(("a", 0, "x"))


@pytest.mark.parametrize("status", ["missing", "unreadable"])
def test_peers_source_that_is_not_ready_is_no_conflict(status: str) -> None:
    base = cpdr._peers_pack()
    held = Source(
        source_id="peers",
        name="peers.txt",
        media_type="text/plain",
        status=status,
        extraction_status="blocked",
        limitation="Requested file is absent",
    )
    pack = PreparedPack(run=base.run, sources=(*base.sources, held))
    upstream = cpdr._upstream(cpdr._head_with_pack())
    assert (
        cp1c.validate_peer_benchmark(pack=pack, submission=cpdr._submission(), upstream=upstream)
        == ()
    )
    assert "context_issue" not in cp1c.context_block(pack=pack, upstream=upstream)


def test_high_confidence_refusal_names_the_pack_provenance() -> None:
    body = copy.deepcopy(cpdr.SUBS["cp1c_peers"])
    body["overall"]["confidence"] = "High"
    issues = cp1c.validate_peer_benchmark(
        pack=cpdr._peers_pack(),
        submission=cpdr._submission(body),
        upstream=cpdr._upstream(cpdr._head_with_pack()),
    )
    assert issues == (
        "Confidence cannot be High: the peer figures are read from supplied evidence and unaudited",
    )
