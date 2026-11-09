"""S13-C08: an issuer name with braces or square brackets stays valid run text in a claim."""

import pytest

from deploy_vii import prose
from deploy_vii.contracts import Claim
from deploy_vii.narrative import IssuerPart, ProsePart
from deploy_vii.narrative_projection import _passage


@pytest.mark.parametrize(
    ("name", "shown"),
    [
        ("Acme Holdings [UK] Ltd", "Acme Holdings (UK) Ltd"),
        ("Acme [Holdings Ltd", "Acme (Holdings Ltd"),
        ("Acme {Group}", "Acme (Group)"),
        ("Acme Group 4 [UK]", "Acme Group 4 (UK)"),
    ],
)
def test_reserved_characters_of_an_issuer_name_become_round_brackets_in_a_claim(
    name: str, shown: str
) -> None:
    # By hand: "[" and "]" and "{" and "}" are reserved run-text syntax, so each reads "(" or ")"
    # in a claim; the table text (chips False) keeps the name as it is. The digit of "Group 4" is
    # part of the supplied name, so it is no bare figure in either spelling.
    passage = (IssuerPart(), ProsePart(text=" reported higher leverage"))
    text, _ = _passage(passage, name, {}, {}, {}, "f1/evidence", chips=True)
    assert text == shown + " reported higher leverage"
    claim = Claim(claim_id="f1", text=f"Leverage · Title\n\nEvidence\n{text}", citations=())
    assert prose.issues(claim.text, {}, names=(name,)) == ()
    table_text, _ = _passage(passage, name, {}, {}, {}, "f1/evidence")
    assert table_text == name + " reported higher leverage"
