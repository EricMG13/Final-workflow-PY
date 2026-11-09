"""S16 A04/C06/C07: one source is one family however its label is spelled or its bytes repeated."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from cpdr_o7b1b_support import brief, evidence, sources

from deploy_workflow.research import review as r
from deploy_workflow.research import tables
from deploy_workflow.research.intake import intake, parse_rows

H1, H2 = "a" * 64, "b" * 64


def _issues(first: str, second: str, h2: str = H2) -> list[str]:
    family_of = {"ev-1": (r.family_key(first), H1), "ev-2": (r.family_key(second), h2)}
    return [i.text for i in r._family_issues("q1", ("ev-1", "ev-2"), family_of)]


# Hand-derived: each pair names one outlet; only a truly different name is independent.
@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Reuters", "Reuters"),
        ("Reuters", "reuters"),
        ("Reuters", "Reuters "),
        ("Reuters", "  Reuters\t"),
        ("Reuters News", "Reuters   News"),
        ("Reuters", "Ｒｅｕｔｅｒｓ"),  # fullwidth, NFKC
        ("Reuters", "Reu\u200bters"),  # zero-width space
        ("Réuters", "RÉUTERS"),
        ("Straße", "STRASSE"),  # casefold, not lower
    ],
)
def test_label_variants_are_one_family(first: str, second: str) -> None:
    assert len(_issues(first, second)) == 1


@pytest.mark.parametrize(("first", "second"), [("Reuters", "Reuter"), ("Reuters", "Bloomberg")])
def test_different_families_stay_independent(first: str, second: str) -> None:
    assert _issues(first, second) == []


def test_distinct_accented_names_are_not_merged() -> None:
    assert _issues("Reuters", "Réuters") == []


def test_identical_content_is_one_source_under_two_families() -> None:
    # Hand-derived: same hash H1 under 'Wire A' and 'Wire B' -> one issue naming the content.
    assert _issues("Wire A", "Wire B", h2=H1) == [
        "families not independent: ev-1 and ev-2 hold identical content"
    ]


def test_same_file_twice_from_intake_is_not_independent(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("Alder Ridge said revenue rose.\n", encoding="utf-8")
    base = {"path": "a.txt", "locator": "L", "tag": "research", "published": "2025-01-01"}
    rows = parse_rows([{**base, "family": "Wire A"}, {**base, "family": "Wire B"}])
    day = date(2026, 1, 1)
    got = intake(rows, base_dir=tmp_path, dest_dir=None, as_of=day, cutoff=day, today=day)
    family_of = {i.item_id: (r.family_key(i.family), i.sha256) for i in got.accepted}
    assert len(r._family_issues("q1", ("ev-1", "ev-2"), family_of)) == 1


def _review(
    submissions: dict[str, Any],
    expected: dict[str, Any],
    manifest: dict[str, Any],
    ev3: dict[str, str],
) -> list[tuple[str, str]]:
    """research_v1 (competition.c1 lists ev-1 and ev-3 as independent) with ev-3 changed."""
    items = [i.model_copy(update=ev3) if i.item_id == "ev-3" else i for i in evidence(expected)]
    issues = r.research_issues(
        submission=r.ResearchSubmission.parse(submissions["research_v1"]),
        brief=brief(expected),
        evidence=items,
        sources=sources(manifest),
    )
    return [(i.question_id, i.text) for i in issues]


# S16 A04/C06 review, through research_issues (the production mapping), hand-derived from the
# frozen oracle: ev-1 is 'sector-desk-notes', ev-3 'registry-filings' with another hash.
def test_review_merges_a_label_variant_and_identical_content(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    ev1 = next(i for i in evidence(expected) if i.item_id == "ev-1")
    assert _review(submissions, expected, manifest, {}) == []
    variant = {"family": " Sector-Desk-Notes\u200b"}  # space, case, zero-width space
    assert _review(submissions, expected, manifest, variant) == [
        ("competition", "families not independent: ev-1 and ev-3 share family sector-desk-notes")
    ]
    assert _review(submissions, expected, manifest, {"sha256": ev1.sha256}) == [
        ("competition", "families not independent: ev-1 and ev-3 hold identical content")
    ]


def test_the_stored_family_label_is_shown_unnormalised(
    submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    # The key decides independence only: TDR.2 shows each cited label as the manifest gave it.
    items = [
        i.model_copy(update={"family": "SECTOR-desk-notes "}) if i.item_id == "ev-1" else i
        for i in evidence(expected)
    ]
    sub = r.ResearchSubmission.parse(submissions["research_v1"])
    b = brief(expected)
    composed = tables.compose(
        b, sub, items, r.answer_counts(sub), r.claim_states(sub, b), b.as_of.isoformat()
    )
    family = next(f for f in composed.facts if f.fact_id == "TDR.2.competition.c1.family")
    assert family.text == "SECTOR-desk-notes ; registry-filings"
