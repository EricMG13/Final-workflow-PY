"""S16 review: provider mappers, transport and pricing at the paid-execution boundary.

No network, no provider: fake connections and literal reply bodies. Expected amounts are written
out by hand (per-million rates times literal token counts), not computed by production code.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model.pricing import Priced, price_usage
from deploy_workflow.model.providers import (
    ErrorKind,
    ProviderError,
    build,
    error_from_transport,
    parse,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import (
    ConnectTimeout,
    NotConnected,
    Request,
    TransportError,
    https_transport,
)
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    ProviderBlock,
    ToolCall,
    Turn,
    TurnRequest,
    Usage,
)

KEY = "sk-proj-S16EXACTKEYVALUE000000000000"
OPUS = ModelSpec("opus-medium", "anthropic", "claude-opus-5-5", "medium")
SOL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")


# ---------------------------------------------------------------- connect failures


class _Conn:
    def __init__(self, error: BaseException) -> None:
        self.error, self.sent, self.closed, self.sock = error, 0, False, None

    def connect(self) -> None:
        raise self.error

    def request(self, *_a: object) -> None:  # pragma: no cover - never reached
        self.sent += 1

    def getresponse(self) -> Any:  # pragma: no cover - never reached
        raise AssertionError("no response without a connection")

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("error", "kind"),
    [(ConnectionRefusedError("x"), NotConnected), (TimeoutError(), ConnectTimeout)],
)
def test_a_failed_connect_sends_nothing_and_is_not_sent(
    error: BaseException, kind: type[TransportError]
) -> None:
    conn = _Conn(error)
    with pytest.raises(kind) as info:
        https_transport(
            Request("https://api.example/v1", {}, b"{}"), connection_factory=lambda *_: conn
        )
    assert conn.sent == 0 and conn.closed
    assert isinstance(info.value, NotConnected)
    outcome = error_from_transport("openai", info.value, Redactor())
    assert isinstance(outcome, ProviderError)
    assert outcome.kind is ErrorKind.NOT_SENT and outcome.error_class == "NotConnected"


def test_a_failure_after_the_connection_stays_unknown() -> None:
    outcome = error_from_transport("openai", TransportError("network error: OSError"), Redactor())
    assert isinstance(outcome, ProviderError)
    assert outcome.kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_the_live_adapter_reports_a_failed_connect_as_not_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rulings = tmp_path / "rulings"
    rulings.mkdir()
    ruling = rulings / "lift.md"
    ruling.write_text(
        "lifts: live-provider-pause\nby: user\ndate: 2026-11-01\nconfigs: sol-medium\n"
    )
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", rulings)

    def transport(_request: Request) -> Any:
        raise NotConnected("connection failed: ConnectionRefusedError")

    live = adapter_module.LiveAdapter(
        SOL, ruling, transport=transport, environ={"OPENAI_API_KEY": KEY}
    )
    request = TurnRequest((Message("user", "hi"),), (), 100, "medium")
    reply = live.complete(request, invocation_digest="d" * 64, call_index=0, reservation_id="r")
    assert reply.kind == "not_sent" and reply.error_class == "NotConnected"
    assert reply.http_status is None and reply.usage is None


# ---------------------------------------------------------------- pricing


def _sol_usage(**details: int) -> Usage:
    body = {
        "id": "r",
        "model": "gpt-6.1-sol",
        "status": "completed",
        "usage": {
            "input_tokens": 5162,
            "input_tokens_details": {"cached_tokens": 0, **details},
            "output_tokens": 227,
        },
        "output": [{"type": "function_call", "call_id": "c", "name": "t", "arguments": "{}"}],
    }
    turn = parse("openai", 200, json.dumps(body).encode(), {}, Redactor())
    assert isinstance(turn, Turn)
    return turn.usage


def test_an_absent_openai_write_count_is_an_unknown_charge_live() -> None:
    # cases/pricing/openai-sol-cache-write.json pilot: 3 fresh at 2.00, 5159 written at 2.50,
    # 227 output at 10.00 per million = 0.00000600 + 0.01289750 + 0.00227000
    assert price_usage("sol-medium", _sol_usage(cache_write_tokens=5159)) == Priced(
        Decimal("0.01517350"), "computed"
    )
    assert price_usage("sol-medium", _sol_usage()) == Priced(None, "unknown")
    # a reported zero is a zero: 5162 at 2.00 + 227 at 10.00
    assert price_usage("sol-medium", _sol_usage(cache_write_tokens=0)) == Priced(
        Decimal("0.01259400"), "computed"
    )


def test_deepseek_written_tokens_stay_unknown_offline() -> None:
    usage = Usage(input_tokens=100, cached_read_tokens=0, cache_write_tokens=10, output_tokens=1)
    assert price_usage("deepseek-max", usage, offline=True) == Priced(None, "unknown")


# ---------------------------------------------------------------- Anthropic request


def test_the_anthropic_key_goes_in_x_api_key() -> None:
    request = TurnRequest((Message("user", "hi"),), (), 1000, "medium")
    built = build(OPUS, request, KEY)
    assert built.headers["x-api-key"] == KEY
    assert "Authorization" not in built.headers
    assert built.headers["anthropic-version"] == "2026-10-21"
    assert KEY.encode() not in built.body


# ---------------------------------------------------------------- ciphertext and the exact key


def _openai_with_cipher(cipher: str) -> bytes:
    return json.dumps(
        {
            "id": "r",
            "model": "gpt-6.1-sol",
            "status": "completed",
            "usage": {"input_tokens": 5, "output_tokens": 1},
            "output": [
                {"type": "reasoning", "summary": [], "encrypted_content": cipher},
                {"type": "function_call", "call_id": "c", "name": "t", "arguments": "{}"},
            ],
        }
    ).encode()


def test_an_exact_key_inside_ciphertext_is_key_reflected() -> None:
    redactor = Redactor([KEY])
    outcome = parse("openai", 200, _openai_with_cipher("gAAA" + KEY + "zzz"), {}, redactor)
    assert isinstance(outcome, ProviderError) and outcome.error_class == "KeyReflected"


def test_a_chance_key_shape_inside_ciphertext_is_still_exempt() -> None:
    cipher = "gAAA_sk-" + "A" * 30
    outcome = parse("openai", 200, _openai_with_cipher(cipher), {}, Redactor([KEY]))
    assert isinstance(outcome, Turn)
    assert outcome.provider_blocks[0].data["item"]["encrypted_content"] == cipher


# ---------------------------------------------------------------- OpenRouter scalar tool_calls


@pytest.mark.parametrize("scalar", [1, True, 2.5, "x"])
def test_scalar_openrouter_tool_calls_are_unparsable_not_a_crash(scalar: object) -> None:
    body = {
        "id": "g",
        "model": "deepseek/deepseek-v4",
        "usage": {"prompt_tokens": 5, "completion_tokens": 1, "cost": 0.001},
        "choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": scalar}}],
    }
    outcome = parse("openrouter", 200, json.dumps(body).encode(), {}, Redactor())
    assert isinstance(outcome, ProviderError) and outcome.error_class == "UnparsableReply"
    # the reported cost is exact, so the refused reply still settles from it
    assert outcome.kind is ErrorKind.SENT_CHARGE_USAGE
    assert outcome.billed_usd == Decimal("0.001")


def test_scalar_tool_calls_without_a_cost_stay_unknown() -> None:
    body = {
        "id": "g",
        "model": "deepseek/deepseek-v4",
        "choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": 1}}],
    }
    outcome = parse("openrouter", 200, json.dumps(body).encode(), {}, Redactor())
    assert isinstance(outcome, ProviderError)
    assert outcome.error_class == "UnparsableReply"
    assert outcome.kind is ErrorKind.SENT_CHARGE_UNKNOWN and outcome.billed_usd is None


# ---------------------------------------------------------------- order of resent blocks


def _sse(*events: dict[str, Any]) -> bytes:
    return "".join(f"event: x\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def _block(index: int, block: dict[str, Any], delta: dict[str, Any] | None) -> list[dict[str, Any]]:
    events = [{"type": "content_block_start", "index": index, "content_block": block}]
    if delta is not None:
        events.append({"type": "content_block_delta", "index": index, "delta": delta})
    events.append({"type": "content_block_stop", "index": index})
    return events


def test_interleaved_anthropic_blocks_are_resent_in_their_order() -> None:
    thinking_a = {"type": "thinking", "thinking": "A", "signature": "sa"}
    thinking_b = {"type": "thinking", "thinking": "B", "signature": "sb"}
    body = _sse(
        {"type": "message_start", "message": {"id": "m", "model": "claude-opus-5-5", "usage": {}}},
        *_block(0, thinking_a, None),
        *_block(1, {"type": "text", "text": ""}, {"type": "text_delta", "text": "between"}),
        *_block(2, thinking_b, None),
        *_block(
            3,
            {"type": "tool_use", "id": "t1", "name": "read", "input": {}},
            {"type": "input_json_delta", "partial_json": '{"p": 1}'},
        ),
        {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use"},
            "usage": {"input_tokens": 1, "cache_read_input_tokens": 0, "output_tokens": 1},
        },
        {"type": "message_stop"},
    )
    turn = parse("anthropic", 200, body, {}, Redactor())
    assert isinstance(turn, Turn) and turn.text == "between"
    history = (
        Message("user", "go"),
        Message("assistant", turn.text, turn.tool_calls, provider_blocks=turn.provider_blocks),
        Message("tool", "page", tool_call_id="t1"),
    )
    sent = json.loads(build(OPUS, TurnRequest(history, (), 1000, "medium"), KEY).body)
    assert sent["messages"][1]["content"] == [
        thinking_a,
        {"type": "text", "text": "between"},
        thinking_b,
        {"type": "tool_use", "id": "t1", "name": "read", "input": {"p": 1}},
    ]


def test_plain_order_keeps_only_the_thinking_blocks() -> None:
    blocks = (ProviderBlock("anthropic", {"type": "thinking", "thinking": "A", "signature": "s"}),)
    history = (
        Message("user", "go"),
        Message("assistant", "hi", (ToolCall("t1", "read", {}),), provider_blocks=blocks),
    )
    sent = json.loads(build(OPUS, TurnRequest(history, (), 1000, "medium"), KEY).body)
    assert [b["type"] for b in sent["messages"][1]["content"]] == ["thinking", "text", "tool_use"]


def test_reasoning_between_two_openai_messages_keeps_its_place() -> None:
    r1 = {"type": "reasoning", "id": "rs1", "summary": [], "encrypted_content": "c1"}
    r2 = {"type": "reasoning", "id": "rs2", "summary": [], "encrypted_content": "c2"}
    body = {
        "id": "r",
        "model": "gpt-6.1-sol",
        "status": "completed",
        "usage": {"input_tokens": 5, "output_tokens": 1},
        "output": [
            r1,
            {"type": "message", "content": [{"type": "output_text", "text": "one"}]},
            r2,
            {"type": "message", "content": [{"type": "output_text", "text": "two"}]},
            {"type": "function_call", "call_id": "f1", "name": "t", "arguments": "{}"},
        ],
    }
    turn = parse("openai", 200, json.dumps(body).encode(), {}, Redactor())
    assert isinstance(turn, Turn) and turn.text == "onetwo"
    history = (
        Message("user", "go"),
        Message("assistant", turn.text, turn.tool_calls, provider_blocks=turn.provider_blocks),
    )
    sent = json.loads(build(SOL, TurnRequest(history, (), 1000, "medium"), KEY).body)
    assert sent["input"][1:] == [
        r1,
        {"role": "assistant", "content": "one"},
        r2,
        {"role": "assistant", "content": "two"},
        {"type": "function_call", "call_id": "f1", "name": "t", "arguments": "{}"},
    ]
