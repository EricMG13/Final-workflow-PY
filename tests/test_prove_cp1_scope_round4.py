from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType

import pytest

from cases.prove.cp1_scope_round4 import (
    Counts,
    VerificationError,
    _acceptance_controls_pass,
    _has_required_api,
    _rehashed_context_mutation,
    _static_omission_refused,
    _verify_static_callers,
    evaluate_instrument_cases,
    instrument_cases,
    load_key,
    normalize_identity,
    normalize_scope,
    scope_text_matches,
)

REPO = Path(__file__).resolve().parents[1]
ROUND5_SOURCE = Path(
    "/Users/ericguei/.codex/worktrees/cp1-audit-scope-round5/Deploy Workflow/work/cp1-chain-runtime/audit.py"
)
ROUND5_SOURCE_SHA256 = "7db797b30cebd3a494de1512ba0fbb543c793675fc6a467c79439e34443bd3c4"


def test_frozen_scope_key_hash_is_pinned() -> None:
    key, digest = load_key(REPO)
    assert digest == "1be79cecd12f1727b2e583ef85867a491a4d80a6d5fa0dcb38f6173340f04d53"
    assert len(key["positive_controls"]) == 2
    assert len(key["negative_controls"]) == 17
    assert len(key["positive_controls"]) + len(key["negative_controls"]) + 4 == 23
    page_hashes = key["source"]["page_text_sha256"]
    assert {"105", "106", "107", "109"} <= set(page_hashes)
    assert all(len(page_hashes[page]) == 64 for page in ("105", "106", "107", "109"))


def test_instrument_matrix_preserves_all_keyed_negative_classes() -> None:
    key, _ = load_key(REPO)
    _, bad = instrument_cases(key)
    instrument_ids = {case_id.removeprefix("missing-text-") for case_id, _, _ in bad}
    assert {control["id"] for control in key["negative_controls"]} <= instrument_ids


def test_static_instrument_refuses_missing_caller_binding() -> None:
    if not ROUND5_SOURCE.is_file():
        pytest.skip("frozen round-5 audit source is not present in this checkout")
    baseline = ROUND5_SOURCE.read_text(encoding="utf-8")
    omitted = (
        baseline
        + "\ndef _actual_period_crosswalk(financial, oracle, *, store, provenance, scope=None):\n    return financial\n"
    )
    errors = _verify_static_callers(omitted)
    assert any("makes scope input optional" in error for error in errors)
    assert any(
        "does not enforce through _require_verified_financial_scope" in error for error in errors
    )
    assert _static_omission_refused(errors, "_actual_period_crosswalk")


def test_static_omission_fixture_does_not_pass_on_unrelated_errors() -> None:
    assert not _static_omission_refused(
        ["_audit_profile_maps does not enforce through _require_verified_financial_scope"],
        "_actual_period_crosswalk",
    )


def test_failed_or_missing_control_cannot_set_component_acceptance() -> None:
    assert _acceptance_controls_pass(Counts(23, 23, 23, 0, 0), 23)
    assert not _acceptance_controls_pass(Counts(23, 23, 22, 1, 0), 23)
    assert not _acceptance_controls_pass(Counts(23, 22, 22, 0, 1), 23)


def test_static_gate_accepts_frozen_candidate_transitive_and_positional_flow() -> None:
    if not ROUND5_SOURCE.is_file():
        pytest.skip("frozen round-5 audit source is not present in this checkout")
    assert hashlib.sha256(ROUND5_SOURCE.read_bytes()).hexdigest() == ROUND5_SOURCE_SHA256
    source = ROUND5_SOURCE.read_text(encoding="utf-8")
    assert (
        "_require_verified_financial_scope(financial, oracle, store, provenance, scope)" in source
    )
    assert "return _actual_period_crosswalk(" in source
    assert _verify_static_callers(source) == []


def test_static_gate_rejects_projection_bypass_outside_authenticated_parent() -> None:
    if not ROUND5_SOURCE.is_file():
        pytest.skip("frozen round-5 audit source is not present in this checkout")
    source = ROUND5_SOURCE.read_text(encoding="utf-8")
    bypass = (
        source
        + "\ndef forged_path(financial, oracle):\n    return _audit_financial_rows(financial, oracle, rows_by_model_id={}, periods_by_oracle_id={}, extracted_tables=())\n"
    )
    errors = _verify_static_callers(bypass)
    assert any("unauthenticated call path to _audit_financial_rows" in error for error in errors)


def test_context_mutation_rehashes_only_typed_context_link_and_preserves_originals() -> None:
    from deploy_vii.context_binding import BookEntityBinding, FinancialContextBinding
    from deploy_vii.source_context import SourceContextReview

    context = SourceContextReview(pack_sha256="a" * 64, entities=(), sources=())
    binding = FinancialContextBinding(
        financial_review_sha256="b" * 64,
        source_context_review_sha256=context.content_hash(),
        books=(BookEntityBinding(book_id="book", entity_id="entity"),),
    )
    provenance = {"context_review": context, "context_binding": binding, "sentinel": object()}

    def append_marker(data: dict[str, object]) -> None:
        data["limitations"] = ("scope verifier forged context marker",)

    forged = _rehashed_context_mutation(provenance, append_marker)
    assert provenance["context_review"] is context
    assert provenance["context_binding"] is binding
    assert forged["context_review"].content_hash() != context.content_hash()
    assert (
        forged["context_binding"].source_context_review_sha256
        == forged["context_review"].content_hash()
    )
    assert forged["context_binding"].financial_review_sha256 == binding.financial_review_sha256
    assert forged["sentinel"] is provenance["sentinel"]


def test_only_key_permitted_normalization_is_applied() -> None:
    key, _ = load_key(REPO)
    parent = key["source_derived_identity"]["parent_name"]
    accepted = [
        template.replace("<parent>", parent) for template in key["accepted_scope_templates"]
    ]
    for text in accepted:
        assert scope_text_matches(text, parent, key)
        assert scope_text_matches(text.upper(), parent.upper(), key)
        assert scope_text_matches(text.upper(), parent, key)
        assert scope_text_matches("  ".join(text.split()) + ".", parent, key)
        assert not scope_text_matches(text + " prepared for lenders", parent, key)


def test_instrument_examples_respect_full_string_without_claiming_evidence_refusals() -> None:
    key, _ = load_key(REPO)
    good, bad = instrument_cases(key)
    assert len(good) == 6
    assert len(bad) == 22
    assert all(
        scope_text_matches(text, key["source_derived_identity"]["parent_name"], key)
        for _, text, _ in good
    )
    assert all(
        not scope_text_matches(text, key["source_derived_identity"]["parent_name"], key)
        for _, text, _ in bad
    )
    counts = evaluate_instrument_cases(key)
    assert counts.as_dict() == {
        "required": len(good) + len(bad),
        "evaluated": len(good) + len(bad),
        "correct": len(good) + len(bad),
        "failed": 0,
        "missing": 0,
    }
    assert "missing-text-missing-context" in {case_id for case_id, _, _ in bad}


def test_missing_scope_api_is_an_explicit_blocker() -> None:
    module = ModuleType("clean_old_candidate")
    function, error = _has_required_api(module)
    assert function is None
    assert error == "candidate API missing: _verify_financial_scope"


def test_scope_api_rejects_optional_evidence_parameters() -> None:
    module = ModuleType("candidate")

    def optional_api(
        financial: object, provenance: object = None, oracle: object = None, store: object = None
    ) -> None:
        return None

    module.__dict__["_verify_financial_scope"] = optional_api
    function, error = _has_required_api(module)
    assert function is None
    assert error == "candidate API makes required evidence inputs optional"


def test_authenticated_identity_normalizes_only_case_and_whitespace() -> None:
    key, _ = load_key(REPO)
    parent = key["source_derived_identity"]["parent_name"]
    assert normalize_identity(parent.upper()) == normalize_identity(parent)
    assert normalize_identity("  ".join(parent.split())) == normalize_identity(parent)
    assert normalize_identity("TDG") != normalize_identity(parent)
    assert normalize_identity(parent + ".") != normalize_identity(parent)


@pytest.mark.parametrize(
    "value",
    [
        None,
        1,
        "TransDigm Group Incorporated and subsidiaries, consolidated; intercompany balances and transactions eliminated..",
    ],
)
def test_invalid_or_overnormalized_scope_inputs_do_not_pass(value: object) -> None:
    key, _ = load_key(REPO)
    if isinstance(value, str):
        assert not scope_text_matches(value, key["source_derived_identity"]["parent_name"], key)
    else:
        with pytest.raises(VerificationError):
            normalize_scope(value)  # type: ignore[arg-type]
