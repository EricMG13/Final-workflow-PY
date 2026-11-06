"""Review S12 (CP-1D): derived facts inherit their inputs' citations, and the view reports a CP-1
head without the seven operands as the validator does instead of raising."""

from decimal import Decimal

import test_connect_cp1d as connect

from deploy_vii.contracts import Citation, Module
from deploy_vii.execution import Attempt, ExecutionSnapshot, candidate_issues, text_sha256
from deploy_workflow.owners import cp1d

FINANCIAL_SHA = "82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429"
ITEM_LINE = "Procurement programme savings  Saving  Unrealised  3.00"
BASIS_LINE = "Signed supplier contracts cover an annualised saving of 1.80."
ADJUSTED = "Adjusted EBITDA  7.5  7.5  7.5  7.5  30.0"
REPORTED = "Reported EBITDA  7.5  7.5  7.5  7.5  30.0"
CFO = "Operating cash flow  4.75  4.75  4.75  4.75  19.00"
DEBT = "Total debt  45  46.25  47.50  48.75  50.00  50.00"
CASH = "Cash and cash equivalents  15  16.25  17.50  18.75  20.00  20.00"

# The quotes a CP-1 head cites for each LTM figure: lines of the pack's `financial` source.
CP1_QUOTES = {
    "adjusted_ebitda_ltm": (("page:2", ADJUSTED),),
    "ebitda_ltm": (("page:2", REPORTED),),
    "cfo_ltm": (("page:3", CFO),),
    "total_debt_ltm": (("page:4", DEBT),),
    "net_debt_ltm": (("page:4", DEBT), ("page:4", CASH)),
    "total_leverage_adjusted": (("page:4", DEBT), ("page:2", ADJUSTED)),
    "net_leverage_adjusted": (("page:4", DEBT), ("page:2", ADJUSTED)),
}


def _financial(locator: str, quote: str) -> Citation:
    return Citation(
        source_id="financial", source_sha256=FINANCIAL_SHA, locator=locator, quote=quote
    )


def _cited_cp1() -> Module:
    """The connect suite's CP-1 head with each selected T4.10 fact citing the financial lines."""
    cp1 = connect._cp1_module()
    facts = tuple(
        f.model_copy(update={"citations": tuple(_financial(*q) for q in CP1_QUOTES[f.row_id])})
        if f.table_id == "T4.10" and f.period == cp1d._CP1_PERIOD
        else f
        for f in cp1.facts
    )
    return cp1.model_copy(update={"facts": facts})


def _quotes(citations: tuple[Citation, ...]) -> list[tuple[str, str, str]]:
    return [(c.source_id, c.locator, c.quote) for c in citations]


def test_calculated_facts_cite_their_inputs_per_page() -> None:
    cp1 = _cited_cp1()
    upstream = connect._upstream(cp1)
    report = cp1d.earnings_quality(
        pack=connect._pack("positive"),
        submission=connect._submission("positive", cp1),
        upstream=upstream,
    )
    by_id = {f.fact_id: f for f in report.facts}
    want = {
        # the accepted share stands on the cited basis
        "T1D.2.a01.accepted": [("bridge", "page:2", BASIS_LINE)],
        # proposed minus accepted: the item line, then the basis line (one per page)
        "T1D.2.a01.unsupported": [
            ("bridge", "page:1", ITEM_LINE),
            ("bridge", "page:2", BASIS_LINE),
        ],
        # CP-1 adjusted minus reported EBITDA: both on financial page:2, the first quote kept
        "T1D.1.stmt.claimed": [("financial", "page:2", ADJUSTED)],
        # the sum of the bridge rows (not the statement row): the first row's line on page:1
        "T1D.3.claimed.value": [("bridge", "page:1", ITEM_LINE)],
        # statement adjusted EBITDA plus the proposed add-backs, transitively
        "T1D.3.mgmt.value": [("financial", "page:2", ADJUSTED), ("bridge", "page:1", ITEM_LINE)],
        "T1D.3.supported.value": [
            ("financial", "page:2", ADJUSTED),
            ("bridge", "page:2", BASIS_LINE),
        ],
    }
    for fact_id, citations in want.items():
        assert by_id[fact_id].value_class == "calculated", fact_id
        assert _quotes(by_id[fact_id].citations) == citations, fact_id
    # Sourced facts keep their own field's citation.
    assert _quotes(by_id["T1D.1.a01.claimed"].citations) == [("bridge", "page:1", ITEM_LINE)]
    # The settled head over these citations passes the product's candidate checks (citations
    # resolve against the pack).
    candidate = cp1d.cp1d_module(report, inputs=upstream.bound, attempt=0)
    payload = candidate.model_dump_json()
    pack = connect._pack("positive")
    attempt = Attempt(
        ticket_id="t1",
        module_id="CP-1D",
        inputs=upstream.bound,
        number=0,
        payload_sha256=text_sha256(payload),
    )
    snapshot = ExecutionSnapshot(run=pack.run, pack_sha256=pack.content_hash(), attempts=(attempt,))
    assert candidate_issues(snapshot, attempt, candidate, pack=pack) == ()


def test_compute_cells_are_unchanged_by_lineage() -> None:
    """The oracle's cells (`compute`) carry no inherited citations; lineage is the product facts'."""
    cp1 = _cited_cp1()
    inputs, _ = cp1d._inputs(
        connect._pack("positive"), connect._submission("positive", cp1), connect._upstream(cp1)
    )
    cells = {c.fact_id: c for c in cp1d.compute(inputs).facts}
    assert cells["T1D.3.mgmt.value"].citations == ()
    assert cells["T1D.3.mgmt.value"].amount == Decimal(36)


def _without_cfo() -> Module:
    cp1 = connect._cp1_module()
    kept = tuple(
        f for f in cp1.facts if not (f.row_id == "cfo_ltm" and f.period == cp1d._CP1_PERIOD)
    )
    return cp1.model_copy(update={"facts": kept})


def test_view_reports_missing_cp1_operand_like_the_validator() -> None:
    cp1 = _without_cfo()
    upstream = connect._upstream(cp1)
    pack = connect._pack("positive")
    issue = "CP-1 operands unavailable: CP-1 T4.10 cfo_adjusted: 0 facts, expected exactly one"
    assert cp1d.validate_earnings_quality(
        pack=pack, submission=connect._submission("positive"), upstream=upstream
    ) == (issue,)
    block = cp1d.context_block(pack=pack, upstream=upstream)
    assert block["context_issue"] == issue
    assert block["cp1_facts"] == []
    bridge = block["bridge"]
    assert isinstance(bridge, dict) and bridge["state"] == "present"
