"""S12-C02: exclude_unrealised leaves out only add-backs CP-1 itself gave an unrealised row."""

from test_cash_scope import book, cite, observation

from deploy_vii.financial_adapter import _addbacks
from deploy_vii.financial_contracts import AddbackObservation, Disclosure
from deploy_vii.model.registers import Cp1Registers
from deploy_vii.model.statements import excluded_addbacks


def _addback(addback_id: str, status: str, amount: int) -> AddbackObservation:
    return AddbackObservation(
        addback_id=addback_id,
        addback_label=addback_id,
        classification="RESTRUCTURING",
        realization_status=status,  # type: ignore[arg-type]
        display_priority=1,
        period_id="fy-2025",
        value=observation(f"ab-{addback_id}", amount, cite(f"{addback_id} {amount}")),
        source_definition="x",
        classification_citations=(cite(f"{addback_id} {amount}"),),
    )


def _registers(*addbacks: AddbackObservation) -> Cp1Registers:
    base = book()
    complete = Disclosure(status="complete", explanation="bridge", citations=(cite("bridge"),))
    rows = _addbacks(base.model_copy(update={"addbacks": addbacks, "addback_disclosure": complete}))
    return Cp1Registers((), (), rows, (), (), (), (), "USD", "MILLIONS")


def test_a_realized_addback_is_kept_where_the_adapter_wrote_gap_rows() -> None:
    # By hand: "restr" is REALIZED (12) for fy-2025 only; the book has other periods, where the
    # adapter writes null NOT_STATED gap rows. Nothing CP-1 said is unrealised: none excluded.
    regs = _registers(_addback("restr", "REALIZED", 12))
    assert {r.realization_status for r in regs.addbacks} == {"REALIZED", "NOT_STATED"}
    assert excluded_addbacks(regs, True) == frozenset()


def test_cp1s_own_unrealized_and_not_stated_rows_still_exclude() -> None:
    # By hand: "pf" is UNREALIZED and "ns" NOT_STATED by CP-1's own rows, "ok" is REALIZED.
    regs = _registers(
        _addback("pf", "UNREALIZED", 5),
        _addback("ns", "NOT_STATED", 3),
        _addback("ok", "REALIZED", 1),
    )
    assert excluded_addbacks(regs, True) == {"pf", "ns"}
    assert excluded_addbacks(regs, False) == frozenset()
