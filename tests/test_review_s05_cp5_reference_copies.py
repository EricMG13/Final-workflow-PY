"""S05 review: CP-4's T4F.2 table holds verbatim copies of CP-1 facts under the CP-1 fact id,
like every module's `cp1_references` table, so CP-5 compares a copy's value, unit, currency
and period with its source but never its placement (methods/cp5.md, task 8.4b ruling 1)."""

from datetime import date
from decimal import Decimal

from deploy_vii.contracts import Fact, Module
from deploy_vii.cp5_integrity import figure_identity, identity_groups

_SOURCE = Fact(
    fact_id="T4.10.net_leverage.fy2024",
    label="Net leverage",
    table_id="T4.10",
    row_id="net_leverage",
    field="fy2024",
    amount=Decimal("3.2"),
    unit="MULTIPLE",
    period="FY2024",
    calculation_id="calc-net-leverage",
)


def _cp4_copy(**changes: object) -> Fact:
    """What CP-4 composes for a referenced CP-1 figure: table T4F.2, row ref01, field value."""
    return _SOURCE.model_copy(
        update={"table_id": "T4F.2", "row_id": "ref01", "field": "value", **changes}
    )


def _heads(copy: Fact) -> list[Module]:
    return [
        Module(
            module_id="CP-1", facts=(_SOURCE,), run_id="r", issuer_id="i", as_of=date(2025, 1, 1)
        ),
        Module(module_id="CP-4", facts=(copy,), run_id="r", issuer_id="i", as_of=date(2025, 1, 1)),
    ]


def test_a_faithful_cp4_copy_is_no_identity_finding() -> None:
    heads = _heads(_cp4_copy())
    assert figure_identity(heads) == ()
    assert [group.differing for group in identity_groups(heads)] == [()]


def test_a_cp4_copy_with_another_value_is_still_a_finding() -> None:
    heads = _heads(_cp4_copy(amount=Decimal("3.3")))
    assert [group.differing for group in identity_groups(heads)] == [("value",)]
    assert len(figure_identity(heads)) == 1


def test_cp4_copies_are_not_pooled_by_coordinate() -> None:
    other = Fact(
        fact_id="T4.10.other.fy2024",
        label="Other",
        table_id="T4F.2",
        row_id="ref01",
        field="value",
        amount=Decimal(9),
        unit="MULTIPLE",
        period="FY2024",
        calculation_id="calc-other",
    )
    heads = [
        Module(
            module_id="CP-4",
            facts=(_cp4_copy(),),
            run_id="r",
            issuer_id="i",
            as_of=date(2025, 1, 1),
        ),
        Module(module_id="CP-6", facts=(other,), run_id="r", issuer_id="i", as_of=date(2025, 1, 1)),
    ]
    assert identity_groups(heads) == ()
