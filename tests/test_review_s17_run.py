"""S17 review regressions for the model-testing driver and report: which run a report keeps,
stale scores, the Accounts ledger, --recorded-run, refusals that exit 2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_model_testing_report import call, meta, module, score

from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing import run as driver
from deploy_workflow.model_testing.pathway import PathwayScore
from deploy_workflow.model_testing.records import JournalError, RunMeta, read_run
from deploy_workflow.model_testing.report import Ledger, render_report

PILOT_1 = "pilot-sol-medium-earnings_update-1"
PILOT_2 = "pilot-sol-medium-earnings_update-2"
SLICE_3 = "slice-sol-medium-earnings_update-3"
REPAIR_1 = "repair-sol-medium-earnings_update-1"


# ---- which run a report keeps (adv S17 run.py:740, report.py:137) ------------------------


def test_slice_ranks_after_the_other_stages() -> None:
    pilot = score("sol-medium", PILOT_1, [module("CP-0", ["match"], True)])
    repair = score("sol-medium", REPAIR_1, [module("CP-0", ["match"], True)])
    slice_ = score("sol-medium", SLICE_3, [module("CP-0", ["mismatch"], False)])
    assert [s.run_id for s in driver._latest([pilot, slice_])] == [SLICE_3]
    assert [s.run_id for s in driver._latest([slice_, repair])] == [SLICE_3]


def test_a_newer_offline_run_never_replaces_a_live_one() -> None:
    live = score("sol-medium", PILOT_1, [module("CP-0", ["mismatch"], False)])
    offline = score("sol-medium", PILOT_2, [module("CP-0", ["match"], True)], mode="offline")
    assert [s.run_id for s in driver._latest([live, offline])] == [PILOT_1]
    assert [s.run_id for s in driver._latest([offline, live])] == [PILOT_1]
    # with no live run the offline one is kept, and its cells say so
    assert [s.run_id for s in driver._latest([offline])] == [PILOT_2]


def test_an_offline_cell_is_labelled() -> None:
    offline = score("sol-medium", PILOT_2, [module("CP-0", ["match"], True)], mode="offline")
    runs = [(meta(run_id=PILOT_2, mode="offline"), [call(run_id=PILOT_2, settled="3.00")])]
    text = render_report([offline], runs, [])
    assert "| CP-0 | OFFLINE PASS 1/1 · $3.00 computed · n/r tok · 10 s |" in text.splitlines()
    live = score("sol-medium", PILOT_1, [module("CP-0", ["match"], True)])
    live_runs = [(meta(run_id=PILOT_1), [call(run_id=PILOT_1, settled="3.00")])]
    text = render_report([live], live_runs, [])
    assert "| CP-0 | PASS 1/1 · $3.00 · n/r tok · 10 s |" in text.splitlines()


# ---- the Accounts ledger (adv S17 report.py:299) ------------------------------------------


def test_accounts_count_the_ledger_not_only_the_reported_runs() -> None:
    mine = [(meta(run_id="r-sol"), [call(run_id="r-sol", settled="1.00")])]
    sibling = [(meta(run_id="r-other"), [call(run_id="r-other", settled="100.00")])]
    scores = [score("sol-medium", "r-sol", [module("CP-0", ["match"], True)])]
    text = render_report(scores, mine, [], (), Ledger([*mine, *sibling]))
    assert "| openai | $101.00 | $117.00 | $16.00 |" in text.splitlines()
    alone = render_report(scores, mine, [])
    assert "| openai | $1.00 | $117.00 | $116.00 |" in alone.splitlines()


# ---- run folders on disk, for report_out --------------------------------------------------


def _folder(parent: Path, run_meta: RunMeta, calls: tuple[CallRecord, ...] = ()) -> Path:
    folder = parent / run_meta.run_id
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(run_meta.model_dump_json(), encoding="utf-8")
    if calls:
        lines = "".join(c.model_dump_json() + "\n" for c in calls)
        (folder / "calls.jsonl").write_text(lines, encoding="utf-8")
    return folder


def _scores(out: Path, *scores: PathwayScore) -> None:
    body = {
        "schema_version": "model-testing-scores/1",
        "scores": [s.model_dump(mode="json") for s in scores],
    }
    (out / driver.SCORES_FILE).write_text(json.dumps(body), encoding="utf-8")


def _settings(root: Path, **changes: Any) -> driver.Settings:
    base: dict[str, Any] = {
        "out": root / "out",
        "cases": root / "no-cases",
        "corpus": root / "no-corpus",
        "runs_root": root,
    }
    return driver.Settings(**{**base, **changes})


def _offline(run_id: str, stopped: str | None = None) -> RunMeta:
    return meta(run_id=run_id, mode="offline", stopped=stopped)


def _offline_score(run_id: str, stopped: str | None = None) -> PathwayScore:
    return score("sol-medium", run_id, [module("CP-0", ["match"], True)], stopped, "offline")


def test_report_refuses_scores_missing_a_newer_run(tmp_path: Path) -> None:
    out = tmp_path / "out"
    _folder(out, _offline(PILOT_1))
    _folder(out, _offline(PILOT_2))
    _scores(out, _offline_score(PILOT_1))
    with pytest.raises(driver.DriverError, match=f"run {PILOT_2}\\); run the score command"):
        driver.report_out(_settings(tmp_path))


@pytest.mark.parametrize(
    ("on_disk", "scored"),
    [
        (_offline(PILOT_1, stopped="cap reached"), _offline_score(PILOT_1)),
        (meta(run_id=PILOT_1), _offline_score(PILOT_1)),  # the run is live, the score offline
    ],
)
def test_report_refuses_a_score_whose_outcome_or_mode_changed(
    tmp_path: Path, on_disk: RunMeta, scored: PathwayScore
) -> None:
    out = tmp_path / "out"
    _folder(out, on_disk)
    _scores(out, scored)
    with pytest.raises(driver.DriverError, match=f"run {PILOT_1}\\); run the score command"):
        driver.report_out(_settings(tmp_path))


def test_report_out_keeps_the_live_run_and_counts_the_runs_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "out"
    _folder(out, meta(run_id=PILOT_1))  # live, no calls: no reservation markers needed
    _folder(out, _offline(PILOT_2))
    _folder(tmp_path / "sibling", _offline("pilot-sol-high-earnings_update-1"))
    live = score("sol-medium", PILOT_1, [module("CP-0", ["mismatch"], False)])
    _scores(out, live, _offline_score(PILOT_2))
    seen: dict[str, Any] = {}
    real = driver.render_report

    def spy(*args: Any) -> str:
        seen["scores"] = [s.run_id for s in args[0]]
        seen["ledger"] = sorted(m.run_id for m, _ in args[4].runs)
        return real(*args)

    monkeypatch.setattr(driver, "render_report", spy)
    text = driver.report_out(_settings(tmp_path)).read_text(encoding="utf-8")
    assert seen["scores"] == [PILOT_1]
    assert seen["ledger"] == ["pilot-sol-high-earnings_update-1", PILOT_1, PILOT_2]
    assert "| CP-0 | FAIL 0/1 · $0.00 · n/r tok · n/r |" in text.splitlines()


# ---- refusals exit 2 with a message (cr S17 run.py:962, run.py:848) -----------------------


def test_a_report_data_error_exits_2_with_a_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    backwards = call(run_id=PILOT_1, seconds=-5, settled="0.10")  # finished before it started
    _folder(out, _offline(PILOT_1), (backwards,))
    _scores(out, _offline_score(PILOT_1))
    argv = ["report", "--out", str(out), "--runs-root", str(tmp_path)]
    assert driver.main(argv) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: report: run pilot-sol-medium-earnings_update-1 module CP-0")
    assert "finished before started" in err and "Traceback" not in err


def test_an_unknown_config_in_run_json_is_a_journal_refusal(tmp_path: Path) -> None:
    body = json.loads(_offline(PILOT_1).model_dump_json())
    body["config_id"] = "cp-os"
    folder = tmp_path / PILOT_1
    folder.mkdir()
    (folder / "run.json").write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(JournalError, match="config_id is not a model-testing configuration"):
        read_run(folder)


@pytest.mark.parametrize("flag", ["--cap", "--week-cap"])
def test_a_non_decimal_cap_is_a_usage_error(
    tmp_path: Path, flag: str, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["slice", "--out", str(tmp_path / "out"), flag, "abc"]
    assert driver.main(argv) == 2
    err = capsys.readouterr().err
    assert "'abc' is not a decimal amount" in err and "Traceback" not in err


# ---- --recorded-run (cr S17 run.py:501) ---------------------------------------------------


def _retained(tmp_path: Path, config_id: str = "sol-medium") -> Path:
    retained = meta(config_id, "slice-x-1", "offline").model_copy(
        update={"pathway": "credit_snapshot", "case_id": "tdg-credit-snapshot"}
    )
    return _folder(tmp_path / "retained", retained)


@pytest.mark.parametrize("stage", ["pilot", "repair", "comparison"])
def test_recorded_run_is_refused_outside_the_slice_stage(
    tmp_path: Path, stage: driver.Stage
) -> None:
    root = tmp_path / "root"
    settings = _settings(root, recordings=tmp_path / "rec", recorded_run=_retained(tmp_path))
    with pytest.raises(driver.DriverError, match="only the slice stage takes it"):
        driver.run_stage(stage, settings)
    assert not (root / driver.LOCK_FILE).exists()  # refused before the lock and any run
    assert not (root / "out").exists()


def test_recorded_run_identity_is_checked_before_the_first_run(tmp_path: Path) -> None:
    root = tmp_path / "root"
    settings = _settings(
        root,
        recordings=tmp_path / "rec",
        recorded_run=_retained(tmp_path, config_id="sol-high"),
        pathway="credit_snapshot",
        config="sol-medium",
    )
    with pytest.raises(driver.DriverError, match="case/config/pathway/scope differs"):
        driver.run_stage("slice", settings)
    assert not (root / driver.LOCK_FILE).exists()
