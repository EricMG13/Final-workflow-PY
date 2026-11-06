"""Run driver (Task 11): plans the (case, pathway, config) runs of a stage, drives O2
``run_pathway`` for each, scores the run directories with ``score_run`` and writes the report.

The framework never writes or edits ``run.json`` (C4): ``run_pathway`` creates it. Offline is the
default (``recorded_adapter``); a live run passes the ruling to ``live_adapter``, which owns the
R2 gate. The driver's own check of the ruling path is a pre-check for a clear message only.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterator, Sequence
from collections.abc import Mapping as MappingABC
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_UP, Decimal, InvalidOperation, localcontext
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from pydantic import ValidationError

from deploy_vii.contracts import PATHWAY_MODULES, Contract, PathwayId
from deploy_workflow.context import ContextRefused
from deploy_workflow.html_text import UndecodableHtml
from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model.adapter import (
    LivePauseInForce,
    ModelAdapter,
    RecordingError,
    live_adapter,
    recorded_adapter,
)
from deploy_workflow.model.record import CallRecord, export_recording
from deploy_workflow.model.redact import KEY_PATTERN, Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.model_testing.budget import (
    AccountExhausted,
    BudgetError,
    Settlement,
    account_spend,
    load_settlements,
    require_budget,
)
from deploy_workflow.model_testing.cases import CaseError, GoldenCase, load_case
from deploy_workflow.model_testing.configs import (
    ACCOUNTS,
    CASES,
    CONFIGS,
    OPUS_PATHWAYS,
    PILOT_PATHWAY,
)
from deploy_workflow.model_testing.faults import read_faults
from deploy_workflow.model_testing.mapping import Mapping, MappingError, load_mapping
from deploy_workflow.model_testing.pathway import PathwayScore, receipt_refusals, score_run
from deploy_workflow.model_testing.records import (
    JournalError,
    RunMeta,
    read_run,
    validation_summary,
)
from deploy_workflow.model_testing.report import (
    _WIDE,
    Ledger,
    ReportInputError,
    _cell_text,
    _money,
    render_report,
)
from deploy_workflow.model_testing.slice_budget import positive_money, slice_cap
from deploy_workflow.run_inputs import (
    HTML_MEDIA,
    CaseSource,
    RunInputError,
    RunOutcome,
    check_arguments,
)
from deploy_workflow.run_pathway import check_rerun_plan, run_pathway
from deploy_workflow.run_scopes import PUBLIC_S1A_SCOPE, DeliveryScopeId

Stage = Literal["pilot", "repair", "comparison", "slice"]
PlannedRun = tuple[str, PathwayId, str]

SETTLEMENTS_FILE = "settlements.json"
SCORES_FILE = "scores.json"
REPORT_FILE = "report.md"
FAULTS_FILE = "faults.jsonl"
EXHAUSTED_FILE = "exhausted.json"
DEFAULT_RUNS_ROOT = Path("artifacts/model-testing")
LOCK_FILE = ".driver.lock"

# Per-run amount a live run must be able to cover before any run has been measured. Basis: spec
# 7.2 (docs/superpowers/specs/2026-10-31-model-testing-design.md, section 7.2 "Budget"), each
# total divided by its run count and rounded up to the cent:
#   sol-medium   67.68 for about two rounds of six pathways (12 runs)     -> 5.64
#   sol-high     48.88 for six pathways                                    -> 8.1467 -> 8.15
#   opus-medium  125.72 for the five Opus pathways                         -> 25.144 -> 25.15
#   deepseek-max 9.97 for one round of six, the DeepSeek line of the budget plan the user
#                adopted ("Adopt it", 2026-10-31; work/model-testing/HANDOFF.md) -> 1.6617 -> 1.67
# deepseek-max is not planned: user, 2026-11-02, "drop deepseek from testing".
# Once a settled live run of the configuration exists, its measured cost replaces the estimate.
RUN_ESTIMATE_USD: MappingABC[str, Decimal] = MappingProxyType(
    {
        "sol-medium": Decimal("5.64"),
        "sol-high": Decimal("8.15"),
        "opus-medium": Decimal("25.15"),
        "deepseek-max": Decimal("1.67"),
    }
)
# Spec 7.2: all six Opus pathways are estimated at 154.65 and the five at 125.72, so
# distressed_restructuring is 28.93; it runs only if the measured Opus spend leaves room.
OPUS_FIVE_ESTIMATE_USD = Decimal("125.72")
DISTRESSED_OPUS_ESTIMATE_USD = Decimal("28.93")
DISTRESSED_PATHWAY: PathwayId = "distressed_restructuring"
OPUS_CONFIG = "opus-medium"

class DriverError(ValueError):
    """A refused argument or input of the driver; the message names it."""


def plan_runs(
    stage: Stage, *, pathway: PathwayId | None = None, config: str | None = None
) -> tuple[PlannedRun, ...]:
    """The (case_id, pathway, config_id) runs of a stage, one configuration at a time so a
    configuration that runs out of credit loses only its own tail."""
    if stage == "slice":
        if (
            pathway is None
            or config is None
            or pathway not in CASES
            or config not in CONFIGS
            or not CONFIGS[config].roles
        ):
            raise DriverError("slice requires a supported --pathway and --config")
        return ((CASES[pathway], pathway, config),)
    if stage == "pilot":
        return tuple(
            (CASES[PILOT_PATHWAY], PILOT_PATHWAY, c.config_id) for c in CONFIGS.values() if c.roles
        )
    if stage == "repair":
        repair = [c.config_id for c in CONFIGS.values() if "repair" in c.roles]
        return tuple(
            (case, pathway, config) for config in repair for pathway, case in CASES.items()
        )
    high = tuple((case, pathway, "sol-high") for pathway, case in CASES.items())
    opus = tuple((CASES[pathway], pathway, OPUS_CONFIG) for pathway in OPUS_PATHWAYS)
    return high + opus  # comparison


@dataclass(frozen=True)
class Settings:
    out: Path
    cases: Path
    corpus: Path
    recordings: Path | None = None
    live: bool = False
    ruling: Path | None = None
    runs_root: Path = DEFAULT_RUNS_ROOT
    through: str | None = None
    replay_from: Path | None = None
    repaired: frozenset[str] = frozenset()
    pathway: PathwayId | None = None
    config: str | None = None
    cap: Decimal | None = None
    week_cap: Decimal | None = None
    delivery_scope: DeliveryScopeId | None = None
    recorded_run: Path | None = None


@dataclass(frozen=True)
class CaseInputs:
    case: GoldenCase
    mapping: Mapping
    sources: tuple[CaseSource, ...]


@dataclass(frozen=True)
class StageResult:
    outcomes: tuple[RunOutcome, ...]
    stopped: MappingABC[str, str]  # config (or config and pathway) -> why its runs stopped


# ------------------------------------------------------------------ arguments and inputs


def _precheck_ruling(ruling: Path) -> None:
    """A clear message for a ruling that is missing or outside docs/rulings. Not the gate:
    ``live_adapter`` runs the R2 gate on every construction."""
    root = adapter_module.LIVE_RULINGS_ROOT.resolve()
    try:
        resolved = ruling.resolve(strict=True)
    except OSError:
        raise DriverError(f"ruling {ruling} does not exist") from None
    if not resolved.is_file() or not resolved.is_relative_to(root):
        raise DriverError(f"ruling {ruling} must be a file under docs/rulings/")


def check_out_inside_root(settings: Settings) -> None:
    if not settings.out.resolve().is_relative_to(settings.runs_root.resolve()):
        raise DriverError(
            f"--out {settings.out} is outside --runs-root {settings.runs_root}: spend stored "
            "outside the runs root is not counted against the account caps"
        )


def check_settings(settings: Settings) -> None:
    for name, value in (("cap", settings.cap), ("week cap", settings.week_cap)):
        if value is not None:
            positive_money(value, name)
    if settings.recorded_run is not None:
        if settings.live or settings.replay_from is not None:
            raise DriverError("--recorded-run is an exact offline replay, not a live repair")
        if settings.recorded_run.resolve().is_relative_to(settings.runs_root.resolve()):
            raise DriverError("exact replay needs a separate offline --runs-root")
    if settings.live and not settings.runs_root.is_absolute():
        raise DriverError(
            "--live needs an explicit absolute --runs-root: the default is relative, so each "
            "worktree would keep its own ledger and miss spend recorded elsewhere"
        )
    check_out_inside_root(settings)
    if (settings.replay_from is None) != (not settings.repaired):
        raise DriverError("--replay-from and --repaired go together: give both or neither")
    if settings.live:
        if settings.ruling is None:
            raise DriverError("--live needs --ruling docs/rulings/<file>.md")
        if settings.recordings is not None:
            raise DriverError("--recordings is for offline runs; it cannot be combined with --live")
        _precheck_ruling(settings.ruling)
    else:
        if settings.ruling is not None:
            raise DriverError("--ruling is for --live runs only")
        if settings.recordings is None:
            raise DriverError(
                "offline runs need --recordings DIR (each configuration reads DIR/<config_id>/)"
            )


def _media_type(source_id: str, path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".htm", ".html"):
        return HTML_MEDIA
    if suffix == ".pdf":
        return "application/pdf"
    raise DriverError(f"source {source_id}: unsupported file type {suffix!r}")


def _golden_sources(case_id: str, golden: object, corpus: Path) -> tuple[CaseSource, ...]:
    if not isinstance(golden, dict) or not isinstance(golden.get("sources"), list):
        raise DriverError(f"{case_id}: module_golden.json has no sources list")
    root = corpus.resolve()
    sources: list[CaseSource] = []
    for item in golden["sources"]:
        try:
            source_id, relative, expected = item["source_id"], item["file"], item["sha256"]
        except (KeyError, TypeError):
            raise DriverError(f"{case_id}: a source lacks source_id, file or sha256") from None
        path = (root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root):
            raise DriverError(f"{case_id}: source {source_id}: file must lie inside the corpus")
        if not path.is_file():
            raise DriverError(f"{case_id}: source {source_id}: file is missing from the corpus")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise DriverError(f"{case_id}: source {source_id}: sha256 differs from the golden's")
        sources.append(CaseSource(source_id, path, _media_type(source_id, path)))
    return tuple(sources)


def load_inputs(case_id: str, cases: Path, corpus: Path) -> CaseInputs:
    """The case, its mapping and its corpus sources, every source checked against the golden's
    sha256 before anything runs. The context is the one the golden names."""
    case_dir = cases / case_id
    golden_path = case_dir / "module_golden.json"
    if not golden_path.is_file():
        raise DriverError(f"{case_id}: no module_golden.json under {cases}")
    try:
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
    except ValueError:
        raise DriverError(f"{case_id}: module_golden.json is not valid JSON") from None
    sources = _golden_sources(case_id, golden, corpus)
    case = load_case(case_dir, corpus)
    return CaseInputs(case, load_mapping(case_dir / "mapping.json", case), sources)


# ------------------------------------------------------------------ run folders and budget


def _run_dirs(root: Path) -> list[Path]:
    """Every run directory under ``root``: one that holds ``sources/`` (``run_pathway`` stages
    it first) or ``run.json``. A run directory is not searched further."""
    found: list[Path] = []
    pending = [root] if root.is_dir() else []
    while pending:
        for child in sorted(
            p
            for p in pending.pop().iterdir()
            if p.is_dir() or (p.is_symlink() and not p.exists())  # a dangling link is refused
        ):
            if child.is_symlink():
                raise DriverError(
                    f"{child} is a symbolic link: its runs would go uncounted; "
                    "move the folder in or remove the link"
                )
            if (child / "run.json").is_file() or (child / "sources").is_dir():
                found.append(child)
            else:
                pending.append(child)
    return sorted(found)


def _read_all(root: Path) -> list[tuple[Path, RunMeta, tuple[CallRecord, ...]]]:
    """Every run directory under ``root``. One with ``sources/`` but no ``run.json`` is a crashed
    run whose spend cannot be counted (ledger ruling 2026-11-01): the command stops."""
    found: list[tuple[Path, RunMeta, tuple[CallRecord, ...]]] = []
    for folder in _run_dirs(root):
        if not (folder / "run.json").is_file():
            raise DriverError(
                f"run folder {folder.name} has no run.json yet (in flight or crashed): its "
                "spend cannot be counted; wait for it, resume it or move it away"
            )
        meta, records = read_run(folder)
        found.append((folder, meta, records))
    return found


def load_runs(root: Path) -> list[tuple[RunMeta, tuple[CallRecord, ...]]]:
    return [(meta, records) for _, meta, records in _read_all(root)]


def load_all_settlements(root: Path, out: Path) -> tuple[Settlement, ...]:
    """The settlements file of ``out`` and of every folder holding a run under ``root``."""
    folders = {out.resolve()} | {d.parent.resolve() for d in _run_dirs(root)}
    found: list[Settlement] = []
    for folder in sorted(folders):
        found += load_settlements(folder / SETTLEMENTS_FILE)
    return tuple(found)


def _next_number(root: Path, prefix: str) -> int:
    """The next free integer for run ids ``<prefix>-<n>`` across every run directory."""
    used = [
        int(m.group(1))
        for folder in _run_dirs(root)
        if (m := re.fullmatch(re.escape(prefix) + r"-(\d+)", folder.name))
    ]
    return max(used, default=0) + 1


def _run_spend(
    meta: RunMeta, records: tuple[CallRecord, ...], settlements: Sequence[Settlement]
) -> Decimal:
    mine = [s for s in settlements if s.run_id == meta.run_id]
    return account_spend([(meta, records)], CONFIGS[meta.config_id].provider, mine)


def needed_usd(
    config_id: str,
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
    settlements: Sequence[Settlement] = (),
) -> Decimal:
    """What one more run of the configuration needs: the highest measured spend of its settled
    live runs, or the spec 7.2 estimate before there is one."""
    measured = [
        _run_spend(meta, records, settlements)
        for meta, records in runs
        if meta.config_id == config_id and meta.mode == "live" and meta.outcome == "settled"
    ]
    return max(measured) if measured else RUN_ESTIMATE_USD[config_id]


def distressed_opus_estimate(
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
    settlements: Sequence[Settlement] = (),
) -> Decimal | None:
    """The spec 7.2 estimate of distressed_restructuring on Opus, scaled by how the five Opus
    pathways measured against their 125.72 estimate; ``None`` until all five have settled.
    Each pathway counts once, at the highest spend of its settled live runs (the rule
    ``needed_usd`` uses); an offline run spends nothing and does not count."""
    best: dict[str, Decimal] = {}
    for meta, records in runs:
        if (
            meta.config_id == OPUS_CONFIG
            and meta.mode == "live"
            and meta.outcome == "settled"
            and meta.pathway in OPUS_PATHWAYS
        ):
            spend = _run_spend(meta, records, settlements)
            best[meta.pathway] = max(best.get(meta.pathway, spend), spend)
    if set(best) != set(OPUS_PATHWAYS):
        return None
    with localcontext(_WIDE):
        spent = sum(best.values(), Decimal(0))
        scaled = DISTRESSED_OPUS_ESTIMATE_USD * spent / OPUS_FIVE_ESTIMATE_USD
        return scaled.quantize(Decimal("0.01"), rounding=ROUND_UP)


# ------------------------------------------------------------------ driving


class _Exhausted(Contract):
    schema_version: Literal["driver-exhausted/1"]
    stopped: dict[str, str]


def _invalid(name: str, error: ValidationError) -> DriverError:
    return DriverError(f"{name}: invalid: {validation_summary(error)}")


def _read_exhausted(out: Path) -> dict[str, str]:
    path = out / EXHAUSTED_FILE
    if not path.is_file():
        return {}
    try:
        return dict(_Exhausted.model_validate_json(path.read_bytes()).stopped)
    except ValidationError as error:
        raise _invalid(EXHAUSTED_FILE, error) from None


def check_budget(
    config_id: str,
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
    needed: Decimal,
    settlements: Sequence[Settlement],
) -> Decimal:
    """The cap for one more run, or ``AccountExhausted`` (an unknown charge, too little credit,
    none left)."""
    cap = require_budget(config_id, runs, needed, settlements)
    if cap <= 0:
        raise AccountExhausted(f"{config_id}: no usable credit left")
    return cap


def current_stops(
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]], settlements: Sequence[Settlement]
) -> dict[str, str]:
    """The configurations that cannot run now, derived from the runs and settlements as they are."""
    stops: dict[str, str] = {}
    for config_id, config in CONFIGS.items():
        if config.provider not in ACCOUNTS:
            continue  # Copilot holds no model-testing account and no stage plans it
        try:
            check_budget(config_id, runs, Decimal(0), settlements)
        except AccountExhausted as error:
            stops[config_id] = str(error)
    return stops


def _spec(config_id: str) -> ModelSpec:
    config = CONFIGS[config_id]
    return ModelSpec(config.config_id, config.provider, config.model, config.effort)


def _adapter(settings: Settings, spec: ModelSpec) -> ModelAdapter:
    """``check_settings`` guarantees a ruling exactly when the run is live."""
    if settings.ruling is not None:
        return live_adapter(spec, settings.ruling)
    if settings.recordings is not None:
        return recorded_adapter(spec, settings.recordings / spec.config_id)
    raise DriverError("neither a ruling nor recordings were given")


@dataclass
class _Driver:
    stage: Stage
    settings: Settings
    inputs: dict[str, CaseInputs]
    adapters: dict[str, ModelAdapter]
    settlements: tuple[Settlement, ...]
    runs: list[tuple[RunMeta, tuple[CallRecord, ...]]]
    recorded: tuple[str, Decimal] | None = None  # an exact replay's run_id and cap
    stopped: dict[str, str] = field(default_factory=dict)
    outcomes: list[RunOutcome] = field(default_factory=list)

    def run(
        self,
        case_id: str,
        pathway: PathwayId,
        config_id: str,
        needed: Decimal | None = None,
        stop_key: str | None = None,
    ) -> None:
        key = config_id if stop_key is None else stop_key
        if key in self.stopped:
            return
        if needed is None:
            live = self.settings.live
            needed = needed_usd(config_id, self.runs, self.settlements) if live else Decimal(0)
        try:
            cap = check_budget(config_id, self.runs, Decimal(0), self.settlements)
            if self.settings.live and self.settings.week_cap is not None:
                cap = slice_cap(
                    config_id, self.runs, self.settlements,
                    cap=self.settings.cap or cap, week_cap=self.settings.week_cap,
                    now=datetime.now(UTC),
                )
            elif self.settings.cap is not None:
                cap = min(cap, self.settings.cap)
            if cap < needed:
                raise AccountExhausted(f"cap {cap}: estimated run requires {needed}")
        except AccountExhausted as error:
            self.stopped[key] = str(error)
            return
        root = self.settings.runs_root
        prefix = f"{self.stage}-{config_id}-{pathway}"
        run_id = f"{prefix}-{_next_number(root, prefix)}"
        found = self.inputs[case_id]
        if self.recorded is not None:
            run_id, cap = self.recorded
        self.settings.out.mkdir(parents=True, exist_ok=True)
        self.outcomes.append(
            run_pathway(
                case_id=case_id,
                sources=found.sources,
                context=found.case.context_path,
                pathway=pathway,
                model=_spec(config_id),
                adapter=self.adapters[config_id],
                cap_usd=cap,
                run_dir=self.settings.out / run_id,
                run_id=run_id,
                through=self.settings.through,
                replay_from=self.settings.replay_from,
                repaired=self.settings.repaired,
                delivery_scope=self.settings.delivery_scope,
            )
        )
        self.runs = load_runs(root)

    def distressed_on_opus(self) -> None:
        """After the five Opus pathways: distressed_restructuring only if the account's cap
        covers its measured estimate."""
        key = f"{OPUS_CONFIG} ({DISTRESSED_PATHWAY})"
        estimate = distressed_opus_estimate(self.runs, self.settlements)
        if estimate is None:
            self.stopped[key] = "skipped: the five Opus pathways have not all settled"
        elif OPUS_CONFIG in self.stopped:
            self.stopped[key] = f"skipped: {OPUS_CONFIG} is stopped"
        else:
            self.run(
                CASES[DISTRESSED_PATHWAY],
                DISTRESSED_PATHWAY,
                OPUS_CONFIG,
                needed=estimate,
                stop_key=key,
            )


def _record_stopped(out: Path, stopped: MappingABC[str, str]) -> None:
    """Rewrite ``exhausted.json`` from this command's stops; none removes it."""
    path = out / EXHAUSTED_FILE
    if not stopped:
        path.unlink(missing_ok=True)
        return
    body = _Exhausted(schema_version="driver-exhausted/1", stopped=dict(stopped))
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(body.model_dump_json(indent=2) + "\n", encoding="utf-8")


@contextmanager
def _root_lock(root: Path) -> Iterator[None]:
    """An exclusive lock on the runs root, held from before the first budget and run_id read until
    the last run returns. A second stage command fails at once rather than waiting."""
    # ponytail: one lock per runs-root; per-config locks if parallel stages are ever needed
    try:
        root.mkdir(parents=True, exist_ok=True)
        handle = (root / LOCK_FILE).open("a")
    except OSError as exc:
        raise DriverError(
            f"cannot open the lock file {root / LOCK_FILE}: {exc.strerror or exc}"
        ) from None
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DriverError(
                f"another stage command holds {root / LOCK_FILE}; wait for it to finish"
            ) from None
        yield


def check_reruns(
    stage: Stage,
    settings: Settings,
    inputs: MappingABC[str, CaseInputs],
    adapters: MappingABC[str, ModelAdapter],
) -> None:
    """Before the first run, check ``--through`` and ``--replay-from`` against every pathway the
    stage will run, with the checks ``run_pathway`` makes (so the two cannot disagree), and refuse
    a replay plan that would run live a module the repaired set does not name or follow: that
    module is frozen by the request, and a live one is spend nobody asked for. Writes nothing."""
    if settings.through is None and settings.replay_from is None:
        return
    runs = list(plan_runs(stage, pathway=settings.pathway, config=settings.config))
    if stage == "comparison":
        runs.append((CASES[DISTRESSED_PATHWAY], DISTRESSED_PATHWAY, OPUS_CONFIG))
    for case_id, pathway, config_id in runs:
        found = inputs[case_id]
        run_id = f"{stage}-{config_id}-{pathway}-precheck"
        checked = check_arguments(
            case_id=case_id,
            sources=found.sources,
            context=found.case.context_path,
            pathway=pathway,
            model=_spec(config_id),
            adapter=adapters[config_id],
            cap_usd=Decimal(1),  # any positive cap: this run is never made
            run_dir=settings.out / run_id,
            run_id=run_id,
            resume=True,  # skips the new-directory check; nothing is created
            delivery_scope=settings.delivery_scope,
        )
        replay = check_rerun_plan(
            checked,
            settings.out / run_id,
            settings.through,
            settings.replay_from,
            settings.repaired,
        )
        if replay is not None and replay.unreplayable:
            named = "; ".join(f"{module} ({why})" for module, why in replay.unreplayable)
            raise DriverError(
                f"the {pathway} rerun would run live a module the earlier run cannot replay and "
                f"--repaired does not name: {named}"
            )


def _recorded_identity(
    stage: Stage, settings: Settings, planned: Sequence[PlannedRun]
) -> tuple[str, Decimal] | None:
    """An exact replay's run_id and cap, checked before any run: ``--recorded-run`` replays one
    retained run, so only the one-run slice stage takes it, and the retained run must be the
    planned run (case, pathway, configuration and delivery scope)."""
    if settings.recorded_run is None:
        return None
    if stage != "slice" or len(planned) != 1:
        raise DriverError("--recorded-run replays one retained run: only the slice stage takes it")
    meta, _ = read_run(settings.recorded_run)
    case_id, pathway, config_id = planned[0]
    if (meta.case_id, meta.pathway, meta.config_id, meta.delivery_scope) != (
        case_id,
        pathway,
        config_id,
        settings.delivery_scope,
    ):
        raise DriverError("recorded run case/config/pathway/scope differs from this request")
    return meta.run_id, meta.cap_usd


def run_stage(stage: Stage, settings: Settings) -> StageResult:
    """Run every planned run of a stage. Everything that can be refused is refused before the
    first run: the arguments, a crashed run folder, the settlements, the cases and their sources,
    each configuration's adapter (the live gate included), and every pathway's ``--through`` and
    rerun plan."""
    check_settings(settings)
    planned = plan_runs(stage, pathway=settings.pathway, config=settings.config)
    recorded = _recorded_identity(stage, settings, planned)
    case_ids = {case for case, _, _ in planned}
    if stage == "comparison":
        case_ids.add(CASES[DISTRESSED_PATHWAY])
    inputs = {c: load_inputs(c, settings.cases, settings.corpus) for c in sorted(case_ids)}
    adapters: dict[str, ModelAdapter] = {}
    for _, _, config_id in planned:
        if config_id not in adapters:
            adapters[config_id] = _adapter(settings, _spec(config_id))
    check_reruns(stage, settings, inputs, adapters)
    with _root_lock(settings.runs_root):
        runs = load_runs(settings.runs_root)
        settlements = load_all_settlements(settings.runs_root, settings.out)
        driver = _Driver(stage, settings, inputs, adapters, settlements, runs, recorded)
        for case_id, pathway, config_id in planned:
            driver.run(case_id, pathway, config_id)
        if stage == "comparison":
            driver.distressed_on_opus()
        _record_stopped(settings.out, driver.stopped)
    return StageResult(tuple(driver.outcomes), MappingProxyType(dict(driver.stopped)))


# ------------------------------------------------------------------ scoring and report


class _Scores(Contract):
    schema_version: Literal["model-testing-scores/1"]
    scores: tuple[PathwayScore, ...]


def _check_refusal_names(meta: RunMeta, refusals: MappingABC[str, tuple[str, ...]]) -> None:
    """A refusal naming a module or input outside the pathway preset is refused, by name."""
    preset = set(PATHWAY_MODULES[meta.pathway])
    for module_id, inputs in refusals.items():
        for name in (module_id, *inputs):
            if name not in preset:
                raise DriverError(
                    f"run {meta.run_id}: the receipt's refusal of {module_id} names {name}, "
                    f"outside the {meta.pathway} preset"
                )


def score_out(settings: Settings) -> Path:
    """Score every run folder under ``out`` into ``scores.json`` (reads only the run folders)."""
    check_out_inside_root(settings)
    found = _read_all(settings.out)
    if not found:
        raise DriverError(f"no run folders under {settings.out}")
    inputs: dict[str, CaseInputs] = {}
    scores: list[PathwayScore] = []
    for folder, meta, _ in found:
        if meta.case_id not in CASES.values():
            raise DriverError(f"run {meta.run_id}: case {meta.case_id} is not one of the goldens")
        if meta.case_id not in inputs:
            inputs[meta.case_id] = load_inputs(meta.case_id, settings.cases, settings.corpus)
        scored = inputs[meta.case_id]
        refusals = receipt_refusals(folder)
        _check_refusal_names(meta, refusals)
        scores.append(score_run(folder, scored.case, scored.mapping, refusals=refusals))
    path = settings.out / SCORES_FILE
    body = _Scores(schema_version="model-testing-scores/1", scores=tuple(scores))
    path.write_text(body.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _notes(
    stopped: MappingABC[str, str],
    settlements: Sequence[Settlement],
    runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]],
) -> list[str]:
    lines: list[str] = []
    if stopped:
        lines += ["## Stopped configurations", ""]
        lines += [f"- {key}: {_cell_text(why)}" for key, why in sorted(stopped.items())]
        lines.append("")
    if settlements:
        lines += [
            "## Settled charges",
            "",
            "| Run | Module | Step | Attempt | Call | Settled | By | Date | Source |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        ordered = sorted(
            settlements, key=lambda x: (x.run_id, x.module_id, x.step_id, x.attempt, x.call_index)
        )
        for s in ordered:
            lines.append(
                f"| {_cell_text(s.run_id)} | {_cell_text(s.module_id)} | {_cell_text(s.step_id)} | "
                f"{s.attempt} | {s.call_index} | {_money(s.settled_usd)} | {_cell_text(s.by)} | "
                f"{s.date} | {_cell_text(s.source)} |"
            )
        lines += ["", "| Account | Spend after settlements |", "| --- | --- |"]
        lines += [
            f"| {account} | {_money(account_spend(runs, account, settlements))} |"
            for account in ACCOUNTS
        ]
        lines.append("")
    return lines


_STAGE_RANK = {"pilot": 0, "repair": 1, "comparison": 2, "slice": 3}


def _recency(run_id: str) -> tuple[int, int, str]:
    """Later stage, then higher run number, is more recent (run ids are ``<stage>-...-<n>``)."""
    number = re.search(r"-(\d+)$", run_id)
    return (
        _STAGE_RANK.get(run_id.split("-", 1)[0], -1),
        int(number.group(1)) if number else 0,
        run_id,
    )


def _rank(score: PathwayScore) -> tuple[bool, tuple[int, int, str]]:
    """A live run before any offline one (an offline replay never stands in for paid model
    output), then the most recent."""
    return score.mode == "live", _recency(score.run_id)


def _latest(scores: Sequence[PathwayScore]) -> tuple[PathwayScore, ...]:
    """One score per (pathway, configuration): the most recent live run, a rerun superseding;
    the most recent offline run only where there is no live one (its cells say OFFLINE)."""
    best: dict[tuple[str, str], PathwayScore] = {}
    for score in scores:
        key = (score.pathway, score.config_id)
        if key not in best or _rank(score) > _rank(best[key]):
            best[key] = score
    return tuple(sorted(best.values(), key=lambda x: x.run_id))


_SCORED_FIELDS = (
    "case_id",
    "pathway",
    "config_id",
    "mode",
    "outcome",
    "stopped_reason",
    "delivery_scope",
)


def _check_scores_match(
    scores: Sequence[PathwayScore], runs: Sequence[tuple[RunMeta, tuple[CallRecord, ...]]]
) -> None:
    """Scores written before a run folder appeared, changed or went away are stale: name the
    run. Every run folder needs one score that agrees with its run.json."""
    by_run = {meta.run_id: meta for meta, _ in runs}
    scored = {score.run_id for score in scores}
    stale = [s.run_id for s in scores if s.run_id not in by_run]
    stale += sorted(run_id for run_id in by_run if run_id not in scored)
    stale += [
        s.run_id
        for s in scores
        if s.run_id in by_run
        and any(getattr(s, f) != getattr(by_run[s.run_id], f) for f in _SCORED_FIELDS)
    ]
    if stale:
        raise DriverError(
            f"{SCORES_FILE} does not match the run folders (run {stale[0]}); "
            "run the score command again"
        )
    for score in scores:
        if score.pathway not in CASES:
            raise DriverError(f"run {score.run_id}: pathway {score.pathway} is not a golden")


def report_out(settings: Settings) -> Path:
    """Write ``report.md`` from ``scores.json`` (the latest run per pathway and configuration),
    the run folders and ``faults.jsonl``. The stopped configurations are derived from the runs
    and settlements as they are now; only a skipped distressed run, which cannot be derived, is
    taken from the last stage command."""
    check_out_inside_root(settings)
    scores_path = settings.out / SCORES_FILE
    if not scores_path.is_file():
        raise DriverError(f"no {SCORES_FILE} under {settings.out}: run the score command first")
    try:
        scores = _Scores.model_validate_json(scores_path.read_bytes()).scores
    except ValidationError as error:
        raise _invalid(SCORES_FILE, error) from None
    runs = load_runs(settings.out)
    everywhere = load_runs(settings.runs_root)
    settlements = load_all_settlements(settings.runs_root, settings.out)
    _check_scores_match(scores, runs)
    latest = _latest(scores)
    try:
        faults = read_faults(settings.out / FAULTS_FILE)
    except ValueError as error:  # the fault journal's one refusal: an unparsable record
        raise DriverError(f"{FAULTS_FILE}: {error}") from None
    # the table matches settlements against this out's runs only; a settlement naming a run in a
    # sibling folder is matched there, and an orphan is still refused through current_stops/_notes
    own_runs = {meta.run_id for meta, _ in runs}
    own_settlements = tuple(s for s in settlements if s.run_id in own_runs)
    try:
        text = render_report(
            latest, runs, faults, own_settlements, Ledger(everywhere, settlements)
        )
    except ReportInputError as error:  # a refused input, named; anything else is a defect
        raise DriverError(f"report: {error}") from None
    skipped = {k: v for k, v in _read_exhausted(settings.out).items() if k not in CONFIGS}
    stopped = {**skipped, **current_stops(everywhere, settlements)}
    notes = _notes(stopped, settlements, everywhere)
    notes += ["## Runs root", "", f"Runs root: {settings.runs_root.resolve()}", ""]
    text += "\n" + "\n".join(notes)
    path = settings.out / REPORT_FILE
    path.write_text(text, encoding="utf-8")
    return path


# ------------------------------------------------------------------ command line


def _modules(text: str) -> frozenset[str]:
    """A comma-separated module list, as ``--repaired CP-1,CP-1A``."""
    names = frozenset(part.strip() for part in text.split(","))
    if "" in names:
        raise argparse.ArgumentTypeError(f"{text!r} is not a comma-separated list of modules")
    return names


def _money_arg(text: str) -> Decimal:
    """A ``--cap``/``--week-cap`` amount; ``check_settings`` refuses one that is not positive."""
    try:
        return Decimal(text)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"{text!r} is not a decimal amount") from None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m deploy_workflow.model_testing",
        description="Plan, run, score and report model-testing runs (offline unless --live).",
    )
    parser.add_argument(
        "command",
        choices=("pilot", "repair", "comparison", "slice", "recordings", "score", "report"),
    )
    parser.add_argument("--out", type=Path, required=True, help="artifacts/model-testing/<run_id>/")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=DEFAULT_RUNS_ROOT,
        help="every run directory under it counts toward the account caps; --out lies inside it",
    )
    parser.add_argument("--cases", type=Path, default=Path("cases/goldens"))
    parser.add_argument("--corpus", type=Path, default=Path("data/public-corpus/v1"))
    parser.add_argument("--pathway", choices=tuple(CASES))
    parser.add_argument("--config", choices=tuple(CONFIGS))
    parser.add_argument("--cap", type=_money_arg)
    parser.add_argument("--week-cap", type=_money_arg)
    parser.add_argument("--delivery-scope", choices=(PUBLIC_S1A_SCOPE,))
    parser.add_argument(
        "--recorded-run",
        type=Path,
        help="slice only: replay with the retained run's identity and cap",
    )
    parser.add_argument("--to", type=Path, help="recordings: destination DIR/<config>/<run>.jsonl")
    parser.add_argument("--recordings", type=Path, help="offline: DIR/<config_id>/ per config")
    parser.add_argument("--live", action="store_true", help="paid provider calls; needs --ruling")
    parser.add_argument("--ruling", type=Path, help="docs/rulings/<file>.md lifting the pause")
    parser.add_argument(
        "--through",
        metavar="MODULE",
        help="stop each run after this planned analytical module settles (no publication)",
    )
    parser.add_argument(
        "--replay-from",
        type=Path,
        metavar="RUN_DIR",
        help="freeze the modules upstream of --repaired from this earlier run's submissions",
    )
    parser.add_argument(
        "--repaired",
        type=_modules,
        default=frozenset(),
        metavar="MODULE[,MODULE]",
        help="the modules to run live again; needs --replay-from",
    )
    return parser


_STAGES: MappingABC[str, Stage] = MappingProxyType(
    {"pilot": "pilot", "repair": "repair", "comparison": "comparison", "slice": "slice"}
)


def _export_recordings(args: argparse.Namespace) -> int:
    if args.to is None or args.live or args.ruling is not None:
        raise DriverError("recordings requires --to and takes no live/provider options")
    folders = [args.out] if (args.out / "run.json").is_file() else _run_dirs(args.out)
    if not folders:
        raise DriverError("no retained runs to export")
    count = 0
    for folder in folders:
        meta, _ = read_run(folder)
        target = args.to / meta.config_id / f"{meta.run_id}.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise DriverError(f"recording already exists: {target}")
        count += export_recording(folder, target, Redactor.from_environ(os.environ))
    print(f"recordings: {count}")
    return 0


def _settings(args: argparse.Namespace) -> Settings:
    """The command line as ``Settings``; the slice stage defaults its run cap, week cap and
    delivery scope."""
    is_slice = args.command == "slice"
    week_cap = args.week_cap if args.week_cap is not None else (Decimal(60) if is_slice else None)
    return Settings(
        out=args.out,
        cases=args.cases,
        corpus=args.corpus,
        recordings=args.recordings,
        live=args.live,
        ruling=args.ruling,
        runs_root=args.runs_root,
        through=args.through,
        replay_from=args.replay_from,
        repaired=args.repaired,
        pathway=args.pathway,
        config=args.config,
        cap=args.cap if args.cap is not None else (Decimal(10) if is_slice else None),
        week_cap=week_cap,
        delivery_scope=args.delivery_scope or (PUBLIC_S1A_SCOPE if is_slice else None),
        recorded_run=args.recorded_run,
    )


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "recordings":
        return _export_recordings(args)
    settings = _settings(args)
    command: str = args.command
    if command in ("score", "report"):
        if settings.live or settings.ruling is not None or settings.recordings is not None:
            raise DriverError(f"{command} takes no --live, --ruling or --recordings")
        if command == "score":
            print(f"scores: {score_out(settings)}")
        else:
            print(f"report: {report_out(settings)}")
        return 0
    result = run_stage(_STAGES[command], settings)
    for outcome in result.outcomes:
        print(f"{outcome.run_id}: {outcome.outcome}")
    for key, why in sorted(result.stopped.items()):
        print(f"stopped {key}: {why}")
    if not result.outcomes:
        return 2
    print(f"scores: {score_out(settings)}")
    print(f"report: {report_out(settings)}")
    return 0 if all(outcome.outcome == "settled" for outcome in result.outcomes) else 2


_REFUSALS = (
    DriverError,
    BudgetError,
    RunInputError,
    CaseError,
    MappingError,
    JournalError,
    ContextRefused,
    UndecodableHtml,
    RecordingError,
    LivePauseInForce,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Exit 0 on success, 2 on a refusal of the framework (message on stderr, no traceback).
    Any other exception is a defect and propagates."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:  # argparse: 0 for --help, 2 for a bad command line
        code = exit_.code
        return code if isinstance(code, int) else (0 if code is None else 2)
    try:
        return _dispatch(args)
    except _REFUSALS as error:
        print(f"error: {KEY_PATTERN.sub('[redacted]', str(error))}", file=sys.stderr)
        return 2
