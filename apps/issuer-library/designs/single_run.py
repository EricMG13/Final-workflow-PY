"""What the single-run walk expects of one run, read from that run's own files. Stdlib only.

The walk (browser_check.py --single-run) never reads the repo-store answer key: every value below
comes from the run folder (workflow.json, the delivery's view.json and delivery.json, the delivered
handoffs, events.jsonl, the intake status.json). A missing file is a named error, never a default;
a value the run does not record is None, never zero.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

LINE = re.compile(r"line (\d+)")
# Markdown or HTML syntax the inspector would render rather than show; such a cell is not compared.
SYNTAX = re.compile(r"[`*\[\]<>\\]")


class Unreadable(Exception):
    """A file the walk needs is missing or not what it names."""


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Unreadable(f"cannot read {path}: {error}") from error


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def only_delivery(run: Path) -> Path:
    found = sorted(p.parent for p in run.glob("deliveries/*/delivery.json"))
    if len(found) != 1:
        raise Unreadable(f"{run.name}: expected one delivery, found {len(found)}")
    return found[0]


def evidence_of(view: dict[str, Any], delivery: Path, delivery_id: str) -> list[dict[str, Any]]:
    """Handoff-line citations whose cited line is a table row, the last module's first.

    The app marks only the lines it renders as records, so the walk opens the first one it shows."""
    found: list[dict[str, Any]] = []
    for module in reversed(view["modules"]):
        file = delivery / f"{module['module_id']}.md"
        run_key = delivery.parents[1].name
        key = f"{run_key}/deliveries/{delivery_id}/{file.name}"
        lines = file.read_text().splitlines() if file.exists() else []
        for fact in module["facts"]:
            for cite in fact["citations"]:
                found_line = LINE.fullmatch(cite["locator"])
                if cite["source_id"] != module["module_id"] or not found_line:
                    continue
                number = int(found_line[1])
                text = lines[number - 1] if number <= len(lines) else ""
                if text.startswith("|") and all(e["key"] != f"{key}:{number}" for e in found):
                    found.append(
                        {
                            "module": module["module_id"],
                            "file": file.name,
                            "line": number,
                            "key": f"{key}:{number}",
                            # The app names the run's own accepted copy, if any.
                            "keys": [f"{key}:{number}", f"{run_key}/{file.name}:{number}"],
                            "cells": [c.strip() for c in text.strip("|").split("|") if c.strip()],
                        }
                    )
    return found


def activity_of(ws: Path, run: Path) -> dict[str, Any]:
    """events.jsonl and the intake status naming this run; None for each the run did not record."""
    events: list[dict[str, Any]] | None = None
    log = run / "events.jsonl"
    if log.exists():
        events = [json.loads(n) for n in log.read_text().splitlines() if n.strip()]
    spent: str | None = None
    for path in sorted(ws.glob("intake/*/status.json")):
        status = load(path)
        if status.get("run_id") == run.name and status.get("spent_usd") is not None:
            spent = str(status["spent_usd"])
    return {"events": events, "spent_usd": spent}


def expectations(ws: Path, folder: str) -> dict[str, Any]:
    run = ws / "runs" / folder
    recorded = load(run / "workflow.json")
    delivery = only_delivery(run)
    manifest = load(delivery / "delivery.json")
    view = load(delivery / "view.json")
    handoffs = {n: h for n, h in manifest["files"].items() if re.fullmatch(r"CP-[^/]+\.md", n)}
    return {
        "folder_id": folder,
        "issuer_name": recorded["run"]["issuer_name"],
        "as_of": recorded["run"]["as_of"],
        "title": recorded["layout"]["title"],
        "delivery_id": delivery.name,
        "module_titles": [m["title"] for m in view["modules"]],
        "modules": [m["module_id"] for m in view["modules"]],
        "handoffs": handoffs,
        # Hashed from the delivered bytes: a drifted file fails here, not by copying the manifest.
        "handoff_bytes_match": {n: sha256(delivery / n) == h for n, h in handoffs.items()},
        "evidence": evidence_of(view, delivery, delivery.name),
        "activity": activity_of(ws, run),
    }
