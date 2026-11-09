"""The repeated-validation theme (S07-cp2-gh-C01 and its duplicates S07-cp2-gh-C02, S06-cp2-ade-C06,
S08-cp3-C10, S10-cp6-cp8-cpl10-C05): one `_validate_step` validates a submission once and composes
it once; the public composers keep their own guard.

Each count is a function that runs once per validation pass or once per composition. A full submit
runs `_validate_step` twice by design (the journal's step validation, then the trusted re-check
before settlement), so the expected counts below are 2 per submit: one validation and one
composition per `_validate_step`. Before the change they were 6 content checks (CP-2G), 6
validation passes and 8 composes (CP-2H), 6 (CP-2A), 6 (CP-2D), 2 per step (CP-2, CP-3, CP-6).
"""

import dataclasses
import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import test_claim_limitation_spelled as limits
import test_connect_cp2a as tc2a
import test_connect_cp2d as tc2d
import test_connect_cp2g as tc2g
import test_connect_cp2h as tc2h
import test_method_cp3 as tm3

from deploy_vii import cp2_synthesis, cp3_relative_value, cp6_committee
from deploy_workflow.owners import cp2a, cp2d, cp2g, cp2h, cp3


def _count(monkeypatch: pytest.MonkeyPatch, module: Any, *names: str) -> Counter[str]:
    calls: Counter[str] = Counter()
    for name in names:
        original = getattr(module, name)

        def counted(*args: Any, __name: str = name, __f: Any = original, **kwargs: Any) -> Any:
            calls[__name] += 1
            return __f(*args, **kwargs)

        monkeypatch.setattr(module, name, counted)
    return calls


@pytest.fixture
def cp2g_seeded(tmp_path: Path) -> Iterator[tuple[Any, Any, Any]]:
    yield tc2g._case_seed(tmp_path, "positive")


def test_cp2g_submit_checks_content_once_per_step(
    cp2g_seeded: tuple[Any, Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = cp2g_seeded
    calls = _count(monkeypatch, cp2g, "content_issues", "_resolve", "_validate_step")
    tc2g._submit(store, attempt, json.dumps(tc2g._payload("positive")))
    finished = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    assert finished.status == "finished" and finished.issues == ()
    # two steps (journal + trusted re-check), one content check and one forecast each
    assert calls == Counter({"_validate_step": 2, "content_issues": 2, "_resolve": 2})


def test_cp2g_public_guards_still_refuse(cp2g_seeded: tuple[Any, Any, Any]) -> None:
    store, pack, attempt = cp2g_seeded
    payload = tc2g._payload("positive")
    payload["assessment"]["confidence"] = "High"  # HIGH_ISSUE, a content issue
    submission = cp2g.ForwardSubmission.model_validate_json(json.dumps(payload))
    upstream = cp2g.cp2g_upstream(store=store, attempt=attempt)
    assert cp2g.validate_forward(pack=pack, submission=submission, upstream=upstream) == (
        cp2g.HIGH_ISSUE,
    )
    with pytest.raises(ValueError, match="High is not allowed"):
        cp2g.forward_model(pack=pack, submission=submission, upstream=upstream)
    with pytest.raises(ValueError, match="CP-2G submission has issues"):
        cp2g.compute(cp2g._inputs(pack, submission, upstream))


def test_cp2h_submit_parses_the_register_once_and_validates_once_per_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, attempt = tc2h.seed(tmp_path, "positive")
    payload = tc2h._submission(store, "positive").model_dump_json()
    calls = _count(monkeypatch, cp2h, "register_source", "_compose", "_view_issues", "select_cp1")
    tc2h._submit(store, attempt, payload)
    finished = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    assert finished.status == "finished" and finished.issues == ()
    # per step: one register read, one validation pass, and two composes (the validation book
    # without the analyst tables, then the submission's book); was 8, 6 and 8 per submit
    assert (calls["register_source"], calls["_view_issues"], calls["_compose"]) == (2, 2, 4)
    # the CP-1 ratios are selected once per compose, not once per trigger (was 66 per submit)
    assert calls["select_cp1"] <= 18


def test_cp2h_public_guards_still_refuse(tmp_path: Path) -> None:
    store, pack, attempt = tc2h.seed(tmp_path, "positive")
    good = tc2h._submission(store, "positive")
    overall = good.overall.model_copy(update={"confidence": "High"})
    submission = good.model_copy(update={"overall": overall})
    upstream = cp2h.cp2h_upstream(store=store, attempt=attempt)
    issues = cp2h.validate_triggers(pack=pack, submission=submission, upstream=upstream)
    assert issues and all("High" in i for i in issues)
    with pytest.raises(ValueError, match="High is not allowed"):
        cp2h.rating_triggers(pack=pack, submission=submission, upstream=upstream)
    with pytest.raises(ValueError, match="High is not allowed"):
        cp2h.compute(cp2h._inputs(pack, submission, upstream))


def test_cp2a_submit_validates_once_per_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, _ = tc2a.seed(tmp_path)
    attempt = store.begin("CP-2A")
    calls = _count(monkeypatch, cp2a, "validate", "_pin_lines", "offered_bases", "_operands")
    tc2a._submit(store, attempt, json.dumps(tc2a._positive_payload()))
    finished = next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
    assert finished.status == "finished" and finished.issues == ()
    # per step: one content check, one pin check, one CP-1 base offer and one composition
    # (was 6, 4, 6 and 2 per submit)
    assert calls == Counter({"validate": 2, "_pin_lines": 2, "offered_bases": 2, "_operands": 2})


def test_cp2a_public_guards_still_refuse(tmp_path: Path) -> None:
    store, pack, _ = tc2a.seed(tmp_path)
    attempt = store.begin("CP-2A")
    payload = tc2a._positive_payload()
    payload["base_period"] = "LTM Q4 24: 2024-01-01 to 2024-12-31"  # not an offered period
    submission = cp2a.DownsideSubmission.model_validate_json(json.dumps(payload))
    upstream = cp2a.cp2a_upstream(store, attempt)
    issues = cp2a.validate_downside(pack=pack, submission=submission, upstream=upstream)
    assert issues and issues[0].startswith("base_period: not an offered period")
    with pytest.raises(ValueError, match="base_period: not an offered period"):
        cp2a.downside_report(pack=pack, submission=submission, upstream=upstream)


def test_cp2d_submit_validates_once_per_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt = tc2d.make_upstream(tmp_path)
    calls = _count(monkeypatch, cp2d, "submission_issues", "run_basis", "_pin_lines", "bridge_of")
    tc2d._submit(store, attempt, tc2d._literal("positive"))
    finished = tc2d._finished(store, attempt.ticket_id)
    assert finished.status == "finished" and finished.issues == ()
    # per step: one submission check, one basis read, one pin check, one bridge (was 6, 6, 4, 2)
    assert calls == Counter(
        {"submission_issues": 2, "run_basis": 2, "_pin_lines": 2, "bridge_of": 2}
    )


def test_cp2d_public_guards_still_refuse(tmp_path: Path) -> None:
    store, attempt = tc2d.make_upstream(tmp_path)
    payload = json.loads(tc2d._literal("positive"))
    payload["horizon_months"] = 0
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(json.dumps(payload))
    upstream = cp2d.cp2d_upstream(store=store, attempt=attempt)
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=submission, upstream=upstream
    )
    assert cp2d.HORIZON_ISSUE in issues
    with pytest.raises(ValueError, match=cp2d.HORIZON_ISSUE):
        cp2d.liquidity_bridge(pack=store.pack(), submission=submission, upstream=upstream)


class _Store:
    """The one store method a VII `_validate_step` reads before its upstream adapter."""

    def __init__(self, payload: str) -> None:
        self.text = payload

    def payload(self, _sha256: str) -> str:
        return self.text


class _Step:
    payload_sha256 = "0" * 64


class _Attempt:
    steps = (_Step(),)


def _vii_step(
    monkeypatch: pytest.MonkeyPatch, module: Any, adapter: str, case: tuple[Any, Any, Any]
) -> Any:
    """`module._validate_step` over a (pack, submission, upstream) case, the upstream adapter
    returning the case's upstream."""
    pack, submission, upstream = case
    monkeypatch.setattr(module, adapter, lambda *_a, **_k: upstream)
    return module._validate_step(_Store(submission.model_dump_json()), pack, _Attempt())


def test_cp2_step_validates_once(monkeypatch: pytest.MonkeyPatch) -> None:
    pack, submission, upstream = limits._cp2_case("Leverage of {T4.10.lev|x} is LTM only.")
    calls = _count(monkeypatch, cp2_synthesis, "_provenance_issues", "_assessment")
    outcome = _vii_step(monkeypatch, cp2_synthesis, "cp2_upstream", (pack, submission, upstream))
    assert outcome.issues == () and outcome.output is not None
    # one validation pass and one composition (was two validation passes)
    assert calls == Counter({"_provenance_issues": 1, "_assessment": 1})
    # the step's output is the guarded composer's
    report = cp2_synthesis.credit_synthesis(pack, submission, upstream)
    assert outcome.output == report.model_dump_json()


def test_cp2_public_guard_still_refuses() -> None:
    pack, submission, upstream = limits._cp2_case("Leverage of {T4.10.lev|x} is LTM only.")
    bad = submission.model_copy(
        update={"key_findings": (cp2_synthesis.Finding(text="Leverage is 4.2x.", cp1a_refs=()),)}
    )
    issues = cp2_synthesis.validate_credit_synthesis(pack, bad, upstream)
    assert issues
    with pytest.raises(ValueError, match="key_findings"):
        cp2_synthesis.credit_synthesis(pack, bad, upstream)


def test_cp6_step_validates_once(monkeypatch: pytest.MonkeyPatch) -> None:
    case = limits._cp6_case("CP-1 shows EBITDA of {T4.10.ebitda.fy2025|US$ m} only")
    calls = _count(
        monkeypatch, cp6_committee, "_provenance_issues", "_reference_issues", "_recommendation"
    )
    outcome = _vii_step(monkeypatch, cp6_committee, "cp6_upstream", case)
    assert outcome.issues == () and outcome.output is not None
    # one validation pass and one composition (was two validation passes)
    assert calls == Counter({"_provenance_issues": 1, "_reference_issues": 1, "_recommendation": 1})
    assert outcome.output == cp6_committee.committee_challenge(*case).model_dump_json()


def test_cp6_public_guard_still_refuses() -> None:
    pack, submission, upstream = limits._cp6_case("No market evidence")
    rec = submission.recommendation.model_copy(update={"rationale": "EBITDA is 120 million"})
    bad = submission.model_copy(update={"recommendation": rec})
    issues = cp6_committee.validate_committee(pack, bad, upstream)
    assert issues
    with pytest.raises(ValueError, match="recommendation"):
        cp6_committee.committee_challenge(pack, bad, upstream)


def _cp3_inputs_with_ten_risks() -> Any:
    """The finding's case: the positive CP-3 inputs with ten risks each citing T2.11.r01."""
    inputs = tm3.make_inputs("positive")
    risk = inputs.submission.risks[0].model_copy(update={"cp2_refs": ("T2.11.r01",)})
    submission = inputs.submission.model_copy(update={"risks": (risk,) * 10})
    return dataclasses.replace(inputs, submission=submission)


def test_cp3_compute_validates_once_and_builds_the_catalogue_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _count(
        monkeypatch,
        cp3_relative_value,
        "_instrument_issues",
        "cp2_catalogue",
        "context_evidence",
        "_instruments",
    )
    result = cp3.compute(_cp3_inputs_with_ten_risks())
    assert result.issues == () and result.report is not None
    # one validation pass, one catalogue for the Upstream, the context read once by the
    # validation and once by the composer's evidence binding, one composition
    # (was 2, 25, 3 and 1)
    assert calls == Counter(
        {"_instrument_issues": 1, "cp2_catalogue": 1, "context_evidence": 2, "_instruments": 1}
    )


def test_cp3_step_validates_once(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _cp3_inputs_with_ten_risks()
    upstream = cp3._upstream(inputs)
    calls = _count(monkeypatch, cp3_relative_value, "_instrument_issues", "_instruments")
    case = (inputs.pack, inputs.submission, upstream)
    outcome = _vii_step(monkeypatch, cp3_relative_value, "cp3_upstream", case)
    assert outcome.issues == () and outcome.output is not None
    assert calls == Counter({"_instrument_issues": 1, "_instruments": 1})
    assert outcome.output == cp3_relative_value.relative_value(*case).model_dump_json()


def test_cp3_public_guard_still_refuses() -> None:
    inputs = tm3.make_inputs("positive")
    preference = inputs.submission.preference.model_copy(update={"ordering": ("no-such",)})
    bad = inputs.submission.model_copy(update={"preference": preference})
    upstream = cp3._upstream(inputs)
    issues = cp3_relative_value.validate_relative_value(inputs.pack, bad, upstream)
    assert "preference.ordering: no-such is not an instruments row" in issues
    with pytest.raises(ValueError, match="not an instruments row"):
        cp3_relative_value.relative_value(inputs.pack, bad, upstream)
    assert cp3.compute(dataclasses.replace(inputs, submission=bad)).issues == issues


def test_review_an_upstream_catalogue_is_per_object_and_a_replaced_upstream_rebuilds() -> None:
    """The cached catalogue belongs to one Upstream; `dataclasses.replace` yields a fresh object
    whose catalogue follows its own bound CP-2 status (blocked: empty)."""
    inputs = tm3.make_inputs("positive")
    upstream = cp3._upstream(inputs)
    catalogue = upstream.catalogue
    assert catalogue and upstream.catalogue is catalogue
    blocked = tuple(
        item.model_copy(update={"status": "blocked"})
        if item.input_id == cp3_relative_value.CP2
        else item
        for item in upstream.bound
    )
    other = dataclasses.replace(upstream, bound=blocked)
    assert other.catalogue == {}
    assert upstream.catalogue is catalogue
