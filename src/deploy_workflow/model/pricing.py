"""Dated per-million-token price table, reservation and charge (money code).

No float touches money: every amount is a ``Decimal`` built from an ``int`` or a ``str``.

Provider-reports table (what each provider returns, so what a charge can be):

=========== ============================== ==========
provider    reports                        cost_status
=========== ============================== ==========
openai      tokens only                    computed
anthropic   tokens only                    computed
openrouter  tokens and ``usage.cost``      billed
copilot     tokens and the runtime's cost  billed
=========== ============================== ==========

Offline (a recorded call) is always priced from the recording's ``Usage`` with ``PRICES`` and is
``computed``; a ``billed_usd`` on a recorded turn is ignored there because no money moves.
Live, a turn that carries ``billed_usd`` is ``billed``; otherwise it is ``computed``, and an
OpenRouter or Copilot call without a reported cost has an unknown charge. Offline replay of a
Copilot recording is therefore always unknown, by design: its charge is the runtime's reported
cost, and token rates would only size holds.

Offline deepseek token pricing treats prompt tokens as including cached reads (OpenAI-style),
because OpenRouter's usage schema is OpenAI-compatible; this is not verified against a live reply.

A ``None`` count that the provider documents as reported makes the charge unknown, never a
partial charge.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

from deploy_workflow.model.turn import CONFIG_PROVIDERS, Usage

PRICES_AS_OF = date(2026, 10, 31)  # provider-docs fetch date
COPILOT_PRICES_AS_OF = date(2026, 11, 6)  # GitHub "Models and pricing" fetch date
CostStatus = Literal["computed", "billed", "unknown"]


class PricingError(ValueError):
    """A price, count or request that money code refuses."""


class NoPrice(PricingError):
    """The configuration is not in the price table."""


class ContextTooLong(PricingError):
    """The request-token bound exceeds the pricing table's supported context ceiling."""


def _money(name: str, value: object) -> Decimal:
    """A Decimal from an int or Decimal only; a float, bool or str-less guess is refused."""
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        raise PricingError(f"{name} must be an int or Decimal, not {type(value).__name__}")
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0:
        raise PricingError(f"{name} must be finite and non-negative")
    return amount


def _count(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PricingError(f"{name} must be a non-negative int")
    return value


@dataclass(frozen=True)
class ModelPrice:
    """USD per million tokens. ``cache_write`` is the rate reservations use for input."""

    input: Decimal
    output: Decimal
    cache_write: Decimal
    cached_read: Decimal | None = None
    cache_write_5m: Decimal | None = None  # Anthropic only
    cache_write_1h: Decimal | None = None  # Anthropic only
    # Legacy standard-tier boundary for prices without a long-context tier.
    max_input_tokens: int | None = None
    cache_write_listed: bool = (
        True  # False: ``cache_write`` only reserves; a charge needing it is unknown
    )
    long_context_after: int | None = None
    long_input: Decimal | None = None
    long_cached_read: Decimal | None = None
    long_cache_write: Decimal | None = None
    long_output: Decimal | None = None
    max_context_tokens: int | None = None
    reservation_context_tokens: int | None = None
    # Holds price output at least this many tokens: a runtime that cannot enforce the request's
    # max_output_tokens can charge up to the model maximum. None: the request cap binds.
    reservation_output_tokens: int | None = None

    def __post_init__(self) -> None:
        for name in ("input", "output", "cache_write"):
            object.__setattr__(self, name, _money(name, getattr(self, name)))
        for name in ("cached_read", "cache_write_5m", "cache_write_1h"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _money(name, value))
        for name in ("long_input", "long_cached_read", "long_cache_write", "long_output"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _money(name, value))
        if self.max_input_tokens is not None:
            _count("max_input_tokens", self.max_input_tokens)
        for name in (
            "long_context_after",
            "max_context_tokens",
            "reservation_context_tokens",
            "reservation_output_tokens",
        ):
            value = getattr(self, name)
            if value is not None:
                _count(name, value)
        if self.reservation_context_tokens is not None and (
            self.max_context_tokens is None
            or self.reservation_context_tokens > self.max_context_tokens
        ):
            raise PricingError("reservation context must fit within a supported context")


@dataclass(frozen=True)
class Priced:
    usd: Decimal | None  # None exactly when cost_status is "unknown"
    cost_status: CostStatus


_UNKNOWN = Priced(None, "unknown")

_SOL = ModelPrice(
    input=Decimal("2.00"),
    cached_read=Decimal("0.10"),
    # the 30-minute write rate: the OpenAI request pins ``prompt_cache_options`` to ttl "30m"
    # (``providers.OPENAI_PROMPT_CACHE_OPTIONS``, PF-R6); source:
    # cases/pricing/openai-sol-cache-write.json
    cache_write=Decimal("2.50"),
    output=Decimal("10.00"),
    # OpenAI applies long-context prices to the whole request above 272K input tokens.
    max_input_tokens=272_000,
    long_context_after=272_000,
    long_input=Decimal(4),
    long_cached_read=Decimal("0.20"),
    long_cache_write=Decimal(5),
    long_output=Decimal(15),
    max_context_tokens=1_050_000,
    reservation_context_tokens=1_050_000,
)
PRICES: Mapping[str, ModelPrice] = MappingProxyType(
    {
        "sol-medium": _SOL,
        "sol-high": _SOL,
        "opus-medium": ModelPrice(
            input=Decimal(4),
            cached_read=Decimal("0.20"),
            cache_write=Decimal(8),  # reserve at the 1 h rate
            cache_write_5m=Decimal(5),
            cache_write_1h=Decimal(8),
            output=Decimal(20),
        ),
        "deepseek-max": ModelPrice(
            input=Decimal("0.45"),  # highest listed endpoint
            cached_read=Decimal("0.009"),
            cache_write=Decimal("0.45"),  # none listed: reserved at input
            output=Decimal("1.80"),
        ),
        # GitHub "Models and pricing", fetched 2026-11-06 (COPILOT_PRICES_AS_OF), lists _SOL's
        # rates, long-context threshold and context ceiling (USD per 1M tokens); the hold adds the
        # model maximum, cases/pilot-fixes/limits.json documented_max_output_tokens.
        # test_copilot_table_rates pins every field, so a change to _SOL is checked against it.
        "copilot-sol-medium": replace(_SOL, reservation_output_tokens=128_000),
        # same source; Copilot lists one write rate (5), no 5 m / 1 h split; the hold uses
        # Anthropic's 1 h rate (8) because the runtime's cache TTL is unverified
        "copilot-opus-medium": ModelPrice(
            input=Decimal(4),
            cached_read=Decimal("0.20"),
            cache_write=Decimal(8),
            output=Decimal(20),
            # the model maximum, cases/pilot-fixes/limits.json documented_max_output_tokens
            reservation_output_tokens=128_000,
        ),
    }
)
if set(PRICES) != set(CONFIG_PROVIDERS):
    raise RuntimeError("PRICES and CONFIG_PROVIDERS must name the same configurations")


def price_of(config_id: str) -> ModelPrice:
    try:
        return PRICES[config_id]
    except KeyError:
        raise NoPrice(f"no price for configuration {config_id!r}") from None


def reservation_usd(price: ModelPrice, input_tokens: int, max_output: int) -> Decimal:
    """Upper bound on a call: every input token at the dearer of input and cache-write rate,
    plus max_output at the output rate. Unquantised."""
    n_in, n_out = _count("input_tokens", input_tokens), _count("max_output", max_output)
    if price.max_input_tokens is not None and n_in > price.max_input_tokens:
        raise ContextTooLong(f"{n_in} input tokens is over the {price.max_input_tokens} listed")
    top = max(price.input, price.cache_write)
    return (n_in * top).scaleb(-6) + (_held_output(price, n_out) * price.output).scaleb(-6)


def _held_output(price: ModelPrice, max_output: int) -> int:
    """Output tokens a hold prices: the request cap, or the model maximum where that is set."""
    floor = price.reservation_output_tokens
    return max_output if floor is None else max(max_output, floor)


def request_reservation_usd(price: ModelPrice, input_bound: int, max_output: int) -> Decimal:
    """Pre-send hold, widened to the configured conservative context ceiling when needed."""
    bound = _count("input_bound", input_bound)
    if price.reservation_context_tokens is None:
        return reservation_usd(price, bound, max_output)
    if bound > price.reservation_context_tokens:
        raise ContextTooLong(
            f"{bound} input-token bound is over the {price.reservation_context_tokens} supported"
        )
    ceiling = price.reservation_context_tokens
    if price.long_context_after is not None and any(
        rate is None
        for rate in (
            price.long_input,
            price.long_cached_read,
            price.long_cache_write,
            price.long_output,
        )
    ):
        raise PricingError("reservation context has an incomplete long-context price")
    rates = tuple(
        rate
        for rate in (
            price.input,
            price.cached_read,
            price.cache_write,
            price.long_input,
            price.long_cached_read,
            price.long_cache_write,
        )
        if rate is not None
    )
    if not rates:
        raise PricingError("reservation context has no input price")
    top = max(rates)
    output = max(
        price.output,
        price.long_output if price.long_output is not None else price.output,
    )
    return (ceiling * top).scaleb(-6) + (
        _held_output(price, _count("max_output", max_output)) * output
    ).scaleb(-6)


def _openai_like(price: ModelPrice, usage: Usage) -> Decimal | None:
    """Input includes cached reads and cache writes (counted once); output includes reasoning.
    Only input and output are required: a partial usage is unknown, never a partial charge."""
    n_in, n_out = usage.input_tokens, usage.output_tokens
    if n_in is None or n_out is None or price.cached_read is None:
        return None
    cached = usage.cached_read_tokens or 0  # absent: all at the input rate, never an undercharge
    written = usage.cache_write_tokens or 0  # input_tokens_details.cache_write_tokens; absent: none
    fresh = n_in - cached - written
    if fresh < 0 or (written and not price.cache_write_listed):
        return None
    threshold = price.long_context_after
    is_long = threshold is not None and n_in > threshold
    input_rate = price.long_input if is_long else price.input
    read_rate = price.long_cached_read if is_long else price.cached_read
    write_rate = price.long_cache_write if is_long else price.cache_write
    output_rate = price.long_output if is_long else price.output
    if input_rate is None or read_rate is None or write_rate is None or output_rate is None:
        return None
    return (
        fresh * input_rate + cached * read_rate + written * write_rate + n_out * output_rate
    ).scaleb(-6)


def _anthropic(price: ModelPrice, usage: Usage) -> Decimal | None:
    """Input excludes cache reads and writes; the 5 m and 1 h writes have their own rates."""
    n_in, n_out, cached = usage.input_tokens, usage.output_tokens, usage.cached_read_tokens
    if n_in is None or n_out is None or cached is None or price.cached_read is None:
        return None
    five, hour, written = (
        usage.cache_write_5m_tokens,
        usage.cache_write_1h_tokens,
        usage.cache_write_tokens,
    )
    if five is not None and hour is not None:
        if written is not None and written != five + hour:
            return None
    elif written == 0 and five in (None, 0) and hour in (None, 0):
        five = hour = 0
    else:
        return None
    if (five and price.cache_write_5m is None) or (hour and price.cache_write_1h is None):
        return None
    write_cost = Decimal(0)
    if five and price.cache_write_5m is not None:
        write_cost += five * price.cache_write_5m
    if hour and price.cache_write_1h is not None:
        write_cost += hour * price.cache_write_1h
    return (
        n_in * price.input + cached * price.cached_read + write_cost + n_out * price.output
    ).scaleb(-6)


def price_usage(
    config_id: str,
    usage: Usage,
    billed_usd: Decimal | None = None,
    *,
    offline: bool = False,
) -> Priced:
    """The charge for one sent call. ``usd`` is None (cost_status "unknown") when it cannot be
    known. ``offline`` prices a recording from its tokens and ignores ``billed_usd``."""
    provider = CONFIG_PROVIDERS.get(config_id)
    price = price_of(config_id)
    if billed_usd is not None and not offline:
        return Priced(_money("billed_usd", billed_usd), "billed")
    if provider in ("openrouter", "copilot") and not offline:
        return _UNKNOWN  # the charge is usage.cost only
    usd = computed_usd(provider, price, usage)
    return _UNKNOWN if usd is None else Priced(usd, "computed")


def computed_usd(provider: str | None, price: ModelPrice, usage: Usage) -> Decimal | None:
    """The token-based charge, or None when a needed count is absent or inconsistent. Input over
    the context the table has rates for is unknown: it is never priced at the standard rates."""
    limit = (
        price.max_context_tokens if price.max_context_tokens is not None else price.max_input_tokens
    )
    if usage.input_tokens is not None and limit is not None and usage.input_tokens > limit:
        return None
    if provider == "copilot":
        return None  # the charge is the runtime's reported cost (billed_usd) only
    if provider == "anthropic":
        return _anthropic(price, usage)
    if provider == "openrouter" and usage.cache_write_tokens:
        return None  # offline only: no cache-write rate is listed
    # openai; openrouter offline (prompt tokens include cached reads)
    return _openai_like(price, usage)


def money_text(amount: Decimal) -> str:
    """Fixed-point text with no exponent."""
    if not isinstance(amount, Decimal) or not amount.is_finite():
        raise PricingError("money_text needs a finite Decimal")
    return format(amount, "f")


def refusal_values() -> tuple[Decimal, Decimal, CostStatus]:
    """(reserved, settled, cost_status) of a call refused before any send."""
    return Decimal(0), Decimal(0), "computed"
