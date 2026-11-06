"""S05 review: CP-4's inherited CP-1 gaps (T4F.5, CONTEXT `inherited_gaps`) keep what a
blocked CP-1 itself inherited, as they do for a settled one."""

from datetime import date
from typing import Any

from deploy_vii.contracts import Module, Run
from deploy_vii.cp4_legal import cp4_upstream
from deploy_vii.preparation import PreparedPack

_RUN = Run(
    run_id="r", issuer_id="i", issuer_name="Issuer", as_of=date(2025, 1, 1), case_kind="synthetic"
)
_PACK = PreparedPack(run=_RUN, sources=())


def _module(module_id: str, status: Any) -> Module:
    return Module(
        run_id="r",
        issuer_id="i",
        as_of=date(2025, 1, 1),
        module_id=module_id,
        status=status,
        limitations=("Statements unreadable",) if module_id == "CP-1" else (),
        inherited_limitations=("Upstream CP-0: source S2 unreadable",)
        if module_id == "CP-1"
        else (),
    )


def test_blocked_cp1_keeps_its_inherited_limitations() -> None:
    upstream = cp4_upstream(_PACK, _module("CP-0", "accepted"), _module("CP-1", "blocked"))
    assert upstream.cp1_gaps == (
        "Upstream CP-1 blocked: Statements unreadable",
        "Upstream CP-0: source S2 unreadable",
    )


def test_settled_cp1_gaps_are_unchanged() -> None:
    upstream = cp4_upstream(_PACK, _module("CP-0", "accepted"), _module("CP-1", "restricted"))
    assert upstream.cp1_gaps == (
        "Statements unreadable",
        "Upstream CP-0: source S2 unreadable",
    )
