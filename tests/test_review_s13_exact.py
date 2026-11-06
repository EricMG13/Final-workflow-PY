"""Review S13: the helpers CP-2D, CP-2E, CP-2G and CP-2H share through `owners.exact` keep the
behaviour (and the pinned wording) of the copies they replaced. Expected values are literals."""

import hashlib
from decimal import Decimal

import pytest

from deploy_vii.contracts import Fact, Input
from deploy_vii.live import submission
from deploy_workflow.owners import cp2d, cp2e, cp2g, cp2h, exact
from deploy_workflow.owners.period_basis import DEFAULT_BASIS


@pytest.mark.parametrize(
    ("value", "text"),
    [
        ("0", "0"),
        ("-0", "0"),
        ("-0.000", "0"),
        ("0E+5", "0"),
        ("1E+5", "100000"),
        ("1.0E+1", "10"),
        ("-1.50", "-1.5"),
        ("0.10", "0.1"),
        ("12345678901234567890123456.7890", "12345678901234567890123456.789"),
    ],
)
def test_exact_text_and_decimal(value: str, text: str) -> None:
    assert exact.exact_text(Decimal(value)) == text
    stored = exact.exact_decimal(Decimal(value))
    assert str(stored) == text and stored.as_tuple() == Decimal(text).as_tuple()


def test_cp2d_exact_amount_text_brackets_negatives() -> None:
    assert cp2d.exact_amount_text(Decimal("-2.50")) == "(2.5) US$ m"
    assert cp2d.exact_amount_text(Decimal("-0")) == "0 US$ m"
    assert cp2d.exact_amount_text(Decimal("1E+3"), "EUR m") == "1000 EUR m"


def test_old_names_still_resolve() -> None:
    assert cp2h.exact_text is exact.exact_text
    assert cp2h.stale_issues is exact.stale_issues
    assert cp2g.stale_issues is exact.stale_issues
    assert not hasattr(cp2h, "_with_rules") or cp2h._with_rules is submission._with_rules


def _input(input_id: str, sha: str, status: str = "accepted") -> Input:
    return Input.model_validate({"input_id": input_id, "sha256": sha * 64, "status": status})


def test_stale_issues_frame() -> None:
    bound = (_input("CP-1", "a"), _input("CP-0", "b"))
    current = (_input("CP-1", "c", "restricted"),)
    assert exact.stale_issues(bound=bound, current=current) == (
        f"Stale input CP-1: bound accepted {'a' * 12}, current restricted {'c' * 12}",
        f"Stale input CP-0: bound accepted {'b' * 12}, current absent",
    )
    assert exact.stale_issues(bound=bound, current=bound) == ()
    (line,) = exact.stale_issues(bound=bound, current="Required upstream " + "x" * 5000)
    assert line.startswith("Stale inputs: Required upstream x") and len(line) <= 600


def test_run_text_issues() -> None:
    assert exact.run_text_issues("summary.text", "A plain sentence.") == []
    (issue,) = exact.run_text_issues("summary.text", "Broken [ref")
    assert issue.startswith("summary.text: ")


def _t410(metric: str, n: int = 1) -> list[Fact]:
    return [
        Fact(
            fact_id=f"T4.10.{metric}.{k}",
            label=f"{DEFAULT_BASIS.ltm_column} · {metric}",
            table_id="T4.10",
            row_id=f"r{k}",
            field="value",
            text="x",
        )
        for k in range(n)
    ]


def test_select_t410_keeps_each_owners_refusal() -> None:
    label = f"{DEFAULT_BASIS.ltm_column} · revenue"
    with pytest.raises(ValueError) as g:
        cp2g.select_cp1(_t410("revenue", 2))
    assert str(g.value) == f"CP-1 needs exactly one T4.10 fact labelled {label}, found 2"
    with pytest.raises(ValueError) as h:
        cp2h.select_cp1([])
    first = cp2h.CP1_METRICS[0]
    assert str(h.value) == (
        f"CP-1 T4.10 needs exactly one fact labelled {DEFAULT_BASIS.ltm_column} · {first}"
    )
    picked = exact.select_t410(_t410("a") + _t410("b"), ("b", "a"), DEFAULT_BASIS, str.format)
    assert [f.fact_id for f in picked.values()] == ["T4.10.b.0", "T4.10.a.0"]


def test_compact_view() -> None:
    digest, body = exact.compact_view({"b": [1, "é"], "a": None})
    assert body == '{"b":[1,"é"],"a":null}'
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    with pytest.raises(ValueError):
        exact.compact_view({"x": float("nan")})


def test_cp2e_uses_the_shared_exact_form() -> None:
    assert cp2e._known(Decimal("-0.00")).amount == Decimal(0)
    assert str(cp2e._known(Decimal("2.500")).amount) == "2.5"
