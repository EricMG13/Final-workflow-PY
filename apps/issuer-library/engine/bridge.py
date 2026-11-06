"""Local CP-OS adapter. `review` is offline; only `start` may contact a provider."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import warnings
from collections.abc import Iterable
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

COMPLETE_MESSAGE = (
    "Report written. Automated checks only: review the handoffs against the "
    "sources before relying on this."
)
HERE = Path(__file__).resolve().parent
ENGINE_SRC = HERE / "src" if (HERE / "src").is_dir() else HERE.parents[2] / "src"
sys.path.insert(0, str(ENGINE_SRC))

from deploy_vii.registry import modules
from deploy_workflow.model.adapter import KEY_VARIABLES
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.pricing import PRICES_AS_OF
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model_testing.configs import CONFIGS
from deploy_workflow.owners.cpos import run_live_handoffs, with_notes
from deploy_workflow.owners.cpos_launch import MAX_OUTPUT_TOKENS, Prepared, checker, prepare
from issuer_library.settings import save_json, write_atomic

# Room a run needs beyond this job's folder: requests/<module>/<hash>/<n>.request.json under runs/.
RUN_PATH_ROOM = 100


class Recorded(Exception):
    """A failed start whose status, with its spend, is already written; main only reports it."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


# The library's one atomic writer; a handoff or status file is replaced whole, never torn.
write_file = write_atomic


def write_json(path: Path, value: object) -> None:
    save_json(path, value, allow_nan=False)


def clean(text: str) -> str:
    """Text the browser may show: redacted, and no provider key value from the environment."""
    cleaned: str = Redactor.from_environ(os.environ).text(text)
    for key in KEY_VARIABLES.values():
        secret = os.environ.get(key)
        if secret:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def release_notes(caught: Iterable[warnings.WarningMessage]) -> list[str]:
    """The adapter's release failures among the warnings a run raised, once each, cleaned."""
    notes: list[str] = []
    for item in caught:
        text = str(item.message)
        if not issubclass(item.category, RuntimeWarning):
            continue
        note = clean(text)
        if text.startswith("adapter release failed") and note not in notes:
            notes.append(note)
    return notes


def read_job(directory: Path) -> tuple[dict, Path]:
    job = json.loads((directory / "job.json").read_text(encoding="utf-8"))
    workspace = Path(job["workspace"]).resolve(strict=True)
    if directory.resolve().parent != workspace / "intake" or directory.name != job["id"]:
        raise ValueError("job is not in its approved workspace intake folder")
    folder = (directory / "sources").resolve()
    if not job["sources"]:
        raise ValueError("choose a folder holding at least one issuer file")
    for item in job["sources"]:
        file = directory / "sources" / item["path"]
        if file.is_symlink() or not file.resolve().is_relative_to(folder):
            raise ValueError("invalid staged source identity")
        try:
            raw = file.read_bytes()
        except OSError as error:
            raise ValueError(
                f"Could not read {item['path']}. If its path is very long, rename the folders "
                "around it or choose a shorter workspace folder."
            ) from error
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError(f"source changed since upload: {item['path']}")
    return job, workspace


def check_path_room(directory: Path) -> None:
    """Windows refuses a path over 259 characters unless long paths are on; ask before any spend."""
    probe = directory / ("x" * RUN_PATH_ROOM)
    try:
        probe.touch()
        probe.unlink()
    except OSError as error:
        raise ValueError(
            "This workspace's path is too long for a run on this computer. "
            "Choose a shorter workspace folder in Settings."
        ) from error


def launch(job: dict, directory: Path, out: Path) -> Prepared:
    """The launcher's own checks and plan. A refusal writes nothing."""
    try:
        cap = Decimal(job["cap_usd"])
    except InvalidOperation:
        cap = Decimal(0)
    if not cap.is_finite() or cap <= 0:
        raise ValueError("Enter the maximum spend as a positive USD amount.")
    if job["config"] not in CONFIGS:
        raise ValueError(f"Unknown model selection: {job['config']}")
    return prepare(
        directory / "context.json",
        directory / "sources",
        out,
        config=job["config"],
        cap=cap,
        modules=job["modules"] or None,
    )


def engine_revision() -> str:
    revision = hashlib.sha256(Path(__file__).read_bytes())
    for file in sorted(ENGINE_SRC.rglob("*")):
        if file.is_file() and file.suffix in {".py", ".json", ".md"}:
            revision.update(file.relative_to(ENGINE_SRC).as_posix().encode())
            revision.update(file.read_bytes())
    return revision.hexdigest()


def review(directory: Path) -> dict:
    job, _ = read_job(directory)
    check_path_room(directory)
    # A scanner holding a file for a moment on Windows must not refuse the review.
    with tempfile.TemporaryDirectory(dir=directory, ignore_cleanup_errors=True) as preview:
        prepared = launch(job, directory, Path(preview))
    request = prepared.plan
    revision = engine_revision()
    # Binds Start to what was reviewed: request, inputs, instructions and the running code.
    material = {
        "job": job,
        "engine": revision,
        "run": request.run.run_id,
        "sources": {name: item.sha256 for name, item in request.sources.items()},
        "instructions": {name: item.sha256 for name, item in request.instructions.items()},
        "hold": str(prepared.hold),
    }
    selected = CONFIGS[job["config"]]
    return {
        "ok": True,
        "review_id": hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest(),
        "id": job["id"],
        "engine_revision": revision,
        "issuer": request.run.issuer_name,
        "issuer_id": request.run.issuer_id,
        "pathway": request.run.pathway,
        "as_of": request.run.as_of.isoformat(),
        "modules": list(prepared.ordered),
        "module_details": [
            {"id": item.module_id, "title": item.title, "purpose": item.purpose}
            for module_id in prepared.ordered
            for item in modules()
            if item.module_id == module_id
        ],
        "config": selected.config_id,
        "provider": selected.provider,
        "model": selected.model,
        "effort": selected.effort,
        "cap_usd": job["cap_usd"],
        "hold_usd": f"{prepared.hold:.2f}",
        "max_turns": job["max_turns"],
        "prices_as_of": str(PRICES_AS_OF),
        "provider_ready": bool(os.environ.get(KEY_VARIABLES[selected.provider])),
        "provider_key": KEY_VARIABLES[selected.provider],
        "sources": job["sources"],
        "ignored": list(prepared.ignored),
        "report_sections": list(prepared.layout.blocks),
        "omitted": list(prepared.omitted),
        "scope": prepared.layout.scope,
    }


def start(directory: Path) -> None:
    approved = json.loads((directory / "review.json").read_text(encoding="utf-8"))
    current = review(directory)
    if approved["review_id"] != current["review_id"]:
        raise ValueError("review is stale; review the inputs again before starting")
    if not current["provider_ready"]:
        raise ValueError("the selected provider is not configured in the launching environment")
    job, workspace = read_job(directory)
    # This receipt is created only after the web API's explicit, one-shot Start.
    ruling = directory / "start-authorization.md"
    with ruling.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(
            f"lifts: live-provider-pause\nby: user\ndate: {date.today()}\n"
            f"configs: {job['config']}\nreview: {current['review_id']}\n"
        )
    prepared = launch(job, directory, workspace / "runs" / job["id"])
    run_dir = prepared.directory

    def spent() -> str:
        return str(Budget(prepared.plan.provider_cap_usd, run_dir / "live").spent)

    def started(task) -> None:
        write_json(
            run_dir / "progress.json",
            {"module": task.module_id, "step": "started", "spent_usd": spent()},
        )

    def progress(task, raw) -> None:
        # Accepted handoffs are retained here so a stopped run still shows what it paid for.
        write_file(run_dir / f"{task.module_id}.md", raw)
        write_json(
            run_dir / "progress.json",
            {"module": task.module_id, "step": "accepted", "spent_usd": spent()},
        )

    try:
        # The app discards stderr: a release failure after a finished run is a RuntimeWarning,
        # recorded here and shown in the status message.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", RuntimeWarning)
            run_live_handoffs(
                prepared.manifest,
                run_dir,
                ruling=ruling,
                rulings_root=directory.resolve(),
                check=checker(prepared.layout),
                max_turns=job["max_turns"],
                max_output_tokens=MAX_OUTPUT_TOKENS,
                on_handoff=progress,
                on_start=started,
                config=job["config"],
            )
    except Exception as error:  # Any failure after a paid call records its spend.
        # A refusal (ValueError, RuntimeError) stops the run; anything else is a failure.
        stopped = isinstance(error, (ValueError, RuntimeError))
        message = (
            f"{with_notes(error)} Retained work is in the run folder; "
            "no automatic paid retry was made."
        )
        write_json(
            directory / "status.json",
            {
                "state": "stopped" if stopped else "failed",
                "message": clean(message),
                "spent_usd": spent(),
            },
        )
        if stopped:
            return
        raise Recorded([clean(with_notes(error))]) from error
    write_json(
        directory / "status.json",
        {
            "state": "complete",
            "message": "; ".join([COMPLETE_MESSAGE, *release_notes(caught)]),
            "spent_usd": spent(),
            "run_id": job["id"],
        },
    )


def main() -> None:
    directory = Path(sys.argv[2]).resolve()
    try:
        if sys.argv[1] == "review":
            print(json.dumps(review(directory)))
        elif sys.argv[1] == "start":
            start(directory)
        else:
            raise ValueError("unknown CP-OS operation")
    except Exception as error:  # noqa: BLE001 -- isolate/redact the worker process boundary
        problems = list(getattr(error, "problems", (with_notes(error),)))
        # Never return arbitrary provider response bodies or environment values.
        cleaned = [clean(str(problem)) for problem in problems]
        if sys.argv[1] == "start" and not isinstance(error, Recorded):
            write_json(
                directory / "status.json", {"state": "failed", "message": "; ".join(cleaned)}
            )
        print(json.dumps({"ok": False, "problems": cleaned}))
        sys.exit(2)


if __name__ == "__main__":
    main()
