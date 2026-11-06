"""S01 review: an envelope's section order is reported alongside any other issue.

A synthetic, empty CP-1 module (no issuer); expected issue texts are literal."""

from datetime import date

from deploy_vii.contracts import Input, Module, Run
from deploy_vii.envelope import Envelope, envelope_issues, write_envelope

LEAD_ISSUE = "Envelope title or lead differs from the canonical envelope"
ORDER_ISSUE = "Sections are not in the r14 order"


def _written() -> tuple[str, str]:
    day = date(2026, 1, 1)
    run = Run(run_id="r1", issuer_id="i1", issuer_name="Issuer", as_of=day, case_kind="synthetic")
    module = Module(
        run_id="r1",
        issuer_id="i1",
        as_of=day,
        module_id="CP-1",
        inputs=(Input(input_id="pack", sha256="a" * 64),),
    )
    return write_envelope(Envelope(run=run, module=module, registers_sha256="b" * 64))


def _swap_first_two_sections(markdown: str) -> str:
    head, first, second, *rest = markdown.split("\n## ")
    return "\n## ".join([head, second, first, *rest])


def test_canonical_envelope_has_no_issues() -> None:
    assert envelope_issues(*_written()) == ()


def test_reordered_sections_alone_are_reported() -> None:
    markdown, sidecar = _written()
    assert envelope_issues(_swap_first_two_sections(markdown), sidecar) == (ORDER_ISSUE,)


def test_reordered_sections_are_reported_beside_a_changed_lead() -> None:
    markdown, sidecar = _written()
    changed = _swap_first_two_sections(markdown).replace("Canonical r14", "Edited r14", 1)
    assert envelope_issues(changed, sidecar) == (LEAD_ISSUE, ORDER_ISSUE)


def test_a_missing_section_is_not_also_called_out_of_order() -> None:
    markdown, sidecar = _written()
    head, _first, *rest = markdown.split("\n## ")
    issues = envelope_issues("\n## ".join([head, *rest]), sidecar)
    assert issues[0] == "Missing section: Source Register"
    assert ORDER_ISSUE not in issues
