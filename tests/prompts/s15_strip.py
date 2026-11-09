"""Undo the S15-A02 wording in the readiness message (`readiness` only): READINESS_EVIDENCE_RULE
now names three more kinds whose null `amount` removes every tag (`computation`,
`historical_value`, `canonical_value`). Restoring the earlier kind list gives the message the
frozen digests pinned before the fix."""

S15_NEW = (
    "`kind=kpi`, `kind=statement_*`, `kind=observation`, `kind=computation`, "
    "`kind=historical_value` or `kind=canonical_value` line whose `amount` is null has no tag"
)
S15_OLD = (
    "`kind=kpi`, `kind=statement_*` or `kind=observation` line whose `amount` is null has no tag"
)


def undo_s15(step_id: str, text: str) -> str:
    """Restore the pre-S15 kind list in rule c of a composed readiness message."""
    if S15_NEW not in text:
        assert step_id != "readiness", step_id
        return text
    assert step_id == "readiness" and text.count(S15_NEW) == 1, step_id
    return text.replace(S15_NEW, S15_OLD)
