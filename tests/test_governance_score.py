"""T2D.8: a High-quality creditor-adverse documented action sets the level High at any count.

r14 CP-2C: no composite unless at least four dimensions are scored, "unless one clearly High-risk
documented action". The action is a floor: adding favourable (Supportive) rows must never lower
the level from High. Expected values follow that rule by hand, not from the code under test.
"""

from deploy_vii.business_context import DIMENSIONS, GovernanceItem, governance_sponsor_score


def _row(direction: str, dimension: str | None, quality: str, kind: str) -> GovernanceItem:
    flag = kind == "behaviour_flag"
    return GovernanceItem.model_validate(
        {
            "kind": kind,
            "topic": "Documented action",
            "documented_fact": "Source fact",
            "direction": direction,
            "behaviour_type": "dividend recap" if flag else None,
            "amount_funding_source": "Debt-funded" if flag else None,
            "legal_capacity_link": "Permitted by the RP basket" if flag else None,
            "dimension": dimension,
            "risk_mechanic": "Cash leaves the issuer",
            "credit_implication": "Reduced buffer",
            "evidence_quality": quality,
            "category": "Documentary Fact",
            "citations": (),
            "limitation": None,
        }
    )


def _supportive(count: int) -> list[GovernanceItem]:
    return [_row("Supportive", d, "Medium", "governance_topic") for d in DIMENSIONS[:count]]


RECAP = _row("Extraction-Oriented", None, "High", "behaviour_flag")


def test_unlabelled_high_action_keeps_high_with_four_supportive_dimensions() -> None:
    # 3 supportive dimensions: fewer than four scored -> Not Scorable, override sets High.
    three = governance_sponsor_score([RECAP, *_supportive(3)])
    assert (three.composite, three.risk_level, three.high_risk_action) == (
        "Not Scorable",
        "High",
        True,
    )
    # A 4th supportive dimension is favourable evidence: the level stays High (composite 5),
    # it must not fall to 1 Low.
    four = governance_sponsor_score([RECAP, *_supportive(4)])
    assert (four.composite, four.risk_level, four.high_risk_action) == ("5", "High", True)


def test_labelled_high_action_beside_support_keeps_high() -> None:
    # The recap shares "Leverage tolerance" with a Supportive row, so that dimension alone is 3
    # (support and extraction coexist); the documented action still floors the composite at 5.
    labelled = _row("Extraction-Oriented", DIMENSIONS[0], "High", "behaviour_flag")
    score = governance_sponsor_score([labelled, *_supportive(4)])
    assert score.dimensions[0].score == "3"
    assert (score.composite, score.risk_level) == ("5", "High")


def test_medium_quality_adverse_row_is_not_an_override() -> None:
    # Medium evidence is not the r14 override: four supportive dimensions score 1 (Low), and
    # the unlabelled Medium row informs no dimension.
    medium = _row("Extraction-Oriented", None, "Medium", "behaviour_flag")
    score = governance_sponsor_score([medium, *_supportive(4)])
    assert (score.composite, score.risk_level, score.high_risk_action) == ("1", "Low", False)


def test_floor_holds_at_five_scored_dimensions_and_for_creditor_adverse() -> None:
    adverse = _row("Creditor-Adverse", None, "High", "behaviour_flag")
    assert len(DIMENSIONS) >= 5
    score = governance_sponsor_score([adverse, *_supportive(5)])
    assert (score.composite, score.risk_level, score.scored) == ("5", "High", 5)


def test_a_high_quality_adverse_row_that_is_not_evidenced_is_no_override() -> None:
    # category "Insufficient Information" makes the row not `evidenced`: no documented action.
    row = _row("Extraction-Oriented", None, "High", "behaviour_flag").model_copy(
        update={"category": "Insufficient Information"}
    )
    score = governance_sponsor_score([row, *_supportive(4)])
    assert (score.composite, score.risk_level, score.high_risk_action) == ("1", "Low", False)


def test_low_quality_adverse_row_is_no_override() -> None:
    low = _row("Extraction-Oriented", None, "Low", "behaviour_flag")
    score = governance_sponsor_score([low, *_supportive(3)])
    assert (score.composite, score.risk_level, score.high_risk_action) == (
        "Not Scorable",
        "Insufficient Information",
        False,
    )
