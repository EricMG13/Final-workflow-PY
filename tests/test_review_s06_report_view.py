"""S06 review fixes in ``deploy_vii.report_view``: honest-state blocks keep their scope tag and
pin; a liquidity record's spelling is checked against its fact cell."""

import dataclasses
from typing import Any

import chart_wiring_c as wiring
import pytest
import test_connect_cp2d as tc

from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.render import empty_view
from deploy_vii.report_view import build, pathways
from deploy_workflow import liquidity_series


def _key_findings(case_kind: str) -> Any:
    run = tc.PACK.run.model_copy(update={"pathway": "credit_snapshot", "case_kind": case_kind})
    pathway = next(item for item in pathways() if item.id == "credit_snapshot")
    report = build(empty_view(run), pathway, SHIPPED_MAPS)
    return next(block for block in report.blocks if block.block_id == "key-findings")


def test_a_not_run_synthetic_block_keeps_its_tag_and_pin() -> None:
    block = _key_findings("synthetic")
    assert (block.state, block.tags, block.pinned) == ("not_run", ("Synthetic",), True)
    assert block.full_analysis_route is None  # an empty block links nowhere


def test_a_public_case_block_carries_no_synthetic_tag() -> None:
    block = _key_findings("public")
    assert (block.state, block.tags, block.pinned) == ("not_run", (), True)


def test_a_liquidity_record_spelled_unlike_its_fact_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = liquidity_series.cp2d_chart_series

    def drifted(*args: Any, **kwargs: Any) -> Any:
        records = real(*args, **kwargs)
        first = records[0]
        index = next(i for i, p in enumerate(first.points) if p.value is not None)
        points = list(first.points)
        points[index] = dataclasses.replace(points[index], shown=points[index].shown + ".0")
        return (dataclasses.replace(first, points=tuple(points)), *records[1:])

    view = wiring.cp2d_view("long_horizon")
    wiring.block_of(wiring.report_of(view), "liquidity-runway")  # the record agrees as shipped
    monkeypatch.setattr(liquidity_series, "cp2d_chart_series", drifted)
    with pytest.raises(ValueError, match=r"CP-2D chart spells T2E\.\S+ '.*\.0', its fact"):
        wiring.report_of(view)
