"""S09-cp4-cp5-A08: a `Same definition` whose definition quote names a document that is not in
the pack is refused (repairable); `Not determinable` is accepted.

Expected values are hand-derived from the quote texts written here, not from the gate.
"""

import importlib
from typing import Any

import pytest

from deploy_vii.business_context import Quote
from deploy_vii.contracts import Coverage, Source, Span
from deploy_workflow.owners import cp4

tm: Any = importlib.import_module("test_method_cp4")

# The positive case's covenant is `Same definition`, cites only pack source `legal-covenants`, and
# its quotes name no document (page 2 says "Group perimeter defined in Clause 1.2": no document
# noun). Each variant replaces its citations with the one quote below.
CREDIT = "Consolidated EBITDA has the meaning given to such term in the Credit Agreement."
ISSUE = (
    "covenants[0]: metric_basis 'Same definition' is refused because the definition quote says "
    "the term is defined in {documents}, which is not a source of this pack: the definition "
    "cannot be compared, so write 'Not determinable'"
)


def _run(quote_text: str, *, extra: tuple[Source, ...] = (), basis: str = "Same definition") -> Any:
    inputs = tm.make_inputs_object("positive")
    pack = inputs.pack.model_copy(update={"sources": (*inputs.pack.sources, *extra)})
    (covenant,) = inputs.submission.covenants
    citation = Quote(source_id="legal-covenants", locator="page:2", quote=quote_text)
    changed = covenant.model_copy(update={"citations": (citation,), "metric_basis": basis})
    submission = inputs.submission.model_copy(update={"covenants": (changed,)})
    return cp4.semantic_issues(pack=pack, submission=submission)


def _source(source_id: str, name: str, status: str = "ready") -> Source:
    ready = status == "ready"
    return Source(
        source_id=source_id,
        name=name,
        status=status,  # type: ignore[arg-type]
        sha256="a" * 64 if ready else None,
        spans=(Span(locator="page:1", text="text"),) if ready else (),
        limitation=None if ready else "not supplied",
        coverage=(Coverage(locator="page:1", status="retained"),) if ready else (),
        extraction_status="complete" if ready else "blocked",
    )


def test_a_clean_positive_quote_has_no_issue() -> None:
    assert _run("Group perimeter defined in Clause 1.2 of this Agreement.") == ()


def test_same_definition_naming_a_missing_credit_agreement_is_refused() -> None:
    # "in the Credit Agreement" names 'credit agreement'; no pack source is one.
    assert _run(CREDIT) == (ISSUE.format(documents="'credit agreement'"),)


def test_not_determinable_naming_a_missing_document_is_accepted() -> None:
    assert _run(CREDIT, basis="Not determinable") == ()


@pytest.mark.parametrize(
    "extra",
    [
        (_source("credit-agreement", "Credit Agreement"),),
        (_source("legal-2", "CREDIT  AGREEMENT dated 5 May 2024"),),
        (_source("credit-agreement", "Other name"),),  # the id read with dashes as spaces
        (_source("legal-2", "Senior Secured Credit Agreement"),),  # name contains the quoted name
    ],
)
def test_the_document_in_the_pack_leaves_same_definition_unchanged(
    extra: tuple[Source, ...],
) -> None:
    assert _run(CREDIT, extra=extra) == ()


def test_a_source_that_is_not_ready_is_not_in_the_pack() -> None:
    missing = (_source("credit-agreement", "Credit Agreement", status="missing"),)
    assert _run(CREDIT, extra=missing) == (ISSUE.format(documents="'credit agreement'"),)


@pytest.mark.parametrize(
    "text",
    [
        "as DEFINED in the CREDIT   AGREEMENT",
        "EBITDA is as defined\nin the\tCredit Agreement (not supplied)",
        "has the meaning assigned to it in the Credit Agreement",
        "is defined in Section 1.1 of the Credit Agreement",  # a section of the named document
        "defined in Schedule A of the CREDIT AGREEMENT",
    ],
)
def test_case_and_whitespace_variants_of_the_name_are_found(text: str) -> None:
    assert _run(text) == (ISSUE.format(documents="'credit agreement'"),)


def test_a_more_specific_quoted_name_is_not_the_shorter_pack_document() -> None:
    # 'credit agreement' is held, but the quote names the 'senior facility agreement'.
    held = (_source("credit-agreement", "Credit Agreement"),)
    text = "defined in the Senior Facility Agreement"
    assert _run(text, extra=held) == (ISSUE.format(documents="'senior facility agreement'"),)


def test_two_missing_documents_are_both_named_in_quote_order() -> None:
    text = "defined in the Credit Agreement; also defined in the Note Indenture"
    assert _run(text) == (ISSUE.format(documents="'credit agreement'; 'note indenture'"),)


@pytest.mark.parametrize(
    "text", ["defined in this Agreement", "defined in such Indenture", "defined in the Agreement"]
)
def test_the_document_itself_names_no_other_document(text: str) -> None:
    assert _run(text) == ()


def test_compute_refuses_before_the_engine_validator_and_composes_nothing() -> None:
    inputs = tm.make_inputs_object("positive")
    (covenant,) = inputs.submission.covenants
    citation = Quote(source_id="legal-covenants", locator="page:2", quote=CREDIT)
    changed = covenant.model_copy(update={"citations": (citation,)})
    submission = inputs.submission.model_copy(update={"covenants": (changed,)})
    result = cp4.compute(cp4.Cp4Inputs(inputs.pack, submission, inputs.upstream, inputs.inputs))
    assert result.issues == (ISSUE.format(documents="'credit agreement'"),)
    assert result.report is None


# --- review of ruling A08 (second model): name matching and the document forms of real text ---
# Each expected document is the quoted words read by hand: case folded, dashes as spaces.


@pytest.mark.parametrize(
    "source_id,text,document",
    [
        # One-letter ids are not words of the quoted name, so they hold no document.
        ("e", "defined in the Note Indenture", "note indenture"),
        ("t", "defined in the Intercreditor Agreement", "intercreditor agreement"),
    ],
)
def test_an_id_holds_a_document_only_as_whole_trailing_words(
    source_id: str, text: str, document: str
) -> None:
    held = (_source(source_id, "x.pdf"),)
    assert _run(text, extra=held) == (ISSUE.format(documents=f"'{document}'"),)


@pytest.mark.parametrize(
    "name,text",
    [
        # The file name without folder and extension ('notes indenture', 'credit agreement') ends
        # the quoted name, so the source is that document.
        ("sources/notes-indenture.pdf", "defined in the Senior Notes Indenture"),
        ("sources/credit-agreement.pdf", "as defined in our Credit Agreement"),
        ("sources/credit-agreement.pdf", "is defined in Section 1.1 of the Credit Agreement"),
    ],
)
def test_a_source_file_name_ending_the_quoted_name_holds_it(name: str, text: str) -> None:
    assert _run(text, extra=(_source("legal", name),)) == ()


def test_a_source_file_name_that_is_another_document_does_not_hold_it() -> None:
    held = (_source("legal", "sources/credit-agreement.pdf"),)
    text = "defined in the Intercreditor Agreement"
    assert _run(text, extra=held) == (ISSUE.format(documents="'intercreditor agreement'"),)


def test_dashes_in_the_quoted_name_read_as_spaces_on_both_sides() -> None:
    text = "defined in the Second-Lien Credit Agreement"
    held = (_source("second-lien-credit-agreement", "x.pdf"),)
    assert _run(text, extra=held) == ()
    assert _run(text) == (ISSUE.format(documents="'second lien credit agreement'"),)


def test_the_trust_indenture_act_is_a_statute_not_a_document() -> None:
    assert _run("terms defined in the Trust Indenture Act have the meanings so assigned") == ()


@pytest.mark.parametrize(
    "text,document",
    [
        # TDG FY2024 10-K wording (retained annual pages), plural and singular.
        ("Subsidiaries (as defined in the applicable indentures)", "applicable indentures"),
        ("Subsidiaries (as defined in the applicable indenture)", "applicable indenture"),
        # Typographic apostrophe, as in the retained 10-K text.
        ("as defined in the Company’s Credit Agreement", "company’s credit agreement"),
        # Retained DIP wording: plural "meanings" and an Article of the named document.
        (
            "have the meanings assigned to such terms in Article I of the Credit Agreement",
            "credit agreement",
        ),
        # "that certain" names an outside document (plural and singular pointer).
        (
            "have the meanings given to such terms in that certain Credit Agreement",
            "credit agreement",
        ),
        ("has the meaning given to it in that certain Credit Agreement", "credit agreement"),
    ],
)
def test_real_document_forms_are_found(text: str, document: str) -> None:
    assert _run(text) == (ISSUE.format(documents=f"'{document}'"),)


def test_that_alone_still_refers_to_the_document_itself() -> None:
    assert _run("defined in that Agreement") == ()


def test_a_possessive_name_is_held_by_a_source_ending_it() -> None:
    held = (_source("credit-agreement", "x.pdf"),)
    assert _run("as defined in the Company’s Credit Agreement", extra=held) == ()


# --- ruling: "set forth in", "specified in", "ascribed to ... in"; memorandum and prospectus ---
# Each expected name is the quoted words after the pointer, case folded, read by hand.

POINTER_CASES = [
    ("has the meaning set forth in the Credit Agreement", "credit agreement"),
    ("as set forth in Section 1.1 of the Credit Agreement", "credit agreement"),
    ("has the meaning specified in the Credit Agreement", "credit agreement"),
    ("have the meanings ascribed to such term in the Note Indenture", "note indenture"),
    ("the meaning ascribed in the Credit Agreement", "credit agreement"),
    ("as defined in the Offering Memorandum", "offering memorandum"),
    ("as set forth in the Base Prospectus Supplement", "base prospectus supplement"),
    ("specified in the Final Prospectus", "final prospectus"),
    ("defined in the Information Memoranda", "information memoranda"),
]


@pytest.mark.parametrize("text,document", POINTER_CASES)
def test_each_new_pointer_and_noun_is_refused_when_the_document_is_missing(
    text: str, document: str
) -> None:
    assert _run(text) == (ISSUE.format(documents=f"'{document}'"),)


@pytest.mark.parametrize("text,document", POINTER_CASES)
def test_each_new_pointer_and_noun_is_accepted_when_the_document_is_present(
    text: str, document: str
) -> None:
    held = (_source("doc", document.title() + ".pdf"),)
    assert _run(text, extra=held) == ()


@pytest.mark.parametrize(
    "text",
    [
        "as defined in the Senior Secured Facility",  # the loan itself, not a document
        "as set forth in the Senior Secured Notes",
        "specified in the Finance Documents",
        "set forth in the Conditions",
        "as specified in the Commitment Letter",
        "ascribed to such term in this Agreement",
        "set forth in the Memorandum",  # no qualifier: same shape as "the Agreement"
    ],
)
def test_facility_notes_documents_conditions_letter_name_no_document(text: str) -> None:
    assert _run(text) == ()


# --- second-model review of the pointer/noun ruling: a locator before the document itself ---
# A part of this document ("Section 7 of this Agreement") is no other document: a determiner after
# a locator the optional "Section 1.1 of" does not take, or "the" directly before the noun, makes
# the noun the document itself, as "this Agreement" and "the Agreement" do on their own.


@pytest.mark.parametrize(
    "text",
    [
        "has the meaning set forth in Section 7 of this Agreement",
        "defined in Clause 2 of this Agreement",  # the earlier pointer had the same fault
        "as specified in Section 5 of such Indenture",
        "set forth in Article II of the Indenture",
        "set forth in Schedule 1 to this Agreement",
        "in the form set forth in Exhibit A to this Agreement",
        "set forth in Section 7 of this Credit Agreement",
        "specified in paragraph 3 of this Prospectus",
        "set forth in the Agreement and this Indenture",
        "set forth in Schedule 1 to each Security Agreement",
        # The forms the ruling's reviewer named: no document after the pointer.
        "has the meaning set forth in Section 2.01",
        "as specified in this Indenture",
        "has the meaning ascribed to such term herein",
        "as defined in the Prospectus",
    ],
)
def test_a_part_of_the_document_itself_names_no_document(text: str) -> None:
    assert _run(text) == ()


@pytest.mark.parametrize(
    "text,document",
    [
        # "the" before a qualifier still names an outside document (retained TDG indenture wording).
        (
            (
                "subject to the limitations set forth in the security documents and the "
                "intercreditor agreements"
            ),
            "security documents and the intercreditor agreements",
        ),
        # A locator outside the optional "Section 1.1 of" stays in the quoted name, as before.
        ("set forth in Exhibit A to the Credit Agreement", "exhibit a to the credit agreement"),
        ("as specified in Section 4 of the Credit Agreement", "credit agreement"),
        # Retained Enel supplement wording; that pack holds no base prospectus.
        (
            "terms defined in the Base Prospectus shall have the same meaning in this Supplement",
            "base prospectus",
        ),
    ],
)
def test_an_outside_document_after_a_locator_or_qualifier_is_still_named(
    text: str, document: str
) -> None:
    assert _run(text) == (ISSUE.format(documents=f"'{document}'"),)


def test_the_locator_name_is_held_by_a_source_ending_it() -> None:
    held = (_source("credit-agreement", "x.pdf"),)
    assert _run("set forth in Exhibit A to the Credit Agreement", extra=held) == ()


def test_a_prospectus_is_held_by_a_file_name_containing_it() -> None:
    held = (_source("s1", "sources/base-prospectus-2018.pdf"),)
    text = "terms defined in the Base Prospectus shall have the same meaning"
    assert _run(text, extra=held) == ()


def test_a_long_quote_of_self_references_names_no_document() -> None:
    # 2,000 self-references (about 86 KB): the per-word check stays linear and names nothing.
    assert _run("has the meaning set forth in Section 7 of this Agreement; " * 2000) == ()
