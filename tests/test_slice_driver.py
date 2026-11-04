import dataclasses
import json

import pytest
from test_model_testing_run import world, no_network  # noqa: F401

from deploy_workflow.model_testing import run as driver
from deploy_workflow.run_scopes import PUBLIC_S1A_SCOPE, PUBLIC_S1A_MODULES


def settings(world, **changes):
    base = world.settings(pathway="credit_snapshot", config="sol-medium", cap=driver.Decimal(10),
                          week_cap=driver.Decimal(60), delivery_scope=PUBLIC_S1A_SCOPE)
    return dataclasses.replace(base, **changes)


def test_slice_selects_one_case():
    assert driver.plan_runs("slice", pathway="credit_snapshot", config="sol-medium") == (
        ("tdg-credit-snapshot", "credit_snapshot", "sol-medium"),
    )
    with pytest.raises(driver.DriverError):
        driver.plan_runs("slice")


def test_scope_reaches_precheck_and_execution(world, monkeypatch):
    seen = []
    original = driver.check_arguments
    def check(**kwargs):
        seen.append(kwargs.get("delivery_scope"))
        return original(**kwargs)
    monkeypatch.setattr(driver, "check_arguments", check)
    result = driver.run_stage("slice", settings(world, through="CP-1"))
    assert seen == [PUBLIC_S1A_SCOPE]
    body = json.loads((result.outcomes[0].run_dir / "run.json").read_text())
    assert body["delivery_scope"] == PUBLIC_S1A_SCOPE
    assert body["requested_modules"] == list(PUBLIC_S1A_MODULES)


def test_exact_replay_preserves_invocation_identity(world):
    first = driver.run_stage("slice", settings(world)).outcomes[0]
    offline_root = world.root.parent / "offline"
    second = driver.run_stage("slice", settings(world, recorded_run=first.run_dir,
        runs_root=offline_root, out=offline_root / "second")).outcomes[0]
    assert second.run_id == first.run_id
    def digests(path):
        return [json.loads(line)["invocation_digest"]
                for line in (path / "calls.jsonl").read_text().splitlines()]
    assert digests(first.run_dir) == digests(second.run_dir)


def test_exact_replay_refuses_scope_change(world):
    first = driver.run_stage("slice", settings(world)).outcomes[0]
    offline_root = world.root.parent / "offline"
    with pytest.raises(driver.DriverError, match="scope differs"):
        driver.run_stage("slice", settings(world, recorded_run=first.run_dir,
            delivery_scope=None, runs_root=offline_root, out=offline_root / "different"))


def test_exact_replay_stays_outside_live_account_root(world):
    first = driver.run_stage("slice", settings(world)).outcomes[0]
    with pytest.raises(driver.DriverError, match="separate offline"):
        driver.run_stage("slice", settings(world, recorded_run=first.run_dir))
