"""CP-OS handoff orchestration and retained native report-navigation verification.

``run_handoffs`` drives the checked public snapshot or explicitly mapped Markdown
report sections using the existing dependency planner and separate delivery adapter.
Explicit ``run_live_handoffs`` uses the adapted cp-os module loop with the existing
provider adapter and durable budget. Replay and host exchanges remain provider-free.
``run_comparison`` uses the same exchange for the current CP-8 definition:
compare complete prior/current delivery bundles, then publish its checked answer.
It does not invoke the imported investment-decision ledger owner.
The narrower native navigation API below remains available unchanged.

`docs/CPOS-OWNER-LEASE.md` (D6: render-time navigation proof over a real selected run, with the
rendered page hash bound to that run's verified receipt hash; no journal head).
The navigation functions are not analytical owner steps and write nothing.

`navigation` authenticates the receipt with G1's `verify_owner_run_receipt` (its only
authentication; CP-OS neither catches nor relabels its refusals), renders the accepted view with
`deploy_vii.render.render`, and returns the page bytes with a `NavigationProof` of the navigator
rows, the six rail destinations and the one external link, every `#` href checked against the
pages the shell draws. `verify_navigation` repeats the derivation and refuses, in this order,
`cpos_binding`, `cpos_target_missing`, `cpos_rows`, `cpos_page`, `cpos_proof` (a `ValueError`
whose message starts with the prefix).
"""

import argparse
import hashlib
import json
import re
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from pydantic import Field, TypeAdapter, model_validator

from deploy_vii.contracts import Contract, Hash, Identifier, Run, Text, View
from deploy_vii.execution import Execution
from deploy_vii.registry import idle_statuses, plan
from deploy_vii.render import render
from deploy_vii.report_view import navigator
from deploy_workflow import platform_io
from deploy_workflow.handoff_delivery import (
    HEADINGS,
    DeliveryRequest,
    HandoffInput,
    MarkdownLayout,
    ModelDelivery,
    comparison_files,
    deliver,
    delivery_files,
    verify_delivery,
    verify_files,
)
from deploy_workflow.owner_workflow import (
    OwnerRunReceipt,
    SettledHead,
    verify_owner_run_receipt,
)
from deploy_workflow.run_events import append_event, stop_reason
from deploy_workflow.run_pathway import RunDirBusy, _single_writer
from deploy_workflow.run_scopes import PUBLIC_S1A_MODULES
from deploy_workflow.workflow import _put

if TYPE_CHECKING:
    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.model_testing.configs import ModelConfig


class RetainedHandoff(HandoffInput):
    """A prior checked answer and the exact source/upstream context it may be reused with."""

    source_hashes: dict[str, Hash]
    upstream: dict[str, Hash]


class HandoffPlan(Contract):
    """Pinned inputs for the public snapshot or explicitly selected report sections."""

    run: Run
    sources: dict[str, HandoffInput] = Field(min_length=1)
    instructions: dict[str, HandoffInput]
    retained_handoffs: dict[str, RetainedHandoff] = Field(default_factory=dict)
    model: ModelDelivery | None = None
    layout: MarkdownLayout | None = None
    execution: Literal["host-session", "retained-response-replay", "synthetic", "live-provider"]
    max_attempts: int = Field(default=2, ge=1, le=3)
    provider_cap_usd: Decimal = Field(default=Decimal(0), ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def execution_budget(self) -> "HandoffPlan":
        if self.execution == "live-provider":
            if self.provider_cap_usd <= 0 or self.max_attempts != 1:
                raise ValueError(
                    "Live mode needs a positive cap and one outer attempt; repairs occur inside the loop"
                )
        elif self.provider_cap_usd != 0:
            raise ValueError("Non-live modes require a zero provider cap")
        return self


class ComparisonPlan(Contract):
    """CP-8 consumes complete prior/current delivery receipts, without decision records."""

    run: Run
    prior: HandoffInput
    current: HandoffInput
    instructions: HandoffInput
    execution: Literal["host-session", "retained-response-replay", "synthetic", "live-provider"]
    max_attempts: int = Field(default=2, ge=1, le=3)
    provider_cap_usd: Decimal = Field(default=Decimal(0), ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def execution_budget(self) -> "ComparisonPlan":
        if self.execution == "live-provider":
            if self.provider_cap_usd <= 0 or self.max_attempts != 1:
                raise ValueError(
                    "Live mode needs a positive cap and one outer attempt; repairs occur inside the loop"
                )
        elif self.provider_cap_usd != 0:
            raise ValueError("Non-live modes require a zero provider cap")
        return self


@dataclass(frozen=True)
class HandoffTask:
    """Exact local model inputs; bytes and mapping proxies prevent in-place edits."""

    run: Run
    module_id: str
    instructions: bytes
    sources: Mapping[str, bytes]
    handoffs: Mapping[str, bytes]
    attempt: int
    feedback: tuple[str, ...]
    draft: bytes | None = None  # Explicit targeted repair; never automatic retry of a sent call.


def _pinned_inputs(base: Path, entries: Mapping[str, HandoffInput]) -> dict[str, bytes]:
    result = {}
    for name, spec in entries.items():
        raw = (base / spec.path).read_bytes()
        if _sha(raw) != spec.sha256:
            raise ValueError(f"cpos_input_changed: {name}")
        result[name] = raw
    return result


def _checked_handoff(
    task: HandoffTask,
    response: bytes,
    check: Callable[[HandoffTask, bytes], tuple[str, ...]],
) -> tuple[str, ...]:
    try:
        text = response.decode("utf-8")
    except UnicodeDecodeError:
        return ("The response must be UTF-8 Markdown.",)
    actual = tuple(line[3:] for line in text.splitlines() if line.startswith("## "))
    if actual != HEADINGS:
        return (
            "Use exactly these six H2 headings, once in this order: "
            + "; ".join("## " + heading for heading in HEADINGS)
            + ". All subsections must use ### or deeper, never ##. "
            + f"Received H2 headings: {actual!r}.",
        )
    issues = check(task, response)
    if type(issues) is not tuple or any(not isinstance(x, str) or not x.strip() for x in issues):
        raise ValueError("cpos_check: verifier must return a tuple of nonempty issue strings")
    return issues


def _retain_request(path: Path, raw: bytes, module_id: str) -> bool:
    """Retain an attempt's request; whether it was already retained (dispatched earlier). A
    retained request differs only in its feedback, which the recheck of the attempt before it now
    gives differently, so that attempt's answer cannot stand for this one."""
    started = path.exists()
    if started and path.read_bytes() != raw:
        raise ValueError(
            f"cpos_feedback_changed: {module_id}: the retained {path.name} answered other feedback "
            "than the recheck of the attempt before it now gives"
        )
    _put(path, raw)
    return started


def _retain_review(path: Path, raw: bytes) -> None:
    """Retain a verdict. A recheck that differs from the retained one (a fixed or tightened
    checker) is kept beside it under its own hash and is the one acted on; earlier verdicts stay as
    evidence (S01-C05)."""
    if path.exists() and path.read_bytes() != raw:
        path = path.with_name(f"{path.name.removesuffix('.json')}-{_sha(raw)}.json")
    _put(path, raw)


def _handoff(  # noqa: PLR0913 - existing signature
    task: HandoffTask,
    directory: Path,
    execute: Callable[[HandoffTask], bytes],
    check: Callable[[HandoffTask, bytes], tuple[str, ...]],
    max_attempts: int,
    *,
    retained: bytes | None = None,
) -> tuple[bytes, str]:
    """Retain before checking; resume checked bytes, never a half-finished call."""
    inputs = {
        "run": task.run.model_dump(mode="json"),
        "module_id": task.module_id,
        "instructions": task.instructions.decode("utf-8"),
        "sources": {k: _sha(v) for k, v in task.sources.items()},
        "handoffs": {k: _sha(v) for k, v in task.handoffs.items()},
        "retained_response_sha256": None if retained is None else _sha(retained),
    }
    if task.draft is not None:
        inputs["repair_draft_sha256"] = _sha(task.draft)
    encoded = json.dumps(inputs, sort_keys=True).encode()
    fingerprint = _sha(encoded)
    folder = directory / "requests" / task.module_id / fingerprint
    feedback: tuple[str, ...] = ()
    for attempt in range(1, max_attempts + 1):
        current = replace(task, attempt=attempt, feedback=feedback)
        request_path = folder / f"{attempt}.request.json"
        response_path = folder / f"{attempt}.response.md"
        review_path = folder / f"{attempt}.review.json"
        request = {**inputs, "attempt": attempt, "feedback": feedback}
        raw_request = json.dumps(request, sort_keys=True, indent=2).encode()
        already_started = _retain_request(request_path, raw_request, task.module_id)
        if response_path.exists():
            response = response_path.read_bytes()
        elif already_started:
            raise ValueError(f"cpos_interrupted: response not retained for {task.module_id}")
        else:
            response = retained if retained is not None else execute(current)
            if not isinstance(response, bytes):
                raise ValueError("cpos_response: executor must return bytes")
            _put(response_path, response)
        if retained is not None and response != retained:
            raise ValueError(f"cpos_response_changed: {task.module_id}")
        if review_path.exists():
            previous = json.loads(review_path.read_bytes())
            if previous["response_sha256"] != _sha(response):
                raise ValueError(f"cpos_response_changed: {task.module_id}")
        feedback = _checked_handoff(current, response, check)
        review = {"response_sha256": _sha(response), "issues": feedback}
        _retain_review(review_path, json.dumps(review, sort_keys=True, indent=2).encode())
        if not feedback:
            return response, str(response_path.relative_to(directory))
        if retained is not None:
            raise ValueError(f"cpos_retained_rejected: {task.module_id}: {'; '.join(feedback)}")
    raise ValueError(f"cpos_module_failed: {task.module_id}: {'; '.join(feedback)}")


def _refuse_decided_stale(ordered: Sequence[str], specs: Mapping[str, RetainedHandoff]) -> None:
    """Refuse, before any call, a retained module whose pinned upstream is not exactly the
    modules placed before it: the pins alone decide that, so no call may precede the refusal."""
    for position, module_id in enumerate(ordered):
        spec = specs.get(module_id)
        if spec is None:
            continue
        earlier = set(ordered[:position])
        if set(spec.upstream) != earlier:
            raise ValueError(f"cpos_retained_stale: {module_id}")


def _refuse_pins_of_replayed(
    specs: Mapping[str, RetainedHandoff], handoffs: Mapping[str, bytes]
) -> None:
    """Refuse a retained module whose pin of an already accepted module differs from those bytes.
    Run before each dispatch, so no call precedes a refusal the replayed modules already decide."""
    for module_id, spec in specs.items():
        if any(m in handoffs and sha != _sha(handoffs[m]) for m, sha in spec.upstream.items()):
            raise ValueError(f"cpos_retained_stale: {module_id}")


def run_handoffs(  # noqa: C901, PLR0912, PLR0913, PLR0915 -- legacy orchestrator; events is one more observer
    manifest: Path,
    directory: Path,
    *,
    execute: Callable[[HandoffTask], bytes],
    check: Callable[[HandoffTask, bytes], tuple[str, ...]],
    on_handoff: Callable[[HandoffTask, bytes], None] | None = None,
    events: Path | None = None,
) -> Path:
    """CP-OS exchange: plan, retain, check, pass current handoffs, deliver.

    Paid execution must use the explicit bounded live executor. The required
    checker compares output with instructions/evidence;
    Markdown shape alone is never analytical approval. Reusing this directory
    rechecks retained answers. Changed instructions/sources invalidate the affected
    requests and their actual consumers. All revisions remain retained. A crash
    after dispatch without retained output refuses automatic repeat. Explicitly
    retained handoffs are checked without executor calls, only when their pinned
    source and upstream context still match; completion records each module's origin.
    An optional observer runs after each checked response is durable and before
    the next module. It may stop for evidence review; resume rechecks the bytes.
    The start observer runs before each module is dispatched.
    With ``events`` (a live run's directory) each module, the delivery and its
    completion are appended to ``events.jsonl`` there; otherwise nothing is written.
    Their declared consumed inputs bound reuse planning; a checked published case
    does not trigger a new analytical build merely to satisfy a native producer.
    """
    request = HandoffPlan.model_validate_json(manifest.read_bytes())
    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.model.handoff import HandoffExecutor

    live = isinstance(execute, HandoffExecutor) and isinstance(
        execute.adapter, LiveAdapter | CopilotAdapter
    )
    if (request.execution == "live-provider") != live:
        raise ValueError("cpos_execution_mode: live mode requires the bounded live executor")
    if (
        live
        and isinstance(execute, HandoffExecutor)
        and (
            execute.budget.cap_usd != request.provider_cap_usd
            or execute.directory.resolve() != (directory / "live").resolve()
            or execute.check is not check
        )
    ):
        raise ValueError("cpos_live_binding: executor must share this run's cap, state and checker")
    if request.execution == "live-provider" and request.layout is None:
        raise ValueError("cpos_layout: a live-provider run needs a delivery layout")
    if request.layout is None and (
        request.run.pathway != "credit_snapshot"
        or request.run.case_kind != "public"
        or request.run.requested_modules != PUBLIC_S1A_MODULES
    ):
        raise ValueError("cpos_scope: only the public five-section handoff snapshot is supported")
    planned = plan(
        request.run.requested_modules,
        retained={m: tuple(spec.upstream) for m, spec in request.retained_handoffs.items()},
    )
    if request.layout is not None:
        from deploy_vii.report_view import pathways

        selected_modules = set(planned)
        if selected_modules & {"CP-8", "CP-MODEL", "CP-MEMO", "CP-OS"}:
            raise ValueError(
                "cpos_scope: select analytical Markdown modules; comparison and Model use their "
                "existing routes"
            )
        preset = next(p for p in pathways() if p.id == request.run.pathway)
        if (
            len(set(request.layout.blocks)) != len(request.layout.blocks)
            or not set(request.layout.blocks) <= set(preset.blocks)
            or {r.block_id for r in request.layout.routes} != set(request.layout.blocks)
            or any(
                r.module_id not in selected_modules
                and not (r.module_id == "CP-MODEL" and request.model is not None)
                for r in request.layout.routes
            )
            or any(r.module_id not in selected_modules for r in request.layout.front)
        ):
            raise ValueError(
                "cpos_layout: route selected modules to unique blocks of the requested pathway"
            )
    ordered = tuple(m for m in planned if m != "CP-MODEL")
    if set(request.instructions) != set(ordered):
        raise ValueError("cpos_instructions: exactly one pinned instruction per analytical module")
    if set(request.retained_handoffs) - set(ordered):
        raise ValueError("cpos_retained_inputs: handoff names must be selected analytical modules")
    sources = _pinned_inputs(manifest.parent, request.sources)
    instructions = _pinned_inputs(manifest.parent, request.instructions)
    retained = _pinned_inputs(manifest.parent, request.retained_handoffs)
    _refuse_decided_stale(ordered, request.retained_handoffs)
    source_hashes = {name: _sha(raw) for name, raw in sources.items()}
    for module_id, retained_spec in request.retained_handoffs.items():
        if retained_spec.source_hashes != source_hashes:
            raise ValueError(f"cpos_retained_sources: {module_id}")
    for raw in instructions.values():
        raw.decode("utf-8")
    model_inputs = {} if request.model is None else dict(request.model.extra_handoffs)
    if request.model is not None and request.model.forecast_exact is not None:
        model_inputs["forecast_exact"] = request.model.forecast_exact
    model_raws = _pinned_inputs(manifest.parent, model_inputs)
    identity = request.model_dump(
        mode="json", exclude={"sources", "instructions", "retained_handoffs", "model", "layout"}
    )
    directory.mkdir(parents=True, exist_ok=True)
    with _single_writer(directory):
        _put(directory / "identity.json", json.dumps(identity, sort_keys=True).encode())
        for raw in (
            *sources.values(),
            *instructions.values(),
            *retained.values(),
            *model_raws.values(),
        ):
            _put(directory / "inputs" / _sha(raw), raw)
        handoffs: dict[str, bytes] = {}
        selected: dict[str, str] = {}
        for module_id in ordered:
            _refuse_pins_of_replayed(request.retained_handoffs, handoffs)
            spec = request.retained_handoffs.get(module_id)
            if spec is not None and spec.upstream != {m: _sha(raw) for m, raw in handoffs.items()}:
                raise ValueError(f"cpos_retained_stale: {module_id}")
            task = HandoffTask(
                request.run,
                module_id,
                instructions[module_id],
                MappingProxyType(sources),
                MappingProxyType(dict(handoffs)),
                1,
                (),
            )
            if events is not None:
                append_event(events, "module_started", module=module_id)
            raw, path = _handoff(
                task,
                directory,
                execute,
                check,
                request.max_attempts,
                retained=retained.get(module_id),
            )
            handoffs[module_id] = raw
            selected[module_id] = path
            if events is not None:
                append_event(events, "module_accepted", module=module_id)
            if on_handoff is not None:
                on_handoff(task, raw)
        if events is not None:
            append_event(events, "delivery_started")
        delivery_request = DeliveryRequest(
            run=request.run,
            handoffs={
                m: HandoffInput(path=selected[m], sha256=_sha(handoffs[m]))
                for m in (ordered if request.layout is not None else ("CP-1", "CP-1A", "CP-2"))
            },
            layout=request.layout,
            module_execution=_module_execution(ordered, retained, request)
            if request.layout is not None
            else None,
            model=None
            if request.model is None
            else request.model.model_copy(
                update={
                    "extra_handoffs": {
                        k: HandoffInput(path="inputs/" + spec.sha256, sha256=spec.sha256)
                        for k, spec in request.model.extra_handoffs.items()
                    },
                    "forecast_exact": None
                    if request.model.forecast_exact is None
                    else HandoffInput(
                        path="inputs/" + request.model.forecast_exact.sha256,
                        sha256=request.model.forecast_exact.sha256,
                    ),
                }
            ),
        )
        delivery_raw = delivery_request.model_dump_json(indent=2).encode()
        manifest_id = _sha(delivery_raw)
        delivery_manifest = directory / f"delivery-{manifest_id}.json"
        _put(delivery_manifest, delivery_raw)
        publication = delivery_files(delivery_manifest)
        delivery_id = _sha(
            json.dumps(
                {name: _sha(raw) for name, raw in publication.items()}, sort_keys=True
            ).encode()
        )
        destination = directory / "deliveries" / delivery_id
        if not destination.exists():
            staging = directory / "pending-deliveries" / uuid4().hex
            deliver(delivery_manifest, staging)
            verify_delivery(delivery_manifest, staging)
            destination.parent.mkdir(parents=True, exist_ok=True)
            platform_io.replace(staging, destination)
        report = verify_delivery(delivery_manifest, destination)
        completion = {
            "kind": "cpos-handoff-snapshot/1"
            if request.layout is None
            else "cpos-markdown-delivery/1",
            "execution": request.execution,
            "scope": request.layout.scope
            if request.layout is not None
            else "public five-section snapshot"
            + (
                " plus deterministic HTML Model/charts/calculation JSON"
                if request.model is not None
                else "; Model publication not requested"
            )
            + "; not full pathway/native acceptance",
            "provider_cap_usd": str(request.provider_cap_usd) if live else 0,
            "modules": selected,
            "module_execution": _module_execution(ordered, retained, request),
            "cp_model_published": request.model is not None,
            "delivery_manifest_sha256": manifest_id,
            "report_sha256": _sha(report.read_bytes()),
        }
        completion_raw = json.dumps(completion, indent=2).encode()
        _put(directory / f"completed-{_sha(completion_raw)}.json", completion_raw)
        if events is not None:
            append_event(events, "delivered")
        return report


def _module_execution(
    ordered: tuple[str, ...], retained: Mapping[str, object], request: HandoffPlan
) -> dict[str, Literal["host-session", "retained-response-replay", "synthetic", "live-provider"]]:
    """How each module was produced: a retained handoff is a replay whatever the run's mode."""
    return {m: "retained-response-replay" if m in retained else request.execution for m in ordered}


def live_adapter_for(
    selected: "ModelConfig", ruling: Path, environ: Mapping[str, str], rulings_root: Path | None
) -> "LiveAdapter | CopilotAdapter":
    """The adapter for one model configuration: the Copilot SDK adapter for a copilot provider,
    else the HTTP adapter. A ``CopilotAdapter`` holds a runtime process and kept sessions:
    its builder must ``close()`` it after the executor finishes."""
    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.model.turn import ModelSpec

    spec = ModelSpec(selected.config_id, selected.provider, selected.model, selected.effort)
    if selected.provider == "copilot":
        return CopilotAdapter(spec, ruling, environ=environ, rulings_root=rulings_root)
    return LiveAdapter(spec, ruling, environ=environ, rulings_root=rulings_root)


def with_notes(error: BaseException) -> str:
    """``str(error)`` followed by its notes (a release failure is recorded as one), joined by "; "."""
    text = str(error)
    notes = "; ".join(n for n in getattr(error, "__notes__", ()) if n not in text)
    return f"{text}; {notes}" if notes else text


def _release(adapter: "LiveAdapter | CopilotAdapter") -> None:
    """Close the Copilot adapter (it holds a runtime process); HTTP adapters hold nothing."""
    from deploy_workflow.model.copilot_adapter import CopilotAdapter

    if isinstance(adapter, CopilotAdapter):
        adapter.close()


def run_live_handoffs(  # noqa: PLR0913 -- the explicit paid entry point takes every run option
    manifest: Path,
    directory: Path,
    *,
    ruling: Path,
    check: Callable[[HandoffTask, bytes], tuple[str, ...]],
    environ: Mapping[str, str] | None = None,
    max_turns: int = 24,
    max_output_tokens: int = 16000,
    on_handoff: Callable[[HandoffTask, bytes], None] | None = None,
    config: str = "sol-medium",
    rulings_root: Path | None = None,
) -> Path:
    """Explicit paid entry point; callers supply an evidence/instruction checker.

    No provider execution occurs during build, import, replay or normal delivery.
    Credentials come from the launching environment, never a file in this API.
    """
    import os

    from deploy_workflow.model.handoff import HandoffExecutor
    from deploy_workflow.model.redact import Redactor
    from deploy_workflow.model_testing.configs import CONFIGS

    request = HandoffPlan.model_validate_json(manifest.read_bytes())
    if request.execution != "live-provider":
        raise ValueError("cpos_live_mode: manifest must explicitly declare live-provider")
    environment = os.environ if environ is None else environ
    adapter = live_adapter_for(CONFIGS[config], ruling, environment, rulings_root)
    try:
        executor = HandoffExecutor(
            directory / "live",
            adapter=adapter,
            cap_usd=request.provider_cap_usd,
            check=check,
            redactor=Redactor.from_environ(environment),
            max_turns=max_turns,
            max_output_tokens=max_output_tokens,
            events=directory,
        )
        result = run_handoffs(
            manifest,
            directory,
            execute=executor,
            check=check,
            on_handoff=on_handoff,
            events=directory,
        )
    except BaseException as stop:
        # Documented fail-open: a release failure must not mask the stop it follows; it is
        # recorded as a note on the propagating exception.
        if isinstance(stop, Exception) and not isinstance(stop, RunDirBusy):
            # A refused second invocation never held the folder; the running run owns its log.
            append_event(directory, "stopped", reason=stop_reason(stop))
        try:
            _release(adapter)
        except Exception as failure:  # noqa: BLE001 -- noted on the propagating stop
            note = f"adapter release also failed: {failure}"
            stop.add_note(note)
            if (
                isinstance(stop, Exception)
                and len(stop.args) == 1
                and isinstance(stop.args[0], str)
            ):
                stop.args = (f"{stop.args[0]}; {note}",)  # callers that print str(stop) show it
        raise
    try:
        _release(adapter)
    except Exception as failure:  # noqa: BLE001 -- the finished run's result outranks the release
        warnings.warn(f"adapter release failed: {failure}", RuntimeWarning, stacklevel=2)
    return result


def replay_handoffs(
    manifest: Path, directory: Path, responses_manifest: Path | None = None
) -> Path:
    """Drive CP-OS with pinned prior answers; byte parity is not fresh analytical review."""
    request = HandoffPlan.model_validate_json(manifest.read_bytes())
    if request.execution != "retained-response-replay":
        raise ValueError("cpos_replay_mode: the manifest must declare retained-response-replay")
    entries: Mapping[str, HandoffInput]
    if responses_manifest is None:
        entries = request.retained_handoffs
        base = manifest.parent
    else:
        entries = TypeAdapter(dict[str, HandoffInput]).validate_json(
            responses_manifest.read_bytes()
        )
        base = responses_manifest.parent
    if set(entries) != set(request.instructions):
        raise ValueError("cpos_replay_inputs: responses must match selected analytical modules")
    responses = _pinned_inputs(base, entries)
    return run_handoffs(
        manifest,
        directory,
        execute=lambda task: responses[task.module_id],
        check=lambda task, raw: (
            () if raw == responses[task.module_id] else ("Replay bytes differ.",)
        ),
    )


def _comparison_bundle(base: Path, spec: HandoffInput) -> tuple[View, dict[str, bytes]]:
    """Check complete frozen bundle bytes and their embedded report/view consistency."""
    receipt_path = base / spec.path
    receipt_raw = receipt_path.read_bytes()
    if _sha(receipt_raw) != spec.sha256:
        raise ValueError("cp8_bundle_changed: delivery receipt")
    receipt = json.loads(receipt_raw)
    hashes = TypeAdapter(dict[str, Hash]).validate_python(receipt["files"])
    required = {"report.html", "view.json", "report-view.json"}
    if (
        not required <= set(hashes)
        or "delivery.json" in hashes
        or any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None for name in hashes)
    ):
        raise ValueError("cp8_bundle_files: unsafe or incomplete delivery file set")
    files = {name: (receipt_path.parent / name).read_bytes() for name in hashes}
    if any(_sha(files[name]) != digest for name, digest in hashes.items()):
        raise ValueError("cp8_bundle_changed: publication bytes")
    if {p.name for p in receipt_path.parent.iterdir()} != set(hashes) | {receipt_path.name}:
        raise ValueError("cp8_bundle_files: unlisted or missing publication files")
    if receipt.get("cp_model_published") is True and "model.html" not in files:
        raise ValueError("cp8_bundle_files: declared Model HTML is missing")
    view = View.model_validate_json(files["view.json"])
    from deploy_vii.report_view import ReportView

    report = ReportView.model_validate_json(files["report-view.json"])
    if files["report.html"].decode().count(OPEN_TAG) != 1 or _extract(
        files["report.html"]
    ) != _extract(render(view, report).encode()):
        raise ValueError("cp8_bundle_binding: HTML differs from retained View/ReportView")
    if "model.html" in files:
        if not {"model-view.json", "model-report-view.json", "calculation.json"} <= set(files):
            raise ValueError("cp8_bundle_files: incomplete Model publication")
        model_view = View.model_validate_json(files["model-view.json"])
        model_report = ReportView.model_validate_json(files["model-report-view.json"])
        if (
            (
                model_view.run.run_id,
                model_view.run.issuer_id,
                model_view.run.issuer_name,
                model_view.run.as_of,
            )
            != (view.run.run_id, view.run.issuer_id, view.run.issuer_name, view.run.as_of)
            or len(model_view.modules) != 1
            or model_view.modules != tuple(m for m in view.modules if m.module_id == "CP-MODEL")
            or model_view.modules[0].artifact_sha256 != _sha(files["calculation.json"])
        ):
            raise ValueError(
                "cp8_bundle_binding: Model identity/content differs from the current bundle"
            )
        if files["model.html"].decode().count(OPEN_TAG) != 1 or _extract(
            files["model.html"]
        ) != _extract(render(model_view, model_report).encode()):
            raise ValueError("cp8_bundle_binding: Model HTML differs from retained views")
    return view, {**files, "delivery.json": receipt_raw}


def _check_comparison_pair(request: ComparisonPlan, prior: View, current: View) -> None:
    """Both deliveries are the selected issuer's, the current one has the selected date, and they
    are a prior delivery and a later-or-same-dated current one: CP-8 compares a prior run's
    deliverables with the current run's (AGENTS.md), never a delivery with itself."""
    for view in (prior, current):
        if (view.run.issuer_id, view.run.issuer_name) != (
            request.run.issuer_id,
            request.run.issuer_name,
        ):
            raise ValueError("cp8_issuer: both deliveries must identify the selected issuer")
    if current.run.as_of != request.run.as_of:
        raise ValueError(
            "cp8_as_of: comparison uses the selected current delivery's financial date"
        )
    if request.prior.sha256 == request.current.sha256:
        raise ValueError("cp8_same_delivery: prior and current pin the same delivery receipt")
    if prior.run.as_of > current.run.as_of:
        raise ValueError(
            "cp8_order: the prior delivery's financial date is after the current delivery's"
        )


def run_comparison(
    manifest: Path,
    directory: Path,
    *,
    execute: Callable[[HandoffTask], bytes],
    check: Callable[[HandoffTask, bytes], tuple[str, ...]],
) -> Path:
    """CP-OS: verify both deliveries, request/check CP-8, publish its actual handoff."""
    request = ComparisonPlan.model_validate_json(manifest.read_bytes())
    from deploy_workflow.model.adapter import LiveAdapter
    from deploy_workflow.model.copilot_adapter import CopilotAdapter
    from deploy_workflow.model.handoff import HandoffExecutor

    live = isinstance(execute, HandoffExecutor) and isinstance(
        execute.adapter, LiveAdapter | CopilotAdapter
    )
    if (request.execution == "live-provider") != live:
        raise ValueError("cpos_execution_mode: live mode requires the bounded live executor")
    if (
        live
        and isinstance(execute, HandoffExecutor)
        and (
            execute.budget.cap_usd != request.provider_cap_usd
            or execute.directory.resolve() != (directory / "live").resolve()
            or execute.check is not check
        )
    ):
        raise ValueError("cpos_live_binding: executor must share this run's cap, state and checker")
    if request.run.requested_modules != ("CP-8",) or request.run.pathway != "credit_snapshot":
        raise ValueError("cp8_scope: select CP-8 deliverable comparison on the snapshot shell")
    prior_view, prior = _comparison_bundle(manifest.parent, request.prior)
    current_view, current = _comparison_bundle(manifest.parent, request.current)
    _check_comparison_pair(request, prior_view, current_view)
    instructions = _pinned_inputs(manifest.parent, {"CP-8": request.instructions})["CP-8"]
    instructions.decode("utf-8")
    sources = {
        **{"prior/" + k: v for k, v in prior.items()},
        **{"current/" + k: v for k, v in current.items()},
    }
    source_hashes = {name: _sha(raw) for name, raw in sources.items()}
    identity = request.model_dump(mode="json", exclude={"prior", "current", "instructions"})
    if not live:
        identity["provider_cap_usd"] = 0  # Preserve identities of existing provider-free runs.
    directory.mkdir(parents=True, exist_ok=True)
    with _single_writer(directory):
        _put(directory / "identity.json", json.dumps(identity, sort_keys=True).encode())
        for raw in (*sources.values(), instructions):
            _put(directory / "inputs" / _sha(raw), raw)
        task = HandoffTask(
            request.run,
            "CP-8",
            instructions,
            MappingProxyType(sources),
            MappingProxyType({}),
            1,
            (),
        )

        def checked_response(current_task: HandoffTask, raw: bytes) -> tuple[str, ...]:
            try:
                comparison_files(current_task.run, raw, source_hashes)
            except ValueError as error:
                if str(error).startswith("cp8_dimensions:"):
                    return (str(error),)
                raise
            return check(current_task, raw)

        response, response_path = _handoff(
            task, directory, execute, checked_response, request.max_attempts
        )
        files = comparison_files(request.run, response, source_hashes)
        delivery_id = _sha(
            json.dumps({name: _sha(raw) for name, raw in files.items()}, sort_keys=True).encode()
        )
        destination = directory / "deliveries" / delivery_id
        if not destination.exists():
            staging = directory / "pending-deliveries" / uuid4().hex
            for name, raw in files.items():
                _put(staging / name, raw)
            verify_files(staging, files)
            destination.parent.mkdir(parents=True, exist_ok=True)
            platform_io.replace(staging, destination)
        report = verify_files(destination, files)
        completion = {
            "kind": "cpos-deliverable-comparison/1",
            "execution": request.execution,
            "scope": "Checked CP-8 comparison of selected delivery bundles; "
            "not decision calibration or full pathway acceptance",
            "provider_cap_usd": str(request.provider_cap_usd) if live else 0,
            "response": response_path,
            "response_sha256": _sha(response),
            "input_files": source_hashes,
            "delivery_id": delivery_id,
            "report_sha256": _sha(report.read_bytes()),
        }
        raw_completion = json.dumps(completion, indent=2).encode()
        _put(directory / f"completed-{_sha(raw_completion)}.json", raw_completion)
        return report


def run_live_comparison(
    manifest: Path,
    directory: Path,
    *,
    ruling: Path,
    check: Callable[[HandoffTask, bytes], tuple[str, ...]],
    environ: Mapping[str, str] | None = None,
    max_turns: int = 24,
    max_output_tokens: int = 16000,
) -> Path:
    """Explicit bounded CP-8 execution over the existing verified bundle exchange."""
    import os

    from deploy_workflow.model.handoff import HandoffExecutor
    from deploy_workflow.model.redact import Redactor
    from deploy_workflow.model_testing.configs import CONFIGS

    request = ComparisonPlan.model_validate_json(manifest.read_bytes())
    if request.execution != "live-provider":
        raise ValueError("cpos_live_mode: manifest must explicitly declare live-provider")

    def checked_response(task: HandoffTask, raw: bytes) -> tuple[str, ...]:
        # Supply dimension feedback inside the paid repair loop, before outer publication.
        # This validation's files are discarded; run_comparison binds the published input hashes.
        try:
            comparison_files(task.run, raw, {})
        except ValueError as error:
            if str(error).startswith("cp8_dimensions:"):
                return (str(error),)
            raise
        return check(task, raw)

    environment = os.environ if environ is None else environ
    adapter = live_adapter_for(CONFIGS["sol-medium"], ruling, environment, None)
    try:
        executor = HandoffExecutor(
            directory / "live",
            adapter=adapter,
            cap_usd=request.provider_cap_usd,
            check=checked_response,
            redactor=Redactor.from_environ(environment),
            max_turns=max_turns,
            max_output_tokens=max_output_tokens,
        )
        return run_comparison(manifest, directory, execute=executor, check=checked_response)
    finally:
        _release(adapter)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CP-OS retained-handoff replay and deliverable comparison; no providers"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--compare", action="store_true", help="Replay CP-8 over prior/current delivery bundles"
    )
    parser.add_argument(
        "--replay-responses",
        type=Path,
        help="Optional when every analytical handoff is pinned in retained_handoffs",
    )
    args = parser.parse_args()
    if args.compare:
        request = ComparisonPlan.model_validate_json(args.manifest.read_bytes())
        if request.execution != "retained-response-replay" or args.replay_responses is None:
            raise ValueError(
                "cp8_replay: declare retained-response-replay and pin the CP-8 response map"
            )
        entries = TypeAdapter(dict[str, HandoffInput]).validate_json(
            args.replay_responses.read_bytes()
        )
        if set(entries) != {"CP-8"}:
            raise ValueError("cp8_replay: response map must contain only CP-8")
        response = _pinned_inputs(args.replay_responses.parent, entries)["CP-8"]
        print(
            run_comparison(
                args.manifest,
                args.state,
                execute=lambda task: response,
                check=lambda task, raw: () if raw == response else ("Replay bytes differ.",),
            )
        )
    else:
        print(replay_handoffs(args.manifest, args.state, args.replay_responses))


SCHEMA = "cpos-navigation/1"
OPEN_TAG = '<script id="report-data" type="application/json">'
CLOSE_TAG = "</script>"
# Routes the shell draws besides modules (app.js routeOf / render).
FIXED_ROUTES = frozenset({"front", "analysis", "FIT", "evidence", "limitations"})
# The recorded shell defect outside CP-OS (lease, `shell_skip_link`): excluded from the refusal.
SKIP_LINK = "workbench"
# The path charset the shell accepts for the model link (app.js renderModelArtifact).
LINK_PATH = re.compile(r"[A-Za-z0-9._-]+")
HASH_HREF = re.compile(r'href="#([^"]*)"')
# (key, label, href) as the shell's DEST (app.js).
DEST = (
    ("front", "Front Page", "#front"),
    ("analysis", "Analysis", "#analysis"),
    ("model", "Model", "#CP-1"),
    ("fit", "Portfolio Fit", "#FIT"),
    ("evidence", "Evidence", "#evidence"),
    ("limits", "Limitations", "#limitations"),
)
DEST_TITLES = {
    "analysis": "Analysis",
    "fit": "Portfolio Fit",
    "evidence": "Evidence",
    "limits": "Limitations",
}


class NavigationRow(Contract):
    """`report_view.NavRow` plus the proof that its link lands on a page that says what is true."""

    module_id: Identifier
    title: Text
    aliases: tuple[str, ...]
    number: int | None
    in_pathway: bool
    color: str
    glyph: str
    word: Text
    href: str
    group: Literal["numbered", "footer"]
    page_title: str
    has_output: bool
    empty_state: Literal["not_part_of_pathway", "no_validated_output"] | None
    limitations_panel: bool


class NavigationDestination(Contract):
    key: str
    label: str
    href: str
    page_title: str


class NavigationProof(Contract):
    schema_version: Literal["cpos-navigation/1"] = "cpos-navigation/1"
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    receipt_content_sha256: Hash
    page_sha256: Hash
    heads: tuple[SettledHead, ...]
    rows: tuple[NavigationRow, ...]
    destinations: tuple[NavigationDestination, ...]
    external_links: tuple[str, ...]


def _refuse(prefix: str, detail: str) -> ValueError:
    return ValueError(f"{prefix}: {detail}")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract(page: bytes) -> dict[str, Any]:
    """The `report-data` JSON of a page. The first closing script tag ends it (render.py escapes
    every `<` in DATA), so the text between is exact. Anything else is `cpos_target_missing`."""
    try:
        text = page.decode()
    except UnicodeDecodeError:
        raise _refuse("cpos_target_missing", "page is not UTF-8") from None
    start = text.find(OPEN_TAG)
    if start < 0:
        raise _refuse("cpos_target_missing", "no report-data tag")
    start += len(OPEN_TAG)
    end = text.find(CLOSE_TAG, start)
    if end < 0:
        raise _refuse("cpos_target_missing", "report-data tag is not closed")
    try:
        data = json.loads(text[start:end])
    except ValueError:
        raise _refuse("cpos_target_missing", "report-data is not JSON") from None
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("modules"), list)
        or not isinstance(data.get("nav"), list)
        or not isinstance(data.get("report"), dict)
        or not isinstance(data["report"].get("blocks"), list)
    ):
        raise _refuse("cpos_target_missing", "report-data lacks modules, nav or report blocks")
    result: dict[str, Any] = data
    return result


def _model_link(data: dict[str, Any]) -> str | None:
    """The calculation link path iff the shell draws it: the CP-MODEL fact `model-destination` /
    `calculation-json` / `path` with the shell's gates (app.js renderModelArtifact)."""
    model = next((m for m in data["modules"] if m.get("module_id") == "CP-MODEL"), None)
    if model is None or not model.get("artifact_sha256"):
        return None

    def fact(table: str, row: str, field: str) -> str | None:
        for item in model.get("facts", ()):
            if (item.get("table_id"), item.get("row_id"), item.get("field")) == (table, row, field):
                text = item.get("text")
                return text if isinstance(text, str) and text else None
        return None

    path = fact("model-destination", "calculation-json", "path")
    if (
        path is None
        or LINK_PATH.fullmatch(path) is None
        or not fact("model-provenance", "cp1-head", "sha256")
        or not fact("model-provenance", "pack", "sha256")
    ):
        return None
    return path


def _external_links(data: dict[str, Any], receipt: OwnerRunReceipt) -> tuple[str, ...]:
    path = _model_link(data)
    if path is None:
        return ()
    if receipt.model is None or path not in receipt.model.files:
        raise _refuse("cpos_target_missing", f"{path} is linked but not in the receipt's files")
    return (path,)


def _check_links(page: bytes, data: dict[str, Any]) -> None:
    """Every `#` href the page draws lands on a page the shell has (lease, never-a-dead-link)."""
    routes = set(FIXED_ROUTES)
    for module in data["modules"]:
        routes.add(module["module_id"])
        routes.update(module.get("aliases", ()))
    hrefs = [row["module_id"] for row in data["nav"]]
    hrefs += [href[1:] for _, _, href in DEST]
    hrefs += [
        b["full_analysis_route"] for b in data["report"]["blocks"] if b.get("full_analysis_route")
    ]
    hrefs += [module["module_id"] for module in data["modules"]]
    if _model_link(data) is not None:
        hrefs.append("CP-MODEL")
    html = page.decode()
    outside = html[: html.find(OPEN_TAG)] + html[html.find(CLOSE_TAG, html.find(OPEN_TAG)) :]
    hrefs += [match[1] for match in HASH_HREF.finditer(outside)]
    for route in hrefs:
        if route != SKIP_LINK and route not in routes:
            raise _refuse("cpos_target_missing", f"#{route} has no page")


def _rows(view: View) -> tuple[NavigationRow, ...]:
    modules = {m.module_id: m for m in view.modules}
    rows = []
    for row in navigator(view):
        module = modules[row.module_id]
        has_output = bool(module.facts or module.claims or module.tables)
        empty_state: Literal["not_part_of_pathway", "no_validated_output"] | None = None
        if not has_output:
            empty_state = "not_part_of_pathway" if row.glyph == "na" else "no_validated_output"
        rows.append(
            NavigationRow(
                **row.model_dump(),
                href="#" + row.module_id,
                group="numbered" if row.in_pathway else "footer",
                page_title=f"{row.module_id} · {row.title}",
                has_output=has_output,
                empty_state=empty_state,
                limitations_panel=bool(module.limitations),
            )
        )
    return tuple(rows)


def _destinations(view: View, data: dict[str, Any]) -> tuple[NavigationDestination, ...]:
    titles = {m.module_id: m.title for m in view.modules}
    limited = any(m.get("limitations") for m in data["modules"]) or bool(
        data["report"].get("unplaced")
    )
    result = []
    for key, label, href in DEST:
        if key == "front":
            page_title = view.run.issuer_name
        elif key == "model":
            page_title = f"CP-1 · {titles['CP-1']}"
        else:
            page_title = DEST_TITLES[key]
        if key == "limits" and limited:
            label += " · with limitations"
        result.append(NavigationDestination(key=key, label=label, href=href, page_title=page_title))
    return tuple(result)


def _derive(
    store: Execution, receipt: OwnerRunReceipt, publication_directory: Path | None
) -> tuple[View, bytes, dict[str, Any], NavigationProof]:
    """Steps 1-5 of the lease: verify, view, render, re-read, parse, derive."""
    verify_owner_run_receipt(store, receipt, publication_directory=publication_directory)
    view: View = store.view()
    if view.run != receipt.run:
        raise _refuse("cpos_binding", "view run differs from the receipt's run")
    idle = idle_statuses(receipt.run)
    heads = {head.module_id: head.status for head in receipt.heads}
    for module in view.modules:
        if module.status != heads.get(module.module_id, idle[module.module_id]):
            raise _refuse("cpos_binding", f"{module.module_id} status differs from the receipt")
    page = render(view).encode()
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise _refuse("cpos_binding", "the store changed during the render")
    data = _extract(page)
    _check_links(page, data)
    proof = NavigationProof(
        run=receipt.run,
        pack_sha256=receipt.pack_sha256,
        snapshot_sha256=receipt.snapshot_sha256,
        receipt_content_sha256=receipt.content_hash(),
        page_sha256=_sha(page),
        heads=receipt.heads,
        rows=_rows(view),
        destinations=_destinations(view, data),
        external_links=_external_links(data, receipt),
    )
    return view, page, data, proof


def navigation(
    store: Execution, receipt: OwnerRunReceipt, publication_directory: Path | None
) -> tuple[bytes, NavigationProof]:
    """The navigation page of a verified run and its proof. Writes nothing."""
    _, page, _, proof = _derive(store, receipt, publication_directory)
    return page, proof


def verify_navigation(
    store: Execution,
    receipt: OwnerRunReceipt,
    publication_directory: Path | None,
    page: bytes,
    proof: NavigationProof,
) -> None:
    """Refuse a page or proof that is not the derived one, by the first failing check in the
    order binding, target, rows, page, full proof."""
    view, derived_page, _, derived = _derive(store, receipt, publication_directory)
    if (
        proof.receipt_content_sha256 != receipt.content_hash()
        or proof.snapshot_sha256 != receipt.snapshot_sha256
        or proof.run != receipt.run
        or proof.pack_sha256 != receipt.pack_sha256
        or proof.heads != receipt.heads
        or _sha(page) != proof.page_sha256
    ):
        raise _refuse("cpos_binding", "page or proof is not bound to this verified receipt")
    shown = _extract(page)
    _check_links(page, shown)
    _external_links(shown, receipt)
    if shown["nav"] != [row.model_dump(mode="json") for row in navigator(view)]:
        raise _refuse("cpos_rows", "the page's navigator differs from the run's rows")
    if proof.rows != derived.rows or proof.destinations != derived.destinations:
        raise _refuse("cpos_rows", "the proof's rows or destinations differ from the run's")
    if page != derived_page:
        raise _refuse("cpos_page", "page bytes differ from the render of the run's view")
    if proof != derived:
        raise _refuse("cpos_proof", "proof differs from the derived proof")


if __name__ == "__main__":
    main()
