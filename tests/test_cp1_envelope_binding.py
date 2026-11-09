"""A05/C03: an exported CP-1 envelope is bound to the handoff its promotion retained.

The export (Markdown, sidecar and receipt) can be rewritten consistently: the receipt's file
hashes and its registers and QA hashes recomputed from the rewritten envelope. Only the
journal's promoted attempt and its retained `quality` step output (`CP1Handoff`) are outside
the export, so the registers hash, gap limitations, QA report and journal inputs must equal
what they recorded. The store is a stub with the journal's shape (heads, attempts, step
outputs); the expected issue lines are written out by hand from the binding rule.
"""

import hashlib
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.contracts import Input, Module, Run
from deploy_vii.cp1_workflow import CP1_STEPS, CP1Handoff, EnvelopeRefused, read_cp1_envelope
from deploy_vii.envelope import Envelope, write_envelope
from deploy_vii.execution import text_sha256
from deploy_vii.quality import CoverageField, QualityInputs, QualityReview, assess_quality


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


RUN = Run(
    run_id="r1",
    issuer_id="iss",
    issuer_name="Issuer",
    as_of=date(2026, 1, 31),
    case_kind="synthetic",
    requested_modules=("CP-1",),
)
JOURNAL = (Input(input_id="prepared-pack", sha256=h("pack")), Input(input_id="cp0", sha256=h("c")))
MODULE = Module(
    run_id="r1",
    issuer_id="iss",
    as_of=date(2026, 1, 31),
    module_id="CP-1",
    status="restricted",
    inputs=(*JOURNAL, Input(input_id="pack", sha256=h("pack"))),
    limitations=("Q4 cash flow statement missing",),
)
GAPS = ("FY2024 comparatives absent: growth not calculable",)


def _report(coverage_present: bool) -> Any:
    inputs = QualityInputs(
        artifact_sha256=h("registers"),
        coverage_policy="One slot per required register",
        claims=(),
        coverage=(CoverageField(field_id="slot", present=coverage_present, rationale="Slot"),),
        source_gate="pass",
        module_status="restricted",
        references=(),
        ceilings=(),
    )
    return assess_quality(inputs, QualityReview(inputs_sha256=inputs.content_hash(), claims=()))


QUALITY = _report(False)
HANDOFF = CP1Handoff(
    registers_sha256=h("registers"),
    quality=QUALITY,
    gap_limitations=GAPS,
    candidate_sha256=h("candidate"),
    envelope_sha256=h("envelope"),
    sidecar_sha256=h("sidecar"),
)
GENUINE = Envelope(
    run=RUN,
    module=MODULE,
    registers_sha256=HANDOFF.registers_sha256,
    gap_limitations=GAPS,
    quality=QUALITY,
    journal=JOURNAL,
)


def _store() -> Any:
    head = SimpleNamespace(
        module_id="CP-1",
        status="restricted",
        result_sha256=MODULE.content_hash(),
        qualification=None,
    )
    steps = [SimpleNamespace(step_id=s, output_sha256=None) for s in CP1_STEPS]
    steps.append(SimpleNamespace(step_id="quality", output_sha256=h("handoff")))
    attempt = SimpleNamespace(
        result_sha256=MODULE.content_hash(), steps=steps, inputs=JOURNAL, ticket_id="t1"
    )
    snapshot = SimpleNamespace(heads=[head], attempts=[attempt], run=RUN, pack_sha256=h("pack"))
    outputs = {h("handoff"): HANDOFF.model_dump_json()}
    return SimpleNamespace(read=lambda: snapshot, step_output=outputs.__getitem__)


def _export(envelope: Envelope, directory: Path) -> Path:
    """A consistent export of `envelope`: the receipt is recomputed from it, as a forger would."""
    markdown, sidecar = write_envelope(envelope)
    quality = None if envelope.quality is None else envelope.quality.content_hash()
    directory.mkdir()
    (directory / "envelope.md").write_text(markdown, encoding="utf-8")
    (directory / "envelope.json").write_text(sidecar, encoding="utf-8")
    receipt = {
        "schema_version": "cp1-envelope/1",
        "module_sha256": MODULE.content_hash(),
        "pack_sha256": h("pack"),
        "registers_sha256": envelope.registers_sha256,
        "quality_report_sha256": quality,
        "status": "restricted",
        "qualification": None,
        "files": {"envelope.md": text_sha256(markdown), "envelope.json": text_sha256(sidecar)},
    }
    (directory / "complete.json").write_text(json.dumps(receipt), encoding="utf-8")
    return directory


def test_the_genuine_export_reads_back(tmp_path: Path) -> None:
    got = read_cp1_envelope(_store(), _export(GENUINE, tmp_path / "x"))
    assert (got.gap_limitations, got.registers_sha256) == (GAPS, h("registers"))


PREFIX = "Envelope differs from the promoted handoff: "


@pytest.mark.parametrize(
    ("update", "issues"),
    [
        ({"gap_limitations": ()}, (PREFIX + "gap limitations",)),
        (
            {"registers_sha256": h("other registers")},
            (PREFIX + "registers hash", "Receipt registers_sha256 does not match the journal"),
        ),
        (
            {"quality": _report(True)},  # a different QA report (coverage 100 instead of 0)
            (PREFIX + "QA report", "Receipt quality_report_sha256 does not match the journal"),
        ),
        (
            {"quality": None},
            (PREFIX + "QA report", "Receipt quality_report_sha256 does not match the journal"),
        ),
        ({"journal": ()}, (PREFIX + "journal inputs",)),
    ],
)
def test_a_consistently_rewritten_export_is_refused(
    tmp_path: Path, update: dict[str, Any], issues: tuple[str, ...]
) -> None:
    forged = Envelope.model_validate(GENUINE.model_copy(update=update).model_dump())
    with pytest.raises(EnvelopeRefused) as refused:
        read_cp1_envelope(_store(), _export(forged, tmp_path / "x"))
    assert refused.value.issues == issues


def test_an_export_without_a_promoted_handoff_is_refused(tmp_path: Path) -> None:
    store = _store()
    store.read().attempts[0].steps.pop()  # the quality step is not in the journal
    with pytest.raises(EnvelopeRefused) as refused:
        read_cp1_envelope(store, _export(GENUINE, tmp_path / "x"))
    assert refused.value.issues == ("CP-1 head was not promoted through a verified handoff",)


@pytest.mark.parametrize("update", [{"step_id": "other"}, {"output_sha256": None}])
def test_a_step_that_is_not_the_retained_quality_output_is_refused(
    tmp_path: Path, update: dict[str, Any]
) -> None:
    store = _store()
    vars(store.read().attempts[0].steps[-1]).update(update)
    with pytest.raises(EnvelopeRefused) as refused:
        read_cp1_envelope(store, _export(GENUINE, tmp_path / "x"))
    assert refused.value.issues == ("CP-1 head was not promoted through a verified handoff",)


def test_a_genuine_export_is_refused_when_the_journal_holds_another_handoff(
    tmp_path: Path,
) -> None:
    """The binding runs both ways: the journal's handoff, not the export, is the record."""
    store = _store()
    other = HANDOFF.model_copy(update={"gap_limitations": (*GAPS, "A second gap")})
    outputs = {h("handoff"): other.model_dump_json()}
    store.step_output = outputs.__getitem__
    with pytest.raises(EnvelopeRefused) as refused:
        read_cp1_envelope(store, _export(GENUINE, tmp_path / "x"))
    assert refused.value.issues == (PREFIX + "gap limitations",)


def test_envelope_issues_are_bounded_like_every_other_issue_list() -> None:
    # S14-C03: a tampered 2,000,000-character Identity cell is quoted in its issue line; the line
    # is cut to execution.MAX_ISSUE_CHARS: 599 characters and "…" (600).
    from deploy_vii.envelope import envelope_issues

    run = Run(
        run_id="r1", issuer_id="i1", issuer_name="Acme", as_of=date(2026, 1, 1), case_kind="public"
    )
    module = Module(
        run_id="r1",
        issuer_id="i1",
        as_of=date(2026, 1, 1),
        module_id="CP-1",
        inputs=(Input(input_id="pack", sha256="a" * 64),),
    )
    markdown, sidecar = write_envelope(Envelope(run=run, module=module, registers_sha256="b" * 64))
    assert envelope_issues(markdown, sidecar) == ()
    big = markdown.replace("| issuer_name | Acme |", f"| issuer_name | {'X' * 2_000_000} |", 1)
    (issue,) = envelope_issues(big, sidecar)
    assert len(issue) == 600 and issue.endswith("X…")
    assert issue.startswith("Module Handoff / Identity: row 4 'Value' reads 'XXX")
