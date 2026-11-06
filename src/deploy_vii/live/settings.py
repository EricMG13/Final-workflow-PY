"""The live settings the tool loop reads, as values (`LiveSettings`, `StepEffort`).

Task 8.0d defined three user-owned entries, each optional (absent: the earlier behaviour):
`tool_loop` (run the registry's tool-loop steps through `live.loop`), the per-step effort table
(`step_efforts`; without a row a step uses `default_effort`) and the completeness floor
(`completeness_floor`, statement lines per expected cell).

Task 8.12 (user decision "C", 24 Oct 2026) adds `extracted_coverage_min`: the `financials`
extracted-coverage floor (`live.tools.extracted_coverage`), a Decimal from 0 to 1 with at most
four decimal places (`valid_coverage_floor`); absent, the floor is off.

Review S07: the `settings/project.toml` loader (`load_settings`) had no caller and required a
provider key file (`credential_file`), against the project rule that provider keys come only
from the launching environment; the loader and the key-file fields are removed.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

# The effort values in escalation order (task 8.0d; OpenRouter's documented levels the catalog
# lists for the pool models).
EFFORT_LADDER = ("low", "medium", "high", "xhigh", "max")
# Escalation never passes this level unless a step's row names a higher ceiling.
DEFAULT_CEILING = "high"

# Task 8.12: the coverage a cell shows has four places (`live.tools.COVERAGE_PLACES`).
COVERAGE_FLOOR_PLACES = 4


class SettingsError(ValueError):
    """A settings value is not usable (an effort off `EFFORT_LADDER`, a ceiling below it)."""


@dataclass(frozen=True)
class CandidateSetting:
    key: str
    model_id: str
    resolution: str


@dataclass(frozen=True)
class RecurringCaps:
    e1_per_case: Decimal
    e2_per_milestone: Decimal
    e3_per_week: Decimal
    cumulative_ceiling: Decimal


@dataclass(frozen=True)
class StepEffort:
    """A step's effort and the highest level its one-level escalation may reach (task 8.0d)."""

    effort: str
    ceiling: str

    def __post_init__(self) -> None:
        for value in (self.effort, self.ceiling):
            if value not in EFFORT_LADDER:
                raise SettingsError(f"effort {value!r} is not one of {', '.join(EFFORT_LADDER)}")
        if EFFORT_LADDER.index(self.ceiling) < EFFORT_LADDER.index(self.effort):
            raise SettingsError(f"ceiling {self.ceiling} is below effort {self.effort}")

    @classmethod
    def of(cls, effort: str, ceiling: str | None = None) -> "StepEffort":
        """`ceiling` defaults to `high`, or to `effort` when that is already above it."""
        if ceiling is None and effort in EFFORT_LADDER:
            top = max(EFFORT_LADDER.index(effort), EFFORT_LADDER.index(DEFAULT_CEILING))
            ceiling = EFFORT_LADDER[top]
        return cls(effort, DEFAULT_CEILING if ceiling is None else ceiling)

    def escalated(self) -> str:
        """One level above `effort`, never above `ceiling` (deterministic)."""
        level = min(EFFORT_LADDER.index(self.effort) + 1, EFFORT_LADDER.index(self.ceiling))
        return EFFORT_LADDER[level]


@dataclass(frozen=True)
class LiveSettings:
    # Measured lower bound on request-body bytes per prompt token (decision 0008, MC-10).
    prompt_bytes_per_token_lower_bound: Decimal
    artifact_root: Path
    default_effort: str
    complex_effort: str
    candidates: tuple[CandidateSetting, ...]
    caps: RecurringCaps
    model_calls_in_ci: bool
    tool_loop: bool = False
    step_efforts: Mapping[str, StepEffort] = field(default_factory=dict)
    completeness_floor: int | None = None  # statement lines per expected cell; None: no floor
    # Task 8.12: the least coverage of a cell's extracted statement lines; None: no floor.
    extracted_coverage_min: Decimal | None = None

    def step_effort(self, step_id: str) -> StepEffort:
        """The step's row of the effort table, else `default_effort` (`StepEffort.of`)."""
        return self.step_efforts.get(step_id) or StepEffort.of(self.default_effort)


def valid_coverage_floor(value: object) -> bool:
    """Whether `value` is a usable extracted-coverage floor: a finite Decimal from 0 to 1 with
    at most `COVERAGE_FLOOR_PLACES` decimal places (task 8.12)."""
    if not isinstance(value, Decimal) or not value.is_finite():
        return False
    exponent = value.as_tuple().exponent
    return isinstance(exponent, int) and exponent >= -COVERAGE_FLOOR_PLACES and 0 <= value <= 1
