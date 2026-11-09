"""Fault records for the browser walk. Stdlib only; nothing from src/ or engine/."""

import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Go log lines may start with a date and time; "http: panic serving" is net/http recovering a panic.
CRASH = re.compile(
    r"^(\d{4}/\d\d/\d\d \d\d:\d\d:\d\d(\.\d+)? )?"
    r"(panic: |fatal error: |http: panic serving |Traceback \(most recent call last\):"
    r"|WARNING: DATA RACE)",
    re.MULTILINE,
)
# A navigation or frame swap cancels a load; the cancelled request is not a fault.
IGNORED_FAILURES: tuple[str, ...] = ("net::ERR_ABORTED", "NS_BINDING_ABORTED")


def redact(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        if len(secret) >= 8:
            text = text.replace(secret, "[redacted]")
    return text


def crashes(log: str) -> list[str]:
    lines = log.splitlines()
    return [
        "\n".join(lines[number : number + 6])
        for number, line in enumerate(lines)
        if CRASH.match(line)
    ]


def http_fault(status: int, path: str, expected: frozenset[tuple[int, str]]) -> bool:
    return status >= 500 or (400 <= status < 500 and (status, path) not in expected)


def request_fault(failure: str | None) -> bool:
    return failure is not None and not any(mark in failure for mark in IGNORED_FAILURES)


@dataclass
class Fault:
    walk: str
    kind: str
    detail: str
    url: str = ""
    artifacts: list[str] = field(default_factory=list)


class Faults:
    def __init__(self) -> None:
        self.items: list[Fault] = []

    def add(
        self, walk: str, kind: str, detail: str, url: str = "", artifacts: list[str] | None = None
    ) -> None:
        self.items.append(Fault(walk, kind, detail, url, artifacts or []))

    def write(self, path: Path, scope: str, passed: int, secrets: Iterable[str] = ()) -> None:
        data = {
            "scope": scope,
            "passed": passed,
            "failed": len(self.items),
            "faults": [asdict(item) for item in self.items],
        }
        path.write_text(redact(json.dumps(data, indent=2), secrets) + "\n")
