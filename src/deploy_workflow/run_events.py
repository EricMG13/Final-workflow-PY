"""Append-only event log of a live CP-OS run (``events.jsonl``).

Only a live run writes it: ``run_live_handoffs`` passes its directory; retained
replays and verify scripts pass nothing and so never gain this file.
"""

import json
import os
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from deploy_workflow.model.adapter import LivePauseInForce
from deploy_workflow.model.budget import BudgetExhausted, OverrunStop, RunStopped

EVENTS = "events.jsonl"


def append_event(directory: Path, event: str, **fields: str | int) -> None:
    """Append one ASCII JSON line, then flush and fsync it. Amounts are ``str(Decimal)``.

    Documented fail-open: the log is advisory, so an OSError (disk full, permissions) is
    surfaced as a RuntimeWarning and the write is skipped; it never stops or fails a run.
    A write that fails part-way is cut back to the file's size before it, so the next event
    starts on its own line and the log stays readable.
    """
    record = {"at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "event": event, **fields}
    line = (json.dumps(record) + "\n").encode("ascii")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / EVENTS).open("ab", buffering=0) as handle:
            before = handle.tell()  # append mode opens at the end
            try:
                if handle.write(line) != len(line):  # unbuffered: a short write is a torn line
                    raise OSError("short write")
                os.fsync(handle.fileno())
            except OSError:
                handle.truncate(before)
                raise
    except OSError as error:
        warnings.warn(f"run event not recorded: {event}: {error}", RuntimeWarning, stacklevel=2)


def read_events(path: Path, limit: int = 4 * 1024 * 1024) -> list[dict[str, Any]]:
    """Read at most ``limit`` bytes; drop only an unparsable last line (a write in flight).

    An unparsable earlier line raises ValueError naming its line number.
    """
    with path.open("rb") as handle:
        raw = handle.read(limit)
    lines = raw.decode("utf-8", errors="replace").splitlines()
    events: list[dict[str, Any]] = []
    for number, line in enumerate(lines, start=1):
        try:
            events.append(json.loads(line))
        except ValueError as error:
            if number == len(lines):
                break
            raise ValueError(f"{path.name}: line {number} is not valid JSON") from error
    return events


def stop_reason(error: BaseException) -> str:
    """Fixed reason a live run stopped: budget, checker, provider, interrupted, ruling or other."""
    message = str(error)
    if isinstance(error, RunStopped | BudgetExhausted):
        # Only a cap or an overrun is a spending stop; any other RunStopped (an unknown charge)
        # is the provider's, and the cap was not what stopped the run.
        return "budget" if isinstance(error, BudgetExhausted | OverrunStop) else "provider"
    if message.startswith("cpos_live_stopped"):
        return "budget" if "overrun=True" in message else "provider"
    if message.startswith(
        ("cpos_module_failed", "cpos_live_not_accepted", "cpos_retained_rejected")
    ):
        return "checker"
    if message.startswith(("cpos_interrupted", "cpos_live_already_started")):
        return "interrupted"
    if isinstance(error, LivePauseInForce):
        return "ruling"
    return "other"
