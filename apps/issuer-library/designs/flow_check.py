"""Independent data-flow check: sources -> module handoffs -> delivered copies -> report.

Stdlib only; nothing from src/ or engine/, so expected values stay independent of production code.
Usage: flow_check.py <run_dir> [--sources DIR]
"""

import hashlib
import json
import re
import sys
from collections.abc import Iterable
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# A page reference (pp.3,105-109,131,146) lists pages, which are not figures.
PAGES = re.compile(r"\bpp?\.[\d,\u2013-]+", re.IGNORECASE)
# Arguments of a call, sum(980,161), are separate numbers, not one figure with a thousands comma.
# The exception is a lone digit before a three-digit group, sum(7,941): a single digit is no
# addend (numbers() drops it), so that pair is one figure. sum(12,345) is read as 12 and 345.
CALL_ARGS = re.compile(r"(?<=\w\()[\d.,\s\u2212-]+(?=\))")
ARG_COMMA = re.compile(r"(?<![\d.])(\d),(?=\d{3}(?!\d))|,")
# When a call separates its arguments with ", " (ratio(19,702, 25,228)), a bare comma between a
# 1-3 digit group and a three-digit group is a thousands separator, whatever the group's length.
# ponytail: mixed separators such as sum(980,161, 5) read 980,161 as one figure; the upgrade path is
# to read operands from the calculate tool's own call record.
ARG_COMMA_SPACED = re.compile(r"(?<![\d.])(\d{1,3}),(?=\d{3}(?!\d))|,")
# A digest has letters; a run of digits alone is a long decimal result, not a digest.
# The same date written out for display: 31 March 2025, Mar 31, 2025.
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]{0,6}\.?"
WRITTEN_DATE = re.compile(rf"\b\d{{1,2}} {MONTH},? \d{{4}}\b|\b{MONTH} \d{{1,2}},? \d{{4}}\b")
HEX_RUN = re.compile(r"(?=[0-9]*[a-fA-F])[0-9a-fA-F]{16,}")
# A standalone number: not inside a word, path or file name. A trailing x, bn, mm, m or k is a
# multiple or scale (4.2x, $12.6bn), and a year, month or day word glued on by PDF text extraction
# (5.4years) is a unit; each is stripped; the number never stops short of a decimal.
# Not after "slug-" in lowercase (run-20261105, tdg-20240930; Term Loan B-12 stays checked) and not
# after "digit," (a page list 38,54,106 is not the figure 54,106).
UNIT = r"(?i:x|bn|mm|m|k|years?|months?|days?)"
NUMBER = re.compile(
    rf"(?<![\w/.])(?<![a-z]-)(?<!\d,)(?:\d{{1,3}}(?:,\d{{3}})+|\d+)(?:\.\d+)?{UNIT}?(?!\w|\.[A-Za-z\d])"
)
UNIT_END = re.compile(rf"{UNIT}$")
LEADING_ZERO = re.compile(r"0\d+")
# The completed record does not name its delivery folder, so every folder is checked.
LAUNCHER_KIND = "cpos-markdown-delivery/1"
MODULE = re.compile(r"CP-[A-Z0-9]+")


def _call_args(args: str) -> str:
    comma = ARG_COMMA_SPACED if ", " in args else ARG_COMMA
    return comma.sub(lambda k: k[0] if k[1] else " ", args)


def numbers(text: str) -> set[str]:
    text = CALL_ARGS.sub(lambda m: _call_args(m[0]), text)
    text = PAGES.sub(" ", HEX_RUN.sub(" ", WRITTEN_DATE.sub(" ", ISO_DATE.sub(" ", text))))
    found = set()
    for match in NUMBER.findall(text):
        value = UNIT_END.sub("", match).replace(",", "")
        if "." in value:
            value = value.rstrip("0").rstrip(".")
        if len(value) > 1 and not LEADING_ZERO.fullmatch(value):  # 02, 057: labels, not quantities
            found.add(value)
    return found


def rounded(values: set[str]) -> set[str]:
    """The roundings a reader may print of a long calculation result (4.50682961... -> 4.51).

    Only values with 6 or more decimals are expanded: they are kernel results, not reported figures.
    """
    out = set(values)
    for value in values:
        if "." in value and len(value.split(".")[1]) >= 6:
            for places in range(7):
                for mode in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                    out |= numbers(f"{Decimal(value).quantize(Decimal(1).scaleb(-places), mode):f}")
    return out


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(data: bytes) -> str:
    # Binary sources (PDF, images) carry no checkable text; they are skipped, not guessed at.
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _decode(path: Path) -> str:
    # A missing input is reported by _checked_inputs, so it adds no text here.
    return _text(path.read_bytes()) if path.is_file() else ""


def _verified(path: Path, digest: str) -> str:
    data = path.read_bytes() if path.is_file() else b""
    return _text(data) if _sha(data) == digest else ""


def _completion(run: Path) -> dict[str, Any] | None:
    """The newest completed record of the run, or None when it has none."""
    records = sorted(run.glob("completed-*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(records[-1].read_text()) if records else None


def _record_without_modules(run: Path) -> str | None:
    """The fault for a newest completed record that lists no modules, else None."""
    records = sorted(run.glob("completed-*.json"), key=lambda p: p.stat().st_mtime)
    if records and "modules" not in json.loads(records[-1].read_text()):
        return f"completed record {records[-1].name} has no modules"
    return None


def _accepted(run: Path) -> dict[str, Path]:
    """Accepted handoffs in the completed record's module order (CP-*.md by name without one)."""
    completion = _completion(run)
    if completion is not None:
        return {module: run / relative for module, relative in completion["modules"].items()}
    return {p.stem: p for p in sorted(run.glob("CP-*.md")) if MODULE.fullmatch(p.stem)}


def _launcher(run: Path) -> bool:
    """A launcher delivery carries every executed module; a manual one carries a chosen few."""
    completion = _completion(run)
    return completion is not None and completion.get("kind") == LAUNCHER_KIND


def _invocations(run: Path) -> tuple[dict[str, list[tuple[Path, dict[str, Any]]]], list[str]]:
    by_module: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    faults = []
    for folder in sorted(run.glob("live/modules/*/")):
        try:
            request = json.loads(
                json.loads((folder / "0.request.json").read_text())["messages"][1]["text"]
            )
            by_module.setdefault(request["module_id"], []).append((folder, request))
        except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
            faults.append(f"{folder.name}: invocation record unreadable ({error!r})")
    return by_module, faults


def _accepted_draft(draft: Path) -> bool:
    """The checker passed this draft: its N.review.json lists no issues. A missing or unreadable
    review means acceptance cannot be shown."""
    review = draft.with_name(draft.name.removesuffix(".draft.md") + ".review.json")
    try:
        record = json.loads(review.read_text())
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get("issues") == []


def _producing(
    invocations: list[tuple[Path, dict[str, Any]]], handoff: bytes
) -> list[tuple[Path, dict[str, Any]]]:
    """The invocations holding a draft that byte-equals the accepted handoff and passed review;
    earlier attempts of a re-run module received superseded upstreams and did not produce it."""
    return [
        (folder, request)
        for folder, request in invocations
        if any(
            d.read_bytes() == handoff and _accepted_draft(d)
            for d in sorted(folder.glob("*.draft.md"))
        )
    ]


def _source_names(by_module: dict[str, list[tuple[Path, dict[str, Any]]]]) -> set[str]:
    return {
        name for invocations in by_module.values() for _, r in invocations for name in r["sources"]
    }


def _named_source(sources: Path | None, name: str) -> Path:
    path = (sources or Path()) / name
    if sources is not None and not path.is_file() and name.endswith(".jsonl"):
        path = sources / name.removesuffix(".jsonl")
    return path


def _shared_numbers(run: Path, sources: Path | None, names: set[str]) -> set[str]:
    """Numbers any module may cite: the run's own text copies and context, and, given a sources
    folder, the files some request names. A request names the converted copy (x.htm.jsonl) of a
    source file x.htm, so a name ending .jsonl with no such file maps to the file without it."""
    texts = [_decode(p) for p in sorted(run.glob("source-text/*.jsonl"))]
    texts += [_decode(run / "context.json")] if (run / "context.json").exists() else []
    for name in sorted(names) if sources is not None else []:
        texts.append(_decode(_named_source(sources, name)))
    return set().union(*(numbers(t) for t in texts)) if texts else set()


def _calls(folder: Path) -> dict[str, Any]:
    """Tool-call arguments by call id. The newest request carries the whole assistant history. An
    unreadable record yields no calls, so no calculate result of that invocation counts."""
    requests = sorted(folder.glob("*.request.json"), key=lambda p: int(p.name.split(".")[0]))
    try:
        messages = json.loads(requests[-1].read_text())["messages"] if requests else []
        return {
            c["call_id"]: c["arguments"]
            for m in messages
            if m.get("role") == "assistant"
            for c in m.get("tool_calls", [])
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def _operands(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set().union(*(_operands(v) for k, v in node.items() if k != "operation"))
    if isinstance(node, list):
        return set().union(*(_operands(v) for v in node))
    return numbers(str(node))


def _read_numbers(folder: Path, base: set[str]) -> set[str]:
    """Numbers in what the module read. The engine's own replies (write_handoff, edit_handoff) are
    not reading. A calculate result counts only once every operand of its call is itself evidence,
    iterated to a fixpoint, so chained calculations resolve; an invented operand of two or more
    digits cannot launder (single digits are not checked, as everywhere here)."""
    calls, pending, evidence = _calls(folder), [], set(base)
    for tools in sorted(folder.glob("*.tools.json")):
        for c in json.loads(tools.read_text()):
            if c["name"] == "calculate":
                pending.append(c)
            elif c["name"] not in ("write_handoff", "edit_handoff"):
                evidence |= numbers(c["text"])
    changed = True
    while changed:
        changed, known = False, rounded(evidence)
        for c in list(pending):
            arguments = calls.get(c["call_id"])
            if arguments is not None and _operands(arguments) <= known:
                evidence |= numbers(c["text"])
                pending.remove(c)
                changed = True
    return evidence


def _checked_inputs(
    run: Path, request: dict[str, Any], sources: Path | None, module: str
) -> list[str]:
    faults = []
    for name, digest in request["sources"].items():
        copies = {"inputs": run / "inputs" / digest}
        if sources is not None:
            copies["sources"] = sources / name
        present = {where: path for where, path in copies.items() if path.is_file()}
        bad = [where for where, path in present.items() if _sha(path.read_bytes()) != digest]
        if not present:
            faults.append(f"{module}: source {name} sha256 {digest[:12]} matches no supplied file")
        faults += [
            f"{module}: source {name} copy in {where} does not hash to {digest[:12]}"
            for where in bad
        ]
    return faults


def _received(run: Path, request: dict[str, Any]) -> set[str]:
    """Numbers in what the module was given: its upstream handoffs and its source files."""
    texts = [h["markdown"] for h in request["handoffs"].values()]
    # A copy that does not hash to its digest is reported by _checked_inputs and never read.
    texts += [_verified(run / "inputs" / digest, digest) for digest in request["sources"].values()]
    return set().union(*(numbers(t) for t in texts)) if texts else set()


def run_faults(run: Path, sources: Path | None = None) -> list[str]:
    if (missing := _record_without_modules(run)) is not None:
        return [missing]
    accepted = _accepted(run)
    if not accepted:
        return [f"no accepted handoff found in {run}"]
    handoffs = {module: path.read_bytes() for module, path in accepted.items()}
    by_module, faults = _invocations(run)
    shared = _shared_numbers(run, sources, _source_names(by_module))
    # The completed record lists modules in the order they were accepted; each must have received
    # all that came before it. Without a record (CP-*.md files) no order is recorded: not checked.
    ordered = list(handoffs) if _completion(run) is not None else []
    for index, (module, data) in enumerate(handoffs.items()):
        invocations = _producing(by_module.get(module, []), data)
        if not by_module.get(module):
            faults.append(f"{module}: no invocation record to check the handoff against")
        elif not invocations:
            faults.append(
                f"{module}: accepted {module} is not a draft the model submitted "
                "and the checker accepted"
            )
        evidence = set(shared)
        for folder, request in invocations:
            faults += [
                f"{module}: upstream {before} never received, though accepted before it"
                for before in ordered[:index]
                if before not in request["handoffs"]
            ]
            for upstream, sent in request["handoffs"].items():
                want = handoffs.get(upstream)
                if (
                    want is None
                    or sent["sha256"] != _sha(want)
                    or sent["markdown"].encode() != want
                ):
                    faults.append(
                        f"{module}: upstream {upstream} received differs from its accepted handoff"
                    )
            faults += _checked_inputs(run, request, sources, module)
            evidence |= _read_numbers(folder, shared | _received(run, request))
        evidence = rounded(evidence)
        if invocations:
            faults += [
                f"{module}: number {n} in the handoff is not in what the module read or received"
                for n in sorted(numbers(data.decode("utf-8", "replace")) - evidence)
            ]
    folders = sorted(p for p in run.glob("deliveries/*") if p.is_dir())
    for folder in folders if _launcher(run) else []:
        faults += [
            f"{module}: no copy in delivery {folder.name}, the handoff was dropped"
            for module in handoffs
            if not (folder / f"{module}.md").is_file()
        ]
    for copy in sorted(run.glob("deliveries/*/CP-*.md")):
        if copy.read_bytes() != handoffs.get(copy.stem):
            faults.append(
                f"{copy.stem}: delivered copy {copy.parent.name}/{copy.name} differs "
                "from the accepted handoff"
            )
    return faults


def report_faults(report_text: str, handoffs: Iterable[str], context: str = "") -> list[str]:
    known = rounded(numbers(context).union(*(numbers(h) for h in handoffs)))
    return [
        f"report: number {n} is not in the handoffs or context"
        for n in sorted(numbers(report_text) - known)
    ]


def main(argv: list[str]) -> int:
    args = list(argv)
    sources = Path(args.pop(args.index("--sources") + 1)) if "--sources" in args else None
    if sources is not None:
        args.remove("--sources")
    if len(args) != 1:
        print("usage: flow_check.py <run_dir> [--sources DIR]", file=sys.stderr)
        return 2
    faults = run_faults(Path(args[0]), sources)
    print("\n".join(faults))
    print(f"flow: {len(faults)} fault(s)")
    return int(bool(faults))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
