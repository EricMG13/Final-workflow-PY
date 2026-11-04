"""Named, bounded delivery scopes accepted by the public run entry points."""

from __future__ import annotations

from typing import Literal

from deploy_vii.contracts import PathwayId

DeliveryScopeId = Literal["s1a-credit-snapshot-public"]

PUBLIC_S1A_SCOPE: DeliveryScopeId = "s1a-credit-snapshot-public"
PUBLIC_S1A_MODULES: tuple[str, ...] = ("CP-1", "CP-MODEL", "CP-1A", "CP-2")


def modules_for_delivery_scope(
    scope: DeliveryScopeId | None, *, pathway: PathwayId, case_kind: str
) -> tuple[str, ...] | None:
    """Return the one frozen requested tuple, rejecting any incompatible invocation."""
    if scope is None:
        return None
    if scope != PUBLIC_S1A_SCOPE:
        raise ValueError("delivery_scope: unknown named scope")
    if pathway != "credit_snapshot":
        raise ValueError("delivery_scope: requires the credit_snapshot pathway")
    if case_kind != "public":
        raise ValueError("delivery_scope: requires a public case")
    return PUBLIC_S1A_MODULES
