"""A run's CP-OS event log (runs/<id>/events.jsonl): read, decoded and folded into progress.

Decoding follows the Go server's json.Unmarshal into its runEvent struct, so a line the Go app
read is read here and a line it refused is refused here. Standard library only.
"""

from __future__ import annotations

import json
import logging
import os
import re
import stat
from dataclasses import dataclass, field
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

log = logging.getLogger("issuer_library")

EVENTS_LIMIT = 4 << 20  # How much of a log is read; tests patch it.
FIRST_LINE_LIMIT = 8192
TEXT_FIELDS = ("at", "module", "spent_usd", "held_usd", "cap_usd", "reason")
NUMBER_FIELDS = ("turn", "max_turns")
INT64 = 1 << 63
LONE_SURROGATE = re.compile("[\ud800-\udfff]")
SURROGATE_ESCAPE = re.compile(r"\\u[dD][89a-fA-F]")
STEPS = {
    "module_started": "started",
    "turn": "running",
    "draft_rejected": "repairing",
    "module_accepted": "accepted",
    "delivery_started": "delivering",
    "delivered": "delivered",
    "stopped": "stopped",
}


@dataclass
class EventLog:
    """A log as read: ok is false when an earlier line is unreadable (events holds those before
    it), dropped when the last line was dropped as a write in flight, cut when the limit hit."""

    events: list[dict[str, Any]] = field(default_factory=list)
    ok: bool = True
    dropped: bool = False
    cut: bool = False


class GoDecodeError(ValueError):
    """Text or a value json.Unmarshal into the Go struct would refuse."""


def refuse_constant(name: str) -> Any:
    raise ValueError(f"not JSON: {name}")


def scrub(value: Any) -> Any:
    """Lone surrogates, which Go's decoder turns into U+FFFD, replaced the same way."""
    if isinstance(value, str):
        return LONE_SURROGATE.sub("\ufffd", value)
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        return {scrub(key): scrub(item) for key, item in value.items()}
    return value


def loads(raw: bytes, pairs: Callable[[list[tuple[str, Any]]], Any] | None = None) -> Any:
    """JSON from bytes as Go reads it. Raises ValueError for text Go refuses, including nesting
    deeper than the parser's recursion limit."""
    try:
        text = raw.decode("utf-8", "replace")
        value = json.loads(text, parse_constant=refuse_constant, object_pairs_hook=pairs)
        # scrub recurses, so a text with no surrogate escape (the usual case) skips it.
        return (
            scrub(value) if SURROGATE_ESCAPE.search(text) or LONE_SURROGATE.search(text) else value
        )
    except RecursionError as error:
        raise ValueError("nested too deeply") from error


def last_match(pairs: list[tuple[str, Any]]) -> dict[str, list[Any]]:
    """An object's values per key, in document order; keys equal under case folding are one."""
    members: dict[str, list[Any]] = {}
    for key, value in pairs:
        members.setdefault(key.casefold(), []).append(value)
    return members


def go_record(raw: bytes) -> dict[str, list[Any]]:
    """The members json.Unmarshal reads into a struct (read them with go_value), also in nested
    objects. null is the empty struct; any other non-object raises GoDecodeError."""
    value = loads(raw, last_match)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise GoDecodeError("not an object")
    return value


def go_value(
    record: dict[str, list[Any]],
    name: str,
    convert: Callable[[Any], Any],
    nil_resets: bool = False,
) -> Any:
    """A field as Go decodes it: every value in order must have the type (convert raises
    GoDecodeError otherwise), the last other value wins, and a null leaves the field as it was
    (for a slice, nil_resets, it sets the field back to nil); convert(None) is the zero value."""
    found = convert(None)
    for value in record.get(name, ()):
        if value is not None or nil_resets:
            found = convert(value)
    return found


def go_text(value: Any) -> str:
    """A string field as Go decodes it: null is "", any other non-string raises ValueError."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise GoDecodeError("not a string")
    return value


def state_of(raw: bytes) -> str | None:
    """The `state` of a status.json as Go's struct{State string} reads it: missing or null is "",
    the key matches without regard to case (null leaves it as it was, the last value wins), a
    non-string value or a non-object is a decode error, None here."""
    try:
        state: str = go_value(go_record(raw), "state", go_text)
        return state
    except ValueError:
        return None


def is_int(value: Any) -> bool:
    return type(value) is int and -INT64 <= value < INT64


def event_fields(value: dict[str, Any]) -> dict[str, Any] | None:
    """The runEvent fields of a decoded object; None when a field has the wrong type.

    Go matches keys to fields without regard to case and drops unknown keys; null leaves a field
    empty. Empty strings and zero numbers are omitted again on the way out, as the struct tags do.
    """
    wanted = ("event", "writes_left", *TEXT_FIELDS, *NUMBER_FIELDS)
    event: dict[str, Any] = {"event": ""}
    for key, item in value.items():
        name = key.lower()
        if name not in wanted or item is None:
            continue
        numeric = name in NUMBER_FIELDS or name == "writes_left"
        if (numeric and not is_int(item)) or (not numeric and not isinstance(item, str)):
            return None
        if name == "writes_left" or item not in ("", 0):
            event[name] = item
    return event


def decode_event(line: bytes) -> dict[str, Any] | None:
    """One log line as its event, or None when Go's json.Unmarshal would refuse it."""
    try:
        value = loads(line)
    except ValueError:
        return None
    if value is None:
        return {"event": ""}
    return event_fields(value) if isinstance(value, dict) else None


def parse_events(raw: bytes) -> EventLog:
    """Split on newlines; an unreadable last line is a write in flight, an earlier one stops."""
    lines = raw.split(b"\n")
    if not lines[-1]:
        lines.pop()
    record = EventLog()
    for number, line in enumerate(lines):
        event = decode_event(line)
        if event is None:
            if number == len(lines) - 1:
                record.dropped = True
            else:
                record.ok = False
            return record
        record.events.append(event)
    return record


def open_regular(path: Path) -> BinaryIO:
    """Open a regular file for reading without following a link and without blocking on a FIFO.

    Deliberately stricter than Go's os.Open. FileNotFoundError when it is missing; any other
    OSError when it is a link or not a regular file. Without O_NOFOLLOW (Windows) an lstat check
    stands in for it.
    """
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow and not stat.S_ISREG(path.lstat().st_mode):
        raise OSError(f"not a regular file: {path.name}")
    fd = os.open(path, os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(f"not a regular file: {path.name}")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def read_log(folder: Path) -> EventLog:
    """Raises FileNotFoundError for a missing log and OSError for any other read failure."""
    with open_regular(folder / "events.jsonl") as stream:
        raw = stream.read(EVENTS_LIMIT)
    record = parse_events(raw)
    record.cut = len(raw) >= EVENTS_LIMIT
    return record


def read_events(folder: Path) -> tuple[list[dict[str, Any]], bool]:
    """The run's events and whether the list is complete (not cut, not dropped, no bad line)."""
    record = read_log(folder)
    return record.events, record.ok and not record.dropped and not record.cut


def fold(events: list[dict[str, Any]]) -> dict[str, Any]:
    progress: dict[str, Any] = {"accepted": 0}
    for event in events:
        name = event["event"]
        if name in STEPS:
            if name == "stopped":
                progress["stopped_during"] = progress.get("step")  # What the stop interrupted.
            progress["step"] = STEPS[name]
        if name == "module_started":
            progress["module"] = event.get("module", "")
        elif name == "module_accepted":
            progress["accepted"] += 1
        elif name == "turn":
            progress["turn"] = event.get("turn", 0)
            progress["max_turns"] = event.get("max_turns", 0)
            for key in ("spent_usd", "held_usd", "cap_usd"):
                progress[key] = event.get(key, "")
    return progress


def retained_progress(folder: Path) -> dict[str, Any] | None:
    try:
        with open_regular(folder / "progress.json") as stream:
            value = loads(stream.read())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def progress(folder: Path) -> dict[str, Any] | None:
    """The run's progress: the folded event log, else the retained progress.json, else None.

    An unreadable earlier log line skips the whole log and falls back to progress.json: a
    documented fail-open, because progress is advisory; it is logged once per call.
    """
    try:
        record = read_log(folder)
    except FileNotFoundError:
        return retained_progress(folder)
    except OSError as error:
        log.warning(
            "run %s: events.jsonl could not be read (%s); using progress.json", folder.name, error
        )
        return retained_progress(folder)
    if record.ok and record.events:
        folded = fold(record.events)
        if record.cut:
            folded["incomplete"] = (
                True  # The log passed EVENTS_LIMIT: this is the state at the cut.
            )
        return folded
    if not record.ok:
        log.warning(
            "run %s: events.jsonl has an unreadable line; falling back to progress.json",
            folder.name,
        )
    return retained_progress(folder)


def started(folder: Path) -> str:
    """The time of the run's first event, or "" when there is no log or its first line has none."""
    try:
        with open_regular(folder / "events.jsonl") as stream:
            head = stream.read(FIRST_LINE_LIMIT)
    except OSError:
        return ""
    event = decode_event(head.split(b"\n", 1)[0])
    return event.get("at", "") if event is not None else ""
