"""Helpers the CP-2 owners (CP-2D, CP-2E, CP-2G, CP-2H) share, each defined once.

Each body is the one the owners carried as identical copies (exact decimal form, the staleness
issue frame, the run-text check, the T4.10 selector and the compact read view). The owners keep
their own names as re-exports or one-line wrappers, so callers and pinned wording are unchanged.
"""

import json
from collections.abc import Callable, Iterable, Sequence
from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from deploy_vii.contracts import Fact, Input, RunText
from deploy_vii.execution import clipped, text_sha256
from deploy_workflow.owners.period_basis import PeriodBasis


def exact_text(value: Decimal) -> str:
    """Canonical exact decimal: plain notation, no trailing zeros, unsigned zero. Formatting and
    stripping cannot round, unlike ``Decimal.normalize`` under a context precision."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def exact_decimal(value: Decimal) -> Decimal:
    """The stored form of a Decimal: the same value, trailing zeros dropped, no exponent and no
    negative zero (equal inputs give byte-equal facts)."""
    return Decimal(exact_text(value))


def stale_issues(*, bound: Sequence[Input], current: Sequence[Input] | str) -> tuple[str, ...]:
    """Every bound upstream that changed, in the `cp2_synthesis._stale_issues` form; a refused
    current read (a string) is the one clipped `Stale inputs: ...` line."""
    if isinstance(current, str):
        return (clipped(("Stale inputs: ", current)),)
    was = {item.input_id: item for item in bound}
    now = {item.input_id: item for item in current}

    def state(item: Input | None) -> str:
        return "absent" if item is None else f"{item.status} {item.sha256[:12]}"

    return tuple(
        f"Stale input {key}: bound {state(was.get(key))}, current {state(now.get(key))}"
        for key in dict.fromkeys((*was, *now))
        if was.get(key) != now.get(key)
    )


_RUN_TEXT: TypeAdapter[str] = TypeAdapter(RunText)


def run_text_issues(path: str, text: str) -> list[str]:
    """Text built as `Claim.text` checked with that very type (`RunText`, one `TypeAdapter` built
    once), so a malformed reference is a journaled issue and composition never raises after the
    binding write. The message never echoes the input."""
    try:
        _RUN_TEXT.validate_python(text)
    except ValidationError as error:
        found = error.errors(include_input=False, include_url=False, include_context=False)
        return [clipped((path, ": ", item["msg"])) for item in found]
    return []


def select_t410(
    facts: Iterable[Fact],
    metrics: Sequence[str],
    basis: PeriodBasis,
    refusal: Callable[[str, int], str],
) -> dict[str, Fact]:
    """metric -> the unique CP-1 T4.10 fact labelled `<LTM column> · <metric>`. Zero or several
    raise ValueError with ``refusal(label, count)`` (each owner keeps its pinned wording)."""
    facts = tuple(facts)
    out: dict[str, Fact] = {}
    for metric in metrics:
        label = f"{basis.ltm_column} · {metric}"
        found = [f for f in facts if f.table_id == "T4.10" and f.label == label]
        if len(found) != 1:
            raise ValueError(refusal(label, len(found)))
        out[metric] = found[0]
    return out


def compact_view(block: object) -> tuple[str, str]:
    """(sha256, body) of a read view: the block as compact JSON (no ASCII escaping, no NaN)."""
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return text_sha256(body), body
