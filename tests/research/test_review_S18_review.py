"""S18 review fixes in the CP-DR research review: a not_found answer cites no contrary item, and
the one shared text rule (``review.text_issues``) behaves as the three copies it replaced did.

The submissions are the frozen cpdr-research-owner oracle (read, never edited)."""

import copy
from typing import Any

from cpdr_o7b1b_support import brief, evidence, sources

from deploy_workflow.research import review
from deploy_workflow.research import steps as s


def issues_of(
    body: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> list[str]:
    found = review.research_issues(
        submission=review.ResearchSubmission.parse(body),
        brief=brief(expected),
        evidence=evidence(expected),
        sources=sources(manifest),
    )
    return [str(issue) for issue in found]


def test_a_not_found_answer_with_a_cited_contrary_item_is_an_issue(
    expected: dict[str, Any], submissions: dict[str, Any], manifest: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    assert issues_of(body, expected, manifest) == []
    not_found = next(a for a in body["answers"] if a["answer_state"] == "not_found")
    cited = next(c for a in body["answers"] for c in a["contrary"] if c["kind"] == "cited")
    not_found["contrary"] = [copy.deepcopy(cited)]
    assert issues_of(body, expected, manifest) == [
        f"{not_found['question_id']}: a not_found question cites no contrary item"
    ]


def test_a_not_found_answer_with_a_none_found_entry_is_still_accepted(
    expected: dict[str, Any], submissions: dict[str, Any], manifest: dict[str, Any]
) -> None:
    body = copy.deepcopy(submissions["research_v1"])
    not_found = next(a for a in body["answers"] if a["answer_state"] == "not_found")
    not_found["contrary"] = [
        {
            "kind": "none_found",
            "searched": list(not_found["searched"]),
            "limitation": "Nothing contrary was found in the searched items.",
        }
    ]
    assert issues_of(body, expected, manifest) == []


def test_the_shared_text_rule_reports_each_banned_word_once_then_the_figure() -> None:
    texts = ["We Recommend it.", "Twelve months.", "Up 3 points and recommended."]
    assert [str(i) for i in review.text_issues("q1", texts)] == [
        "q1: banned word: recommend",
        "q1: text must not contain a figure",
    ]
    assert review.text_issues("q1", ["Plain words only."]) == []
    assert [str(i) for i in review.text_issues("q1", ["٣ is an Arabic-Indic digit."])] == [
        "q1: text must not contain a figure"
    ]


def test_the_brief_step_reads_the_question_text_through_the_shared_rule() -> None:
    question = s.BriefQuestion(question_id="custom-1", text="Recommend 2 peers.", kind="custom")
    assert s._language(question) == [
        "custom-1: banned word: recommend",
        "custom-1: text must not contain a figure",
    ]
