"""OpenAI, Anthropic and OpenRouter mappers: one request in, one provider-neutral turn out.

``build`` makes exactly one request; ``parse`` reads one reply. Retry, resend and repair belong
to the loop. A reply that is not a usable turn comes back as a ``ProviderError`` carrying an
``ErrorKind`` that says how its charge is settled: SentChargeKnown (a 4xx error object, nothing
generated) at 0; SentChargeUsage (tokens were generated and usage is reported) from that usage,
computed, never at 0; SentChargeUnknown held and counted; NotSent nothing.
Provider facts: work/context-plan/provider-docs-2026-10-31.md and provider-docs-o5-controller.md.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, cast

from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import (
    CONNECT_S,
    IDLE_S,
    OVERALL_S,
    IdleTimeout,
    InsecureUrl,
    NotConnected,
    OverallTimeout,
    Request,
    TransportError,
)
from deploy_workflow.model.turn import (
    CONFIG_MODELS,
    MODEL_EFFORTS,
    Message,
    ModelSpec,
    Provider,
    ProviderBlock,
    StopReason,
    ToolCall,
    Turn,
    TurnError,
    TurnRequest,
    Usage,
    dump_json,
    load_arguments,
    load_json,
)

OPENAI_URL = "https://api.openai.com/v1/responses"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# The claude-api reference (2026-11-06) sends API keys as ``x-api-key`` (``Authorization: Bearer``
# is the OAuth-token path) and names ``anthropic-version: 2026-10-21`` as the current version.
ANTHROPIC_VERSION = "2026-10-21"
OPENAI_STRICT_TOOLS = False  # not specified by the brief; schemas are not constrained to strict
MAX_OUTPUT_TOKENS = 131072  # spec §8 "up to 128k"; global cap (per-model limits not supplied)
OPENROUTER_IGNORE_FOR_DEEPSEEK = ["open-inference"]  # spec §8
MESSAGE_CHARS = 500
RETRY_AFTER_DEFAULT_S = 120
RETRY_AFTER_MAX_S = 300  # runner.py:608-614


@dataclass(frozen=True)
class Inclusivity:
    """Whether a provider's token counts include the sub-counts (ruling F6); used by pricing."""

    input_includes_cached_read: bool | None  # None: the charge does not use token counts
    output_includes_reasoning: bool | None
    charge_from_reported_cost: bool


INCLUSIVITY: Mapping[str, Inclusivity] = {
    "openai": Inclusivity(True, True, False),
    "anthropic": Inclusivity(False, True, False),  # input excludes cache read and creation
    "openrouter": Inclusivity(None, None, True),  # charge is usage.cost only
    "copilot": Inclusivity(None, None, True),  # charge is the runtime's reported cost only
}


class ProviderConfigError(ValueError):
    """A request refused before it is built; nothing is sent (NotSent)."""


class UnknownEffort(ProviderConfigError):
    pass


class MaxOutputTooLarge(ProviderConfigError):
    pass


class KeyMissing(ProviderConfigError):
    pass


REPLY_CUT = "ReplyCut"  # CP1H-R16: a reply cut off before any tool call is a provider stop
# A connect that failed before any request byte was written: NotSent, so the hold is released.
# ``ConnectTimeout`` stays in ``reply_classes.SENT_UNKNOWN`` only for records written before it.
NOT_CONNECTED = "NotConnected"


class ErrorKind(Enum):
    NOT_SENT = "NotSent"
    SENT_CHARGE_KNOWN = "SentChargeKnown"  # a 4xx error object, no usage: nothing generated, 0
    SENT_CHARGE_USAGE = "SentChargeUsage"  # tokens generated, usage reported: settle from it
    SENT_CHARGE_UNKNOWN = "SentChargeUnknown"  # held and counted


@dataclass(frozen=True)
class ProviderError:
    kind: ErrorKind
    error_class: str
    message: str
    http_status: int | None = None
    usage: Usage | None = None  # exactly when kind is SentChargeUsage
    billed_usd: Decimal | None = None  # OpenRouter usage.cost on a usage-bearing error
    reported_model: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        if (self.kind is ErrorKind.SENT_CHARGE_USAGE) != (self.usage is not None):
            raise ValueError("usage is present exactly when kind is SentChargeUsage")


class _BadReply(Exception):
    """The reply body does not have the documented shape."""


class _BadArguments(Exception):
    pass


# ---------------------------------------------------------------- effort, limits, build


def effort_for(spec: ModelSpec, effort: str | None = None) -> str:
    """The provider's effort word, only for a (model, effort) pair in the §7.1 table and a
    model that is the one its configuration names."""
    word = spec.effort if effort is None else effort
    expected = CONFIG_MODELS.get(spec.config_id)
    if expected is not None and expected != spec.model:
        raise UnknownEffort(f"config {spec.config_id!r} runs {expected!r}, not {spec.model!r}")
    if word not in MODEL_EFFORTS.get(spec.model, frozenset()):
        raise UnknownEffort(f"effort {word!r} is not accepted for {spec.model!r}")
    return word


def _json_bytes(body: Mapping[str, Any]) -> bytes:
    return dump_json(body).encode("utf-8")


def _check(spec: ModelSpec, request: TurnRequest, key: str) -> str:
    if not key or not all("!" <= c <= "~" for c in key):
        raise KeyMissing("the key is empty or not printable ASCII")
    if not 1 <= request.max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise MaxOutputTooLarge(
            f"max_output_tokens {request.max_output_tokens} outside 1..{MAX_OUTPUT_TOKENS}"
        )
    return effort_for(spec, request.effort)


def _system_text(messages: tuple[Message, ...]) -> str:
    return "\n\n".join(m.text for m in messages if m.role == "system")


def build(spec: ModelSpec, request: TurnRequest, key: str) -> Request:
    """The one provider request. ``key`` is used only for the header; nothing stores it."""
    effort = _check(spec, request, key)
    if spec.provider == "copilot":
        raise ProviderConfigError("copilot is not an https provider")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    stream = False
    if spec.provider == "openai":
        url, body = OPENAI_URL, _openai_body(spec, request, effort)
    elif spec.provider == "anthropic":
        url, body = ANTHROPIC_URL, _anthropic_body(spec, request, effort)
        del headers["Authorization"]  # an API key goes in x-api-key, never as a Bearer token
        headers["x-api-key"] = key
        headers["anthropic-version"] = ANTHROPIC_VERSION
        headers["Accept"] = "text/event-stream"
        stream = True
    else:
        url, body = OPENROUTER_URL, _openrouter_body(spec, request, effort)
    return Request(
        url=url,
        headers=headers,
        body=_json_bytes(body),
        connect_s=CONNECT_S,
        idle_s=IDLE_S,
        overall_s=OVERALL_S,
        stream=stream,
    )


def _args_json(call: ToolCall) -> str:
    return dump_json(call.arguments)


# PF-R6: sent explicitly so the write tier is the 30m one the price table charges.
OPENAI_PROMPT_CACHE_OPTIONS: Mapping[str, str] = MappingProxyType(
    {"mode": "implicit", "ttl": "30m"}
)


def _take_before(held: list[Any], key: dict[str, Any]) -> list[dict[str, Any]]:
    """The held reasoning blocks anchored before ``key``, as items, removed from ``held``."""
    taken = [dict(d["item"]) for d in held if d["before"] == key]
    held[:] = [d for d in held if d["before"] != key]
    return taken


def _function_call_item(call: ToolCall) -> dict[str, Any]:
    return {
        "type": "function_call",
        "call_id": call.call_id,
        "name": call.name,
        "arguments": _args_json(call),
    }


def _ordered_blocks(held: list[Any]) -> bool:
    """The blocks record the reply's whole output order (``_ordered_output``), not anchors."""
    return any(isinstance(d, dict) and ("message_text" in d or "function_call" in d) for d in held)


def _openai_assistant(m: Message) -> list[dict[str, Any]]:
    """The input items that resend an assistant turn. store=false: each reasoning item goes back
    unchanged, just before the item that followed it in the output (CP1H-R8b); one with nothing
    after it goes last. A reply whose order the anchors cannot express keeps its whole order."""
    held = [b.data for b in m.provider_blocks if b.provider == "openai"]
    if _ordered_blocks(held):
        return _ordered_output(held, m.tool_calls)
    items = _take_before(held, {"type": "message"})
    if m.text:
        items.append({"role": "assistant", "content": m.text})
    for c in m.tool_calls:
        items.extend(_take_before(held, {"type": "function_call", "call_id": c.call_id}))
        items.append(_function_call_item(c))
    items.extend(dict(d["item"]) for d in held)  # nothing followed them
    return items


def _ordered_output(held: list[Any], tool_calls: tuple[ToolCall, ...]) -> list[dict[str, Any]]:
    """The output items in the reply's order: reasoning verbatim, each message's own text, each
    function call where it stood; a call the blocks do not place goes last."""
    calls = {c.call_id: c for c in tool_calls}
    items: list[dict[str, Any]] = []
    for d in held:
        if "function_call" in d:
            call = (
                calls.pop(d["function_call"], None) if isinstance(d["function_call"], str) else None
            )
            if call is not None:
                items.append(_function_call_item(call))
        elif "message_text" in d:
            if d["message_text"]:
                items.append({"role": "assistant", "content": d["message_text"]})
        else:
            items.append(dict(d["item"]))
    items.extend(_function_call_item(c) for c in calls.values())
    return items


def _openai_body(spec: ModelSpec, request: TurnRequest, effort: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for m in request.messages:
        if m.role == "user":
            items.append({"role": "user", "content": m.text})
        elif m.role == "assistant":
            items.extend(_openai_assistant(m))
        elif m.role == "tool":
            items.append(
                {"type": "function_call_output", "call_id": m.tool_call_id, "output": m.text}
            )
    return {
        "model": spec.model,
        "instructions": _system_text(request.messages),
        "input": items,
        "tools": [
            {
                "type": "function",
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "strict": OPENAI_STRICT_TOOLS,
            }
            for t in request.tools
        ],
        "tool_choice": "required",  # CP1H-R7: a step ends through a submit tool call
        "reasoning": {"effort": effort},
        "max_output_tokens": request.max_output_tokens,
        "store": False,  # controller ruling: do not retain request data at the provider
        "prompt_cache_options": dict(OPENAI_PROMPT_CACHE_OPTIONS),
    }


def _tool_use(call: ToolCall) -> dict[str, Any]:
    return {"type": "tool_use", "id": call.call_id, "name": call.name, "input": call.arguments}


def _anthropic_assistant(m: Message) -> list[dict[str, Any]]:
    """An assistant turn's content: thinking blocks unchanged and in order, then the text, then
    the tool calls; or, when the reply interleaved them (``_anthropic_content``), every block at
    its own place, text and tool-use markers included. A call the blocks do not place goes last."""
    stored = [dict(b.data) for b in m.provider_blocks if b.provider == "anthropic"]
    if not any(d.get("type") in ("text", "tool_use") for d in stored):
        blocks = stored
        if m.text:
            blocks.append({"type": "text", "text": m.text})
        return blocks + [_tool_use(c) for c in m.tool_calls]
    calls = {c.call_id: c for c in m.tool_calls}
    blocks = []
    for d in stored:
        if d.get("type") == "tool_use":
            call = calls.pop(d["id"], None) if isinstance(d.get("id"), str) else None
            if call is not None:
                blocks.append(_tool_use(call))
        elif d.get("type") != "text":
            blocks.append(d)
        elif d.get("text"):
            blocks.append({"type": "text", "text": d["text"]})
    return blocks + [_tool_use(c) for c in calls.values()]


def _anthropic_body(spec: ModelSpec, request: TurnRequest, effort: str) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for m in request.messages:
        if m.role == "user":
            out.append({"role": "user", "content": m.text})
        elif m.role == "assistant":
            out.append({"role": "assistant", "content": _anthropic_assistant(m)})
        elif m.role == "tool":
            result = {
                "type": "tool_result",
                "tool_use_id": m.tool_call_id,
                "content": m.text,
                "is_error": False,
            }
            previous = out[-1] if out else None
            if (
                previous is not None
                and previous["role"] == "user"
                and isinstance(previous["content"], list)
            ):
                previous["content"].append(result)  # all results of one turn in one message
            else:
                out.append({"role": "user", "content": [result]})
    return {
        "model": spec.model,
        "max_tokens": request.max_output_tokens,
        "system": _system_text(request.messages),
        "messages": out,
        "tools": [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in request.tools
        ],
        "tool_choice": {"type": "auto"},  # from the first call: forced choice is a 400 on Opus 5.5
        "cache_control": {"type": "ephemeral"},  # CP1H-R9: automatic caching, 5 minutes
        "stream": True,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort},
    }


def _openrouter_body(spec: ModelSpec, request: TurnRequest, effort: str) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for m in request.messages:
        if m.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.text or None}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": c.call_id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": _args_json(c)},
                    }
                    for c in m.tool_calls
                ]
            details = [dict(b.data) for b in m.provider_blocks if b.provider == "openrouter"]
            if details:  # CP1H-R8: the reasoning blocks, unchanged and in order
                entry["reasoning_details"] = details
            out.append(entry)
        elif m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.text})
        else:
            out.append({"role": m.role, "content": m.text})
    body: dict[str, Any] = {
        "model": spec.model,
        "messages": out,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in request.tools
        ],
        "tool_choice": "required",  # CP1H-R7: a step ends through a submit tool call
        "max_completion_tokens": request.max_output_tokens,
        "reasoning": {"effort": effort},
    }
    if spec.model.startswith("deepseek/"):
        body["provider"] = {"ignore": list(OPENROUTER_IGNORE_FOR_DEEPSEEK)}
    return body


# ---------------------------------------------------------------- classification


def _is_error_object(body: bytes) -> bool:
    try:
        data = json.loads(body)
    except (ValueError, RecursionError):
        return False
    if not isinstance(data, dict) or "usage" in data:
        return False
    return isinstance(data.get("error"), dict) or data.get("type") == "error"


def classify(status: int, body: bytes) -> ErrorKind:
    """Whether the charge for a reply that is not a usable turn is known.

    A 4xx whose body is the provider's error object with no usage generated nothing (known).
    Every 5xx, other status, unparsable or empty reply is unknown (ruling B10). A reply that
    generated tokens and reports usage is SentChargeUsage, decided where the usage is read."""
    if 400 <= status < 500 and _is_error_object(body):
        return ErrorKind.SENT_CHARGE_KNOWN
    return ErrorKind.SENT_CHARGE_UNKNOWN


def retry_after_seconds(headers: Mapping[str, str]) -> int:
    """The wait before the loop resends an in-flight 402: ``Retry-After``, at most 300 s."""
    raw = headers.get("retry-after", "")
    try:
        value = int(raw)
    except ValueError:
        return RETRY_AFTER_DEFAULT_S
    return min(max(value, 0), RETRY_AFTER_MAX_S)


def _snippet(redactor: Redactor, text: str) -> str:
    return redactor.text(text)[:MESSAGE_CHARS]


def _provider_message(text: str) -> str:
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return text
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict) and isinstance(err.get("message"), str):
            return cast(str, err["message"])
    return text


def _http_error_class(status: int) -> str:
    if status == 402:
        return "CreditExhausted402"
    if 400 <= status < 500:
        return "ProviderRejected"
    if status >= 500:
        return "ProviderServerError"
    return "UnexpectedStatus"


def _http_error(redactor: Redactor, status: int, body: bytes, text: str) -> ProviderError:
    message = _provider_message(text)
    reflected = redactor.text(message) != message  # e.g. a JSON-escaped key, whole once decoded
    return ProviderError(
        kind=classify(status, body),
        error_class="KeyReflected" if reflected else _http_error_class(status),
        message=_snippet(redactor, message),
        http_status=status,
    )


def error_from_transport(
    provider: Provider, exc: TransportError, redactor: Redactor
) -> Turn | ProviderError:
    """A transport failure as a classified error.

    A refusal before any connection (``InsecureUrl``) and a failed connect (``NotConnected``,
    ``ConnectTimeout`` included: no request byte was written) are NotSent, class
    ``NotConnected`` for the latter; every failure after the connection (a watchdog or deadline
    OverallTimeout included) may have reached the provider and is SentChargeUnknown.
    An Anthropic stream cut by a timeout whose last usage event arrived is settled from it
    (a Turn or a SentChargeUsage error), not unknown."""
    if isinstance(exc, InsecureUrl):
        return ProviderError(ErrorKind.NOT_SENT, "InsecureUrl", _snippet(redactor, str(exc)))
    if isinstance(exc, NotConnected):
        return ProviderError(ErrorKind.NOT_SENT, NOT_CONNECTED, _snippet(redactor, str(exc)))
    error_class = (
        type(exc).__name__ if isinstance(exc, IdleTimeout | OverallTimeout) else "TransportError"
    )
    if provider == "anthropic" and exc.partial:
        cut = parse(provider, 200, exc.partial, {}, redactor)
        if (
            isinstance(cut, Turn)
            or cut.kind is ErrorKind.SENT_CHARGE_USAGE
            or cut.error_class == "KeyReflected"
        ):
            return cut
    return ProviderError(ErrorKind.SENT_CHARGE_UNKNOWN, error_class, _snippet(redactor, str(exc)))


# ---------------------------------------------------------------- parse

# CP1H-R14: the key-shape scan skips exactly two provider-encrypted values and nothing else.
# Ciphertext cannot carry our key in readable form, but base64url can hold "_sk-" and 20 more
# characters by chance, which would stop a run as KeyReflected. The exact-value scan still covers
# those values (a whole key never occurs in ciphertext by chance), and every other byte of a reply
# gets both scans.


def _openai_cipher(item: object) -> bool:
    """A Responses reasoning item with ``encrypted_content`` (output[].encrypted_content)."""
    return (
        isinstance(item, dict)
        and item.get("type") == "reasoning"
        and isinstance(item.get("encrypted_content"), str)
    )


def _openrouter_cipher(entry: object) -> bool:
    """A reasoning_details entry of type reasoning.encrypted with ``data``."""
    return (
        isinstance(entry, dict)
        and entry.get("type") == "reasoning.encrypted"
        and isinstance(entry.get("data"), str)
    )


def _openrouter_entries(data: Mapping[str, Any]) -> list[list[Any]]:
    """The ``reasoning_details`` list of every choice's message."""
    found: list[list[Any]] = []
    choices = data.get("choices")
    for choice in choices if isinstance(choices, list) else []:
        message = choice.get("message") if isinstance(choice, dict) else None
        details = message.get("reasoning_details") if isinstance(message, dict) else None
        if isinstance(details, list):
            found.append(details)
    return found


def _ciphertexts(provider: Provider, data: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(key, value) of every encrypted value that the scans skip."""
    if provider == "openai":
        output = data.get("output")
        return [
            ("encrypted_content", i["encrypted_content"])
            for i in (output if isinstance(output, list) else [])
            if _openai_cipher(i)
        ]
    if provider == "openrouter":
        return [
            ("data", e["data"])
            for details in _openrouter_entries(data)
            for e in details
            if _openrouter_cipher(e)
        ]
    return []


def _swap_ciphertext(
    provider: Provider, data: dict[str, Any], make: Callable[[str], object]
) -> dict[str, Any]:
    """``data`` with each of those values replaced by ``make(value)``, in copies; ``data``
    itself is not changed."""
    if provider == "openai" and isinstance(data.get("output"), list):
        output = [
            {**i, "encrypted_content": make(i["encrypted_content"])} if _openai_cipher(i) else i
            for i in data["output"]
        ]
        return {**data, "output": output}
    if provider == "openrouter" and isinstance(data.get("choices"), list):
        return {**data, "choices": [_swap_choice(c, make) for c in data["choices"]]}
    return data


def _swap_choice(choice: object, make: Callable[[str], object]) -> object:
    if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
        return choice
    message = choice["message"]
    details = message.get("reasoning_details")
    if not isinstance(details, list):
        return choice
    swapped = [{**e, "data": make(e["data"])} if _openrouter_cipher(e) else e for e in details]
    return {**choice, "message": {**message, "reasoning_details": swapped}}


def _swap_block(block: ProviderBlock, make: Callable[[str], object]) -> dict[str, Any]:
    """A block's data with its encrypted value replaced by ``make(value)``, in copies."""
    data = block.data
    item = data.get("item")
    if block.provider == "openai" and isinstance(item, dict) and _openai_cipher(item):
        return {**data, "item": {**item, "encrypted_content": make(item["encrypted_content"])}}
    if block.provider == "openrouter" and _openrouter_cipher(data):
        return {**data, "data": make(data["data"])}
    return data


def _empty(_value: str) -> str:
    return ""


def _blank_ciphertext(provider: Provider, data: dict[str, Any]) -> dict[str, Any]:
    return _swap_ciphertext(provider, data, _empty)


@dataclass(frozen=True)
class _Sealed:
    """An encrypted value set aside while a redactor walks the rest (it passes unknown objects)."""

    value: str


def _unseal(value: Any) -> Any:
    if isinstance(value, _Sealed):
        return value.value
    if isinstance(value, dict):
        return {k: _unseal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_unseal(v) for v in value]
    return value


def redact_reply(redactor: Redactor, data: Any, keep: Provider | None = None) -> Any:
    """``redactor.json_value`` of a decoded reply body. Only when ``keep`` names a provider, the
    encrypted reasoning value at that provider's own path (CP1H-R14) stays whole: ciphertext
    cannot carry a key, and a chance ``_sk-`` match must not corrupt it. The caller passes
    ``keep`` only for a success reply, as ``parse`` skips the path only on a 2xx. With ``None``
    (no provider, an error body) or at the other provider's path nothing is kept whole. Every
    other field, those items' other fields included, is redacted."""
    if keep is None or not isinstance(data, dict):
        return redactor.json_value(data)
    return _unseal(redactor.json_value(_swap_ciphertext(keep, data, _Sealed)))


def redact_block(redactor: Redactor, block: ProviderBlock) -> ProviderBlock:
    """``block`` redacted, but its encrypted reasoning value stays whole (CP1H-R14)."""
    sealed = _swap_block(block, _Sealed)
    return ProviderBlock(redactor.text(block.provider), _unseal(redactor.json_value(sealed)))


def _without_ciphertext(provider: Provider, text: str, redactor: Redactor) -> str | None:
    """The raw reply with each encrypted value emptied, for the key scan; None when a decoded
    encrypted value holds an exact key value (the reply is KeyReflected). A value that cannot be
    found in the text as written (other JSON escapes) stays in and is scanned: that fails closed."""
    if provider == "anthropic":
        return text
    try:
        data = load_json(text)
    except TurnError:
        return text  # not JSON: the whole text is scanned
    if not isinstance(data, dict):
        return text
    for key, value in _ciphertexts(provider, data):
        if redactor.holds_exact(value):
            return None
        pattern = re.compile(r'("' + key + r'"\s*:\s*)' + re.escape(json.dumps(value)))
        text = pattern.sub(lambda m: m.group(1) + '""', text, count=1)
    return text


def _scan_block(block: ProviderBlock, redactor: Redactor) -> dict[str, Any]:
    """A provider block as the scan sees it: its encrypted value emptied, unless it holds an exact
    key value (then it stays, and the scan refuses the turn)."""

    def scanned(value: str) -> str:
        return value if redactor.holds_exact(value) else ""

    return {"provider": block.provider, "data": _swap_block(block, scanned)}


def parse(
    provider: Provider,
    status: int,
    body: bytes,
    headers: Mapping[str, str],
    redactor: Redactor,
    *,
    cut_as_turn: bool = False,
) -> Turn | ProviderError:
    """One reply as a turn or a classified error.

    A reply cut off with no tool call is ``ReplyCut`` (CP1H-R16). ``cut_as_turn`` parses it as
    the turn it was before that ruling, for exporting an old NoSubmit record.

    A body or header holding a key (exact value or key shape), or a key that is whole only
    after decoding (JSON escapes, SSE deltas joined), comes back as ``KeyReflected`` with the
    redacted text, never as a turn."""
    text = body.decode("utf-8", errors="replace")
    scanned = _without_ciphertext(provider, text, redactor) if 200 <= status < 300 else text
    clean = redactor.text(text if scanned is None else scanned)
    if scanned is None or clean != scanned or any(redactor.text(v) != v for v in headers.values()):
        kind = classify(status, body) if not 200 <= status < 300 else ErrorKind.SENT_CHARGE_UNKNOWN
        return ProviderError(
            kind, "KeyReflected", _snippet(redactor, _provider_message(clean)), status
        )
    if not 200 <= status < 300:
        return _http_error(redactor, status, body, text)
    seen: list[Any] = []  # every string a mapper decoded or joined, whatever way it exits
    try:
        if provider == "openai":
            result = _parse_openai(status, text, seen, cut_as_turn)
        elif provider == "anthropic":
            result = _parse_anthropic(status, text, redactor, seen, cut_as_turn)
        elif provider == "copilot":
            from deploy_workflow.model.copilot import parse_events  # copilot imports this module

            result = parse_events(text, redactor, seen, cut_as_turn)
        else:
            result = _parse_openrouter(status, text, seen, cut_as_turn)
    except (_BadReply, RecursionError) as error:
        detail = "reply is nested too deeply" if isinstance(error, RecursionError) else str(error)
        result = ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN, "UnparsableReply", _snippet(redactor, detail), status
        )
    return _guard_decoded(result, status, redactor, seen)


def _guard_decoded(
    result: Turn | ProviderError, status: int, redactor: Redactor, seen: list[Any]
) -> Turn | ProviderError:
    """Run the redactor over what the mapper decoded and over the outcome: a key can be whole
    only here, and a mapper's early exit must not drop the strings it had already joined."""
    try:
        reflected = redactor.json_value(seen) != seen
    except RecursionError:
        # fail closed: data too deep for the redactor cannot be shown clean, so it counts as
        # reflected (the reply is withheld, never passed on unchecked).
        reflected = True
    if isinstance(result, ProviderError):
        if reflected or any(
            redactor.text(v) != v
            for v in (result.message, result.reported_model, result.request_id)
            if v
        ):
            return ProviderError(
                result.kind,
                "KeyReflected",
                _snippet(redactor, result.message),
                result.http_status,
                result.usage,
                result.billed_usd,
            )
        return result
    blocks = [_scan_block(b, redactor) for b in result.provider_blocks]
    calls = [{"id": c.call_id, "name": c.name, "args": c.arguments} for c in result.tool_calls]
    payload = [result.text, result.reported_model, result.request_id, blocks, calls]
    if reflected or redactor.json_value(payload) != payload:
        return ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN,
            "KeyReflected",
            _snippet(redactor, result.text),
            status,
        )
    return result


def _count(data: Mapping[str, Any] | None, key: str) -> int | None:
    if data is None or key not in data or data[key] is None:
        return None
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _BadReply(f"usage field {key} is not a non-negative integer")
    return value


def _sub(data: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if data is None or data.get(key) is None:
        return None
    value = data[key]
    if not isinstance(value, dict):
        raise _BadReply(f"{key} is not an object")
    return value


def _object(text: str) -> dict[str, Any]:
    try:
        data = load_json(text)
    except TurnError:
        raise _BadReply("reply is not JSON") from None
    if not isinstance(data, dict):
        raise _BadReply("reply is not a JSON object")
    return data


BAD_ARGUMENTS = "invalid JSON"


def _arguments(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise _BadArguments("arguments are not a string")
    try:
        return load_arguments(raw or "{}")
    except TurnError:
        raise _BadArguments("arguments are not a JSON object") from None


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _id(item: Mapping[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise _BadReply(f"a tool call has no {key}")
    return value


def _usage_error(
    error_class: str,
    message: str,
    status: int,
    usage: Usage,
    model: str | None,
    rid: str | None,
    billed: Decimal | None = None,
) -> ProviderError:
    """Tokens were generated: SentChargeUsage when usage or an exact billed charge was reported,
    else unknown. A billed charge with no token counts still settles from that charge."""
    counted = any(getattr(usage, f) is not None for f in usage.__dataclass_fields__)
    reported = counted or billed is not None
    return ProviderError(
        ErrorKind.SENT_CHARGE_USAGE if reported else ErrorKind.SENT_CHARGE_UNKNOWN,
        error_class,
        message,
        status,
        usage if reported else None,
        billed,
        model,
        rid,
    )


def _call(call_id: str, name: str, raw: object, seen: list[Any]) -> ToolCall:
    """The tool call; arguments that are not a JSON object make a flagged call with ``{}`` (the
    loop answers it with an error result instead of stopping the run). The provider's raw text
    is not kept: the next request resends ``{}`` for it."""
    try:
        args = _arguments(raw)
    except _BadArguments:
        return ToolCall(call_id, name, {}, bad_arguments=BAD_ARGUMENTS)
    seen.append(args)
    return ToolCall(call_id, name, args)


# OpenAI Responses


def _parse_openai(
    status: int, text: str, seen: list[Any], cut_as_turn: bool = False
) -> Turn | ProviderError:
    data: dict[str, Any] = {}
    texts: list[str] = []
    try:
        data = _object(text)
        return _openai_outcome(status, data, texts, seen, cut_as_turn)
    finally:
        seen.extend([_blank_ciphertext("openai", data), "".join(texts)])


def _anchor_reasoning(
    waiting: list[dict[str, Any]], blocks: list[ProviderBlock], before: dict[str, Any] | None
) -> None:
    """Turn the waiting reasoning items into blocks that name the output item they preceded
    (CP1H-R8b), so the next request resends each at its place; the item itself stays verbatim."""
    blocks.extend(ProviderBlock("openai", {"item": item, "before": before}) for item in waiting)
    waiting.clear()


def _openai_usage(raw_usage: Mapping[str, Any] | None) -> Usage:
    in_details = _sub(raw_usage, "input_tokens_details")
    return Usage(
        input_tokens=_count(raw_usage, "input_tokens"),
        cached_read_tokens=_count(in_details, "cached_tokens"),
        cache_write_tokens=_count(in_details, "cache_write_tokens"),
        output_tokens=_count(raw_usage, "output_tokens"),
        reasoning_tokens=_count(_sub(raw_usage, "output_tokens_details"), "reasoning_tokens"),
    )


def _response_error(status: int, model: str | None, rid: str | None) -> ProviderError:
    return ProviderError(
        ErrorKind.SENT_CHARGE_UNKNOWN,
        "ResponseError",
        "the response carries an error object",
        status,
        reported_model=model,
        request_id=rid,
    )


@dataclass
class _OpenAIOutput:
    """The output items read in order: the tool calls, the reasoning anchored to the item after
    it (CP1H-R8b), and every kept item in order for a reply the anchors cannot express."""

    calls: list[ToolCall] = field(default_factory=list)
    anchored: list[ProviderBlock] = field(default_factory=list)
    ordered: list[ProviderBlock] = field(default_factory=list)
    reordered: bool = False  # a message after a call, or reasoning before a later message
    refused: bool = False
    messages: int = 0

    def blocks(self) -> tuple[ProviderBlock, ...]:
        return tuple(self.ordered if self.reordered else self.anchored)


def _openai_message(item: Mapping[str, Any], texts: list[str], out: _OpenAIOutput) -> str:
    """One message item's text (each output_text part also goes to ``texts``); a refusal part
    sets ``out.refused`` and ends the item there."""
    content = item.get("content")
    if content is None:
        content = []
    if not isinstance(content, list):
        raise _BadReply("message content is not a list")
    parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "refusal":
            out.refused = True
            break
        if isinstance(part, dict) and part.get("type") == "output_text":
            parts.append(str(part.get("text", "")))
            texts.append(parts[-1])
    return "".join(parts)


def _openai_output(output: list[Any], texts: list[str], seen: list[Any]) -> _OpenAIOutput:
    out = _OpenAIOutput()
    waiting: list[dict[str, Any]] = []  # reasoning items not yet tied to the item after them
    for item in output:
        kind = item.get("type") if isinstance(item, dict) else None
        if kind == "reasoning":
            # CP1H-R8: kept whole. Without encrypted_content (store=false) the provider holds
            # no item to resolve, so such an item is not resent.
            encrypted = item.get("encrypted_content")
            if isinstance(encrypted, str) and encrypted:
                waiting.append(dict(item))
                out.ordered.append(ProviderBlock("openai", {"item": dict(item), "before": None}))
        elif kind == "function_call":
            call_id, name = _id(item, "call_id"), _id(item, "name")
            _anchor_reasoning(waiting, out.anchored, {"type": "function_call", "call_id": call_id})
            out.calls.append(_call(call_id, name, item.get("arguments"), seen))
            out.ordered.append(ProviderBlock("openai", {"function_call": call_id}))
        elif kind == "message":
            out.reordered = out.reordered or bool(out.calls) or bool(waiting and out.messages)
            _anchor_reasoning(waiting, out.anchored, {"type": "message"})
            text = _openai_message(item, texts, out)
            if out.refused:
                return out
            out.ordered.append(ProviderBlock("openai", {"message_text": text}))
            out.messages += 1
    _anchor_reasoning(waiting, out.anchored, None)  # nothing followed them: they go last
    return out


def _openai_stop(
    state: object, incomplete: Mapping[str, Any] | None, calls: list[ToolCall]
) -> StopReason:
    if calls:
        return "tool_use"
    if state == "completed":
        return "end"
    if state == "incomplete" and incomplete and incomplete.get("reason") == "max_output_tokens":
        return "max_tokens"
    return "other"


def _openai_outcome(
    status: int, data: dict[str, Any], texts: list[str], seen: list[Any], cut_as_turn: bool = False
) -> Turn | ProviderError:
    usage = _openai_usage(_sub(data, "usage"))
    model, rid = _str_or_none(data.get("model")), _str_or_none(data.get("id"))
    if data.get("error"):
        return _response_error(status, model, rid)
    output = data.get("output")
    if not isinstance(output, list):
        raise _BadReply("output is not a list")
    out = _openai_output(output, texts, seen)
    if out.refused:
        return _usage_error("Refusal", "the model refused", status, usage, model, rid)
    incomplete = _sub(data, "incomplete_details")
    state = data.get("status")
    if state == "incomplete" and not out.calls and not cut_as_turn:
        reason = incomplete.get("reason") if incomplete else None
        token = reason if isinstance(reason, str) and _ERROR_TYPE.fullmatch(reason) else "unknown"
        return _usage_error(REPLY_CUT, f"incomplete: {token}", status, usage, model, rid)
    stop = _openai_stop(state, incomplete, out.calls)
    return Turn(
        "".join(texts), tuple(out.calls), usage, stop, model, rid, status, None, out.blocks()
    )


# Anthropic Messages (SSE)

_LINE_BREAK = re.compile(r"\r\n|\r|\n")  # SSE lines end at LF, CR or CRLF only
_ERROR_TYPE = re.compile(r"[A-Za-z0-9_]{1,64}")


_TERMINAL_EVENTS = ("message_stop", "error")
_SIMPLE_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _open_string(data: str) -> str:
    """The decoded content of the JSON string left open at the end of ``data`` (a stream cut
    inside an event), without a partial escape; "" when no string is open. Field-agnostic."""
    start, i = -1, 0
    while i < len(data):
        if data[i] == "\\" and start >= 0:
            i += 6 if data[i + 1 : i + 2] == "u" else 2
            continue
        if data[i] == '"':
            start = -1 if start >= 0 else i + 1
        i += 1
    if start < 0:
        return ""
    raw, out, i = data[start:], [], 0
    while i < len(raw):
        if raw[i] != "\\":
            out.append(raw[i])
            i += 1
        elif raw[i + 1 : i + 2] in _SIMPLE_ESCAPES:
            out.append(_SIMPLE_ESCAPES[raw[i + 1]])
            i += 2
        elif raw[i + 1 : i + 2] == "u" and len(raw) >= i + 6 and _is_hex(raw[i + 2 : i + 6]):
            out.append(chr(int(raw[i + 2 : i + 6], 16)))
            i += 6
        elif i + 1 >= len(raw) or (raw[i + 1] == "u" and len(raw) < i + 6):
            break  # an escape cut in half: nothing of it is decoded
        else:
            out.append(raw[i])  # not a JSON escape: keep the text, a reader may still see it
            i += 1
    return "".join(out)


def _is_hex(text: str) -> bool:
    return len(text) == 4 and all(c in "0123456789abcdefABCDEF" for c in text)


def _sse_events(text: str, events: list[dict[str, Any]], after: list[Any]) -> str | None:
    """Decode the stream into ``events`` (up to and including the terminal event) and ``after``
    (everything decoded past it, kept only so it can be checked for a key). The caller passes
    the lists in, so events decoded before a ``_BadReply`` survive it. Returns None for a
    stream that ends on an event boundary, else the open string of the event the stream was
    cut inside (``after`` takes that one when it lies past the terminal event)."""
    data: list[str] = []

    def flush(final: bool) -> str | None:
        if not data:
            return None
        joined = "\n".join(data)
        data.clear()
        terminal = bool(events) and events[-1].get("type") in _TERMINAL_EVENTS
        try:
            event = load_json(joined)
        except TurnError:
            if final:
                return _open_string(joined)
            if terminal:
                return None  # past the terminal event nothing is meaning, only text to check
            raise _BadReply("an event's data is not JSON") from None
        if not isinstance(event, dict):
            if terminal:
                after.append(event)
                return None
            raise _BadReply("an event's data is not a JSON object")
        (after if terminal else events).append(event)
        return None

    for line in _LINE_BREAK.split(text):
        if not line:
            flush(final=False)
            continue
        name, _, value = line.partition(":")
        if name == "data":
            data.append(value.removeprefix(" "))
    cut = flush(final=True)  # a cut stream may end inside an event
    if cut is not None and events and events[-1].get("type") in _TERMINAL_EVENTS:
        after.append(cut)
        return None
    return cut


def _joined_deltas(events: list[Any]) -> list[str]:
    """Each delta field joined in order per content block: a key split across events past the
    terminal event, which no block holds, is still whole here."""
    joined: dict[str, str] = {}
    for event in events:
        delta = event.get("delta") if isinstance(event, dict) else None
        if isinstance(delta, dict):
            for field, value in delta.items():
                if field != "type" and isinstance(value, str):
                    slot = f"{event.get('index')!r}/{delta.get('type')!r}/{field}"
                    joined[slot] = joined.get(slot, "") + value
    return list(joined.values())


_ANTHROPIC_STOP: Mapping[str, StopReason] = {
    "end_turn": "end",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
}
_ANTHROPIC_NAMED_ERRORS: Mapping[str, str] = {
    "refusal": "Refusal",
    "pause_turn": "PauseTurn",
    "model_context_window_exceeded": "ContextWindowExceeded",
}
_THINKING_TYPES = ("thinking", "redacted_thinking")


def _anthropic_usage(raw: Mapping[str, Any]) -> Usage:
    creation = _sub(raw, "cache_creation")
    five = _count(creation, "ephemeral_5m_input_tokens")
    hour = _count(creation, "ephemeral_1h_input_tokens")
    written = _count(raw, "cache_creation_input_tokens")
    if written is None and five is not None and hour is not None:
        written = five + hour
    return Usage(
        input_tokens=_count(raw, "input_tokens"),
        cached_read_tokens=_count(raw, "cache_read_input_tokens"),
        cache_write_tokens=written,
        cache_write_5m_tokens=five,
        cache_write_1h_tokens=hour,
        output_tokens=_count(raw, "output_tokens"),
        reasoning_tokens=_count(_sub(raw, "output_tokens_details"), "thinking_tokens"),
    )


def _in_stream_error(
    event: Mapping[str, Any], status: int, message: Mapping[str, Any], redactor: Redactor
) -> ProviderError:
    err = event.get("error")
    err = err if isinstance(err, dict) else {}
    kind = err.get("type")
    error_class = kind if isinstance(kind, str) and _ERROR_TYPE.fullmatch(kind) else "StreamError"
    return ProviderError(
        ErrorKind.SENT_CHARGE_UNKNOWN,  # tokens may have been generated: the charge stays unknown
        redactor.text(error_class),
        _snippet(redactor, f"{err.get('type', 'error')}: {err.get('message', '')}"),
        status,
        reported_model=_str_or_none(message.get("model")),
        request_id=_str_or_none(message.get("id")),
    )


def _anthropic_text(blocks: Mapping[int, Mapping[str, Any]]) -> str:
    return "".join(
        str(blocks[index].get("text", ""))
        for index in sorted(blocks)
        if blocks[index].get("type") == "text"
    )


@dataclass
class _SseState:
    """One Anthropic stream as decoded so far. ``_parse_anthropic`` holds it, so its ``finally``
    still hands every string decoded or joined to the key scan, whatever way the mapper exits."""

    events: list[dict[str, Any]] = field(default_factory=list)
    after: list[Any] = field(default_factory=list)  # decoded past the terminal event
    blocks: dict[int, dict[str, Any]] = field(default_factory=dict)
    partial: dict[int, str] = field(default_factory=dict)  # open tool_use input JSON
    cut: str | None = None
    message: dict[str, Any] = field(default_factory=dict)
    usage_raw: dict[str, Any] = field(default_factory=dict)
    stop_reason: str | None = None
    saw_delta: bool = False

    def strings(self) -> list[Any]:
        """What the key scan must see: the events, the joined deltas, the blocks, and, for a cut
        stream, the open string of the cut event continuing every string so far."""
        found: list[Any] = [
            self.events,
            self.after,
            _joined_deltas([*self.events, *self.after]),
            self.blocks,
            self.partial,
            self.cut,
            _anthropic_text(self.blocks),
        ]
        if self.cut is not None:
            strings = [v for b in self.blocks.values() for v in b.values() if isinstance(v, str)]
            found.extend(s + self.cut for s in [*strings, *self.partial.values()])
        return found


_DELTA_FIELD: Mapping[str, str] = {
    "text_delta": "text",
    "thinking_delta": "thinking",
    "signature_delta": "signature",
}


def _parse_anthropic(
    status: int, text: str, redactor: Redactor, seen: list[Any], cut_as_turn: bool = False
) -> Turn | ProviderError:
    state = _SseState()
    try:
        state.cut = _sse_events(text, state.events, state.after)
        if not state.events and state.cut is None:
            raise _BadReply("no events in the stream")
        for event in state.events:
            if event.get("type") == "error":
                return _in_stream_error(event, status, state.message, redactor)
            _apply_event(state, event)
        return _anthropic_result(state, status, seen, cut_as_turn)
    finally:
        seen.extend(state.strings())


def _apply_event(state: _SseState, event: Mapping[str, Any]) -> None:
    kind, index = event.get("type"), event.get("index")
    if kind == "message_start" and isinstance(event.get("message"), dict):
        state.message = dict(event["message"])
        state.usage_raw.update(_sub(state.message, "usage") or {})
    elif kind == "message_delta":
        delta = event.get("delta")
        if isinstance(delta, dict):
            state.stop_reason = _str_or_none(delta.get("stop_reason")) or state.stop_reason
        state.usage_raw.update(_sub(event, "usage") or {})  # cumulative
        state.saw_delta = True
    elif isinstance(index, int):
        _apply_block_event(state, kind, index, event)


def _apply_block_event(
    state: _SseState, kind: object, index: int, event: Mapping[str, Any]
) -> None:
    blocks, partial = state.blocks, state.partial
    if kind == "content_block_start":
        block = event.get("content_block")
        if not isinstance(block, dict) or index in blocks:
            raise _BadReply(f"content block {index} starts twice or without a block")
        blocks[index] = dict(block)
        if block.get("type") == "tool_use":
            partial[index] = ""
    elif kind == "content_block_delta":
        _apply_delta(state, index, event.get("delta"))
    elif kind == "content_block_stop":
        if index not in blocks:
            raise _BadReply(f"stop for content block {index}, which has not started")
        if index in partial:
            blocks[index]["input_json"] = partial.pop(index) or "{}"


def _apply_delta(state: _SseState, index: int, delta: object) -> None:
    if index not in state.blocks or not isinstance(delta, dict):
        raise _BadReply(f"delta for content block {index}, which has not started")
    dtype = delta.get("type")
    name = _DELTA_FIELD.get(dtype) if isinstance(dtype, str) else None
    if dtype == "input_json_delta" and index in state.partial:
        state.partial[index] += str(delta.get("partial_json", ""))
    elif name is not None:
        block = state.blocks[index]
        block[name] = str(block.get(name) or "") + str(delta.get(name, ""))


def _anthropic_result(
    state: _SseState, status: int, seen: list[Any], cut_as_turn: bool
) -> Turn | ProviderError:
    """The outcome once every event before any error was applied."""
    if state.cut is not None:
        raise _BadReply("an event's data is not JSON")
    model, rid = _str_or_none(state.message.get("model")), _str_or_none(state.message.get("id"))
    if not state.saw_delta:
        return ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN,
            "StreamCut",
            "the stream ended before any usage event",
            status,
            reported_model=model,
            request_id=rid,
        )
    usage = _anthropic_usage(state.usage_raw)
    stop_reason = state.stop_reason
    if state.partial:
        error_class, detail = "StreamCut", "the stream ended inside a tool call"
    elif (named := _ANTHROPIC_NAMED_ERRORS.get(stop_reason or "")) is not None:
        error_class, detail = named, f"stop_reason {stop_reason}"
    else:
        calls, provider_blocks = _anthropic_content(state.blocks, seen)
        if stop_reason != "max_tokens" or calls or cut_as_turn:
            stop: StopReason = _ANTHROPIC_STOP.get(stop_reason or "", "other")
            text = _anthropic_text(state.blocks)
            return Turn(text, calls, usage, stop, model, rid, status, None, provider_blocks)
        error_class, detail = REPLY_CUT, "stop_reason max_tokens"
    return _usage_error(error_class, detail, status, usage, model, rid)


_RANK = {"thinking": 0, "redacted_thinking": 0, "text": 1, "tool_use": 2}


def _anthropic_content(
    blocks: Mapping[int, Mapping[str, Any]], seen: list[Any]
) -> tuple[tuple[ToolCall, ...], tuple[ProviderBlock, ...]]:
    """The tool calls and the blocks to resend. Thinking blocks are kept unchanged and in order.
    When the reply's content is not thinking, then text, then tool use (the order the next
    request rebuilds by default), the text blocks and tool-use markers are kept too, each at its
    place, so the resent turn is the reply as produced."""
    calls: list[ToolCall] = []
    kept: list[tuple[int, dict[str, Any]]] = []
    for index in sorted(blocks):
        block = blocks[index]
        kind = block.get("type")
        if kind in _THINKING_TYPES:
            kept.append((0, dict(block)))
        elif kind == "tool_use":
            call_id, name = _id(block, "id"), _id(block, "name")
            calls.append(_call(call_id, name, block.get("input_json", "{}"), seen))
            kept.append((2, {"type": "tool_use", "id": call_id}))
        elif kind == "text":
            kept.append((1, {"type": "text", "text": str(block.get("text", ""))}))
    ranks = [rank for rank, _ in kept]
    in_order = ranks == sorted(ranks)
    return tuple(calls), tuple(
        ProviderBlock("anthropic", data) for rank, data in kept if rank == 0 or not in_order
    )


# OpenRouter chat completions

_OPENROUTER_STOP: Mapping[str, StopReason] = {
    "stop": "end",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


def _parse_openrouter(
    status: int, text: str, seen: list[Any], cut_as_turn: bool = False
) -> Turn | ProviderError:
    data = _object(text)
    # nothing below changes it; the guard checks the whole decoded reply but for ciphertext
    seen.append(_blank_ciphertext("openrouter", data))
    model, rid = _str_or_none(data.get("model")), _str_or_none(data.get("id"))
    if data.get("error"):
        return _response_error(status, model, rid)
    raw_usage = _sub(data, "usage")
    billed = _openrouter_billed(raw_usage)
    usage = Usage(
        input_tokens=_count(raw_usage, "prompt_tokens"),
        cached_read_tokens=_count(_sub(raw_usage, "prompt_tokens_details"), "cached_tokens"),
        cache_write_tokens=_count(_sub(raw_usage, "prompt_tokens_details"), "cache_write_tokens"),
        output_tokens=_count(raw_usage, "completion_tokens"),
        reasoning_tokens=_count(_sub(raw_usage, "completion_tokens_details"), "reasoning_tokens"),
    )
    reply = _Reported(status, usage, model, rid, billed)
    try:
        return _openrouter_turn(data, reply, seen, cut_as_turn)
    except _BadReply as error:
        if billed is None:
            raise
        # the charge is reported exactly: the reply is refused but settles from usage.cost
        return _usage_error("UnparsableReply", str(error), status, usage, model, rid, billed)


def _openrouter_billed(raw_usage: Mapping[str, Any] | None) -> Decimal | None:
    cost_raw = None if raw_usage is None else raw_usage.get("cost")
    if cost_raw is None:
        return None
    if isinstance(cost_raw, bool) or not isinstance(cost_raw, int | Decimal):
        raise _BadReply("usage.cost is not a number")
    billed = Decimal(cost_raw)
    if not billed.is_finite() or billed < 0:
        raise _BadReply("usage.cost is not a non-negative number")
    return billed


@dataclass(frozen=True)
class _Reported:
    """What a reply reported before its content was read."""

    status: int
    usage: Usage
    model: str | None
    rid: str | None
    billed: Decimal | None


def _openrouter_calls(message: Mapping[str, Any], seen: list[Any]) -> tuple[ToolCall, ...]:
    tool_calls = message.get("tool_calls")
    if tool_calls is None:
        return ()
    if not isinstance(tool_calls, list):
        raise _BadReply("message.tool_calls is not a list")
    calls: list[ToolCall] = []
    for item in tool_calls:
        fn = item.get("function") if isinstance(item, dict) else None
        if not isinstance(fn, dict):
            raise _BadReply("a tool call has no function")
        call_id, name = _id(item, "id"), _id(fn, "name")
        calls.append(_call(call_id, name, fn.get("arguments"), seen))
    return tuple(calls)


def _openrouter_turn(
    data: Mapping[str, Any], reply: _Reported, seen: list[Any], cut_as_turn: bool
) -> Turn | ProviderError:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise _BadReply("choices is empty")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise _BadReply("choice has no message")
    calls = _openrouter_calls(message, seen)
    details = message.get("reasoning_details")
    if details is None:
        details = []
    if not isinstance(details, list) or not all(isinstance(d, dict) for d in details):
        raise _BadReply("reasoning_details is not a list of objects")
    content = message.get("content")
    stop = _OPENROUTER_STOP.get(str(choice.get("finish_reason")), "other")
    if stop == "max_tokens" and not calls and not cut_as_turn:
        return _usage_error(
            REPLY_CUT, "finish_reason length", reply.status, reply.usage, reply.model, reply.rid,
            reply.billed,
        )  # fmt: skip
    if calls and stop == "end":
        stop = "tool_use"
    return Turn(
        content if isinstance(content, str) else "",
        calls,
        reply.usage,
        stop,
        reply.model,
        reply.rid,
        reply.status,
        reply.billed,
        tuple(ProviderBlock("openrouter", dict(d)) for d in details),
    )
