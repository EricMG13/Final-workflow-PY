"""What the credit model's modules share: the Decimal context, the notes,
cell arithmetic and where a balance at a date is read.

Pure: Decimal only, no I/O or display quantization. Arithmetic uses
the 38-significant-digit, half-even context defined in `_cells`.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
)

from deploy_vii.model.frame import Arithmetic, Cell, Column, SourceRef
from deploy_vii.model.registers import Cp1Registers, iso_date

CONTEXT = Context(
    prec=38,
    rounding=ROUND_HALF_EVEN,
    traps=[InvalidOperation, DivisionByZero, Overflow],
)
DIFFERS = "differs from CP-1 stated"
FOREIGN = "different currency, not converted"
RESIDUAL = "residual"
# An outflow CP-1 wrote positive, read as minus its absolute value.
SIGN_NORMALISED = "sign normalised"
# A derived period whose components are not distinct, contiguous and its
# exact span; or an LTM whose fiscal year does not meet its YTD and PYTD.
UNSPANNED = "components do not span the period"
# The source locator of a facility figure converted from another currency
# (`financial_adapter`): its decimal places are the rate's, not the issuer's.
CONVERTED = "facility-normalization"
ABSENT = Cell(None, "NOT_SOURCED")  # no row, or a key the frame has no cell for


def half_unit(amounts: Iterable[Decimal]) -> Decimal:
    """Half a unit in the finest last place any of `amounts` is written to,
    and never more than half a unit (0.5). A figure's own exponent is not its
    printed precision: a JSON parse drops trailing zeros (`1234.0` reads as
    `1234`) and an exponent form (`1.2E+3`) shows none, so the finest place
    among the figures compared stands in for it; a coarser tolerance is never
    inferred."""
    exponent = min((int(amount.as_tuple().exponent) for amount in amounts), default=0)
    return Decimal("0.5").scaleb(min(exponent, 0))


def beyond_rounding(
    stated: Decimal, host: Decimal, printed: Iterable[Decimal] | None = None
) -> bool:
    """Whether `host` differs from `stated` by more than half a unit in the
    finest last place among `stated` and `printed` (`half_unit`); `printed`
    are the printed figures `host` is built from, `host` itself by default
    (a sum is written to its finest part's place)."""
    places = (host,) if printed is None else tuple(printed)
    return abs(stated - host) > half_unit((stated, *places))


def no_negative_zero(value: Decimal) -> Decimal:
    """`value`, a negative zero (how "(0)" reads) as zero; exact."""
    return value.copy_abs() if value.is_zero() else value


def refs(sources: Iterable[SourceRef | None]) -> tuple[SourceRef, ...]:
    """The sources in order, each once."""
    return tuple(dict.fromkeys(s for s in sources if s is not None))


def join_notes(*notes: str | None) -> str | None:
    """The notes as one, each once in order (a note may already join
    several); None without any."""
    kept = dict.fromkeys(part for note in notes if note is not None for part in note.split("; "))
    return "; ".join(kept) if kept else None


def flipped(cell: Cell) -> bool:
    """Whether the cell's figure came from an outflow row CP-1 wrote
    positive."""
    return cell.note is not None and SIGN_NORMALISED in cell.note.split("; ")


def calc(parts: Iterable[tuple[Cell, int]], note: str | None = None) -> Cell:
    """The parts added (+1) or subtracted (-1); `COMPONENT_MISSING` when one
    has no value, noted with why each missing part is missing (its note).
    Noted `SIGN_NORMALISED` where a part was, then `note`."""
    cells = list(parts)
    arithmetic = Arithmetic("sum", tuple(cells))
    total = Decimal(0)
    sources: list[SourceRef] = []
    for cell, sign in cells:
        if cell.value is None:
            why = join_notes(*(part.note for part, _ in cells if part.value is None))
            return Cell(None, "COMPONENT_MISSING", note=why, arithmetic=arithmetic)
        total += cell.value * sign
        sources.extend(cell.sources)
    normalised = any(flipped(cell) for cell, _ in cells)
    noted = join_notes(SIGN_NORMALISED if normalised else None, note)
    return Cell(total, basis="CALCULATED", sources=refs(sources), note=noted, arithmetic=arithmetic)


def opening_date(column: Column) -> str | None:
    """The day before the column starts: its end date less its days; None
    where either is unknown, the end is not a `YYYY-MM-DD` date, the days are
    not positive, or no calendar day is that far back."""
    end = iso_date(column.end_date)
    if end is None or column.days is None or column.days < 1:
        return None
    opening = end.toordinal() - column.days
    return date.fromordinal(opening).isoformat() if opening >= 1 else None


def periods_at(regs: Cp1Registers, own: str | None, day: str | None) -> list[str | None]:
    """Where a balance at `day` is read: `own` first, then every period
    ending that day, in register order. None, no period, matches no row."""
    return [own, *(p.period_id for p in regs.periods if day and p.end_date == day)]
