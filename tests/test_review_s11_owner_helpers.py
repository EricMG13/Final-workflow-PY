"""S11 review: owner helper refusals name the problem instead of escaping as KeyError, and the
legal-documents gap rule matches only the whole token (synthetic inputs)."""

from types import SimpleNamespace

import pytest

from deploy_vii.contracts import Fact
from deploy_workflow.owners.cp0_attachments import LEGAL_EXECUTED_MISSING, _legal_issue
from deploy_workflow.owners.period_basis import PeriodRefused, _row_basis


def row(**texts: str) -> dict[str, Fact]:
    return {
        name: Fact(
            fact_id=f"q4-{name}", label=name, table_id="T4.14", row_id="q4", field=name, text=text
        )
        for name, text in texts.items()
    }


def test_period_row_without_fiscal_year_is_refused_by_name():
    with pytest.raises(PeriodRefused, match="CP-1 T4.14 period q4 has no fiscal_year"):
        _row_basis("USD", "2025", "q4", row(currency="USD", unit="MILLIONS"))


def test_period_row_with_its_fiscal_year_still_reads():
    _row_basis("USD", "2025", "q4", row(currency="USD", unit="MILLIONS", fiscal_year="FY2025"))


@pytest.mark.parametrize(
    "gap,issues",
    [
        ("see legal_documents_v2 folder later", (LEGAL_EXECUTED_MISSING,)),
        ("xlegal_documents pending", (LEGAL_EXECUTED_MISSING,)),
        ("legal_documents: executed indenture not in the pack", ()),
        ("Missing (legal_documents).", ()),
    ],
)
def test_legal_gap_names_legal_documents_only_as_a_whole_token(gap, issues):
    review = SimpleNamespace(sources=())
    assert _legal_issue("executed", review, frozenset(), (gap,)) == issues


def test_with_rules_appends_rule_issues_once_after_validator_issues():
    from deploy_vii.execution import StepValidation
    from deploy_workflow.owners.blank import with_rules

    validate = with_rules(
        lambda pack, attempt: StepValidation(issues=("a", "b")), lambda raw: ("b", "c"), "{}"
    )
    assert validate(None, None).issues == ("a", "b", "c")
    clean = with_rules(lambda pack, attempt: StepValidation(output="x"), lambda raw: (), "{}")
    assert (clean(None, None).output, clean(None, None).issues) == ("x", ())


def test_parse_submission_reads_only_a_bounded_object():
    from pydantic import BaseModel

    from deploy_workflow.owners.blank import NOT_BOUNDED, parse_submission

    class Shape(BaseModel):
        amount: str

    assert parse_submission(Shape, '{"amount": "1.50"}') == (Shape(amount="1.50"), ())
    assert parse_submission(Shape, "[1]") == (None, ("(root): Input should be an object",))
    parsed, issues = parse_submission(Shape, '{"other": 1}')
    assert parsed is None and issues and all("amount" in issue for issue in issues)

    class Loose(BaseModel):
        amount: object

    # Pydantic would read NaN; the bounded reader refuses it first.
    assert parse_submission(Loose, '{"amount": NaN}') == (None, (NOT_BOUNDED,))
