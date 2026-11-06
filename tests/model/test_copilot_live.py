"""Seat verification for the Copilot adapter: paid, run by the owner at work, never in CI.

Run: ``uv run pytest tests/model/test_copilot_live.py -m live -q -s`` with COPILOT_GITHUB_TOKEN
and COPILOT_CLI_PATH set (docs/COPILOT.md). Skipped unless both are set. It uses the real
runtime and the real adapter, and prints the ``finishReason`` word of each reply and the
``billed_usd`` against the tokens' own price so the owner can read them.
"""

import asyncio
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.model.copilot_adapter import (
    ClientOptions,
    CopilotAdapter,
    real_client,
    runtime_environment,
)
from deploy_workflow.model.turn import Message, ModelSpec, ToolSpec, TurnRequest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not (os.environ.get("COPILOT_GITHUB_TOKEN") and os.environ.get("COPILOT_CLI_PATH")),
        reason="needs COPILOT_GITHUB_TOKEN and COPILOT_CLI_PATH in the environment",
    ),
]

SPEC = ModelSpec("copilot-sol-medium", "copilot", "gpt-6.1-sol", "medium")
RULING_TEXT = (
    "lifts: live-provider-pause\nby: user\ndate: 2026-11-06\nconfigs: copilot-sol-medium\n"
)
ECHO = ToolSpec(
    "echo",
    "Return the text it is given.",
    {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
)
SYSTEM = Message("system", "You are a test harness; follow the user's instruction exactly.")
USER = Message(
    "user",
    "In one turn, call the tool echo twice: once with text 'a' and once with text 'b'. "
    "Then reply with both results.",
)


async def listed_models(runtime: str, token: str, home: Path) -> list[dict[str, Any]]:
    client = real_client(ClientOptions(runtime, token, str(home), runtime_environment(os.environ)))
    try:
        await client.start()
        return await client.list_models()
    finally:
        await client.stop()


def test_the_runtime_lists_both_pinned_models_with_medium(tmp_path: Path) -> None:
    home = tmp_path / "list-home"
    home.mkdir()
    models = asyncio.run(
        listed_models(os.environ["COPILOT_CLI_PATH"], os.environ["COPILOT_GITHUB_TOKEN"], home)
    )
    by_id = {m.get("id"): m for m in models}
    for model in ("gpt-6.1-sol", "claude-opus-5.5"):
        assert model in by_id, f"{model} is not listed: {sorted(map(str, by_id))}"
        assert "medium" in (by_id[model].get("supportedReasoningEfforts") or []), model


def test_one_tool_exchange_on_the_seat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "rulings"
    root.mkdir()
    ruling = root / "seat-check.md"
    ruling.write_text(RULING_TEXT, encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # the adapter's per-call home is created under the cwd
    adapter = CopilotAdapter(SPEC, ruling, environ=os.environ, rulings_root=root)
    digest = "seatcheck"
    try:
        first_request = TurnRequest((SYSTEM, USER), (ECHO,), 1000, "medium")
        first = adapter.complete(
            first_request, invocation_digest=digest, call_index=0, reservation_id="r0"
        )
        assert first.kind == "ok" and first.turn is not None, (first.error_class, first.message)
        assert first.turn.stop_reason == "tool_use"
        assert len(first.turn.tool_calls) == 2, "the runtime must dispatch both calls in one turn"
        calls = first.turn.tool_calls
        assert all(c.name == "echo" for c in calls)
        history = (
            *first_request.messages,
            Message("assistant", first.turn.text, calls),
            *(Message("tool", f"result-{n}", tool_call_id=c.call_id) for n, c in zip("ab", calls)),
        )
        second = adapter.complete(
            TurnRequest(history, (ECHO,), 1000, "medium"),
            invocation_digest=digest,
            call_index=1,
            reservation_id="r1",
        )
        assert second.kind == "ok" and second.turn is not None, (second.error_class, second.message)
        assert second.turn.stop_reason == "end" and all(
            f"result-{n}" in second.turn.text for n in "ab"
        )
        assert second.turn.reported_model == "gpt-6.1-sol"
        for name, reply in (("first", first), ("second", second)):
            words = re.findall(rb'"finishReason":\s*"([^"]*)"', reply.raw or b"")
            print(f"{name} reply finishReason: {[w.decode() for w in words]}")
            usage, billed = reply.usage, reply.billed_usd
            assert usage is not None and billed is not None
            expected = (
                Decimal(usage.input_tokens or 0) * Decimal("2.00")
                + Decimal(usage.output_tokens or 0) * Decimal("10.00")
            ) / Decimal(1_000_000)
            print(f"{name} reply billed_usd {billed} vs token price {expected}")
            assert expected / 4 <= billed <= expected * 4, (name, billed, expected)
    finally:
        adapter.close()
