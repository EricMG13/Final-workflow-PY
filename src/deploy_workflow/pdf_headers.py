"""Mapping-only recovery of printed PDF period headings.

This module deliberately returns only synthetic header rows. It never edits the
extracted table or its evidence.
"""

from __future__ import annotations

import re
from datetime import date
from itertools import pairwise
from typing import Literal

MONTH_NAMES = (
    *("January", "February", "March", "April", "May", "June", "July", "August"),
    *("September", "October", "November", "December"),
)
# A 19xx/20xx year standing alone (no adjacent digit); shared with statement_lines.
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_MONTH = "|".join(MONTH_NAMES)
_YEARS = YEAR
_DATE = re.compile(
    rf"(?i)({_MONTH})\s+(\d{{1,2}}),?\s+(\d{{4}})|(?<!\d)(\d{{1,2}})\s+({_MONTH})\s+(\d{{4}})"
)
_MONTH_DAY = re.compile(rf"(?i)({_MONTH})\s+(\d{{1,2}})|(?<!\d)(\d{{1,2}})\s+({_MONTH})")
_DURATION = re.compile(
    r"(?i)(?<![A-Za-z])(?:(three|six|nine|twelve)\s+months?|(?:fiscal\s+)?years?)\s+ended\b"
)
_TITLE = re.compile(
    r"(?i)^\s*(?:(?:condensed|consolidated)\s+)*(?:"
    r"balance\s+sheets?|financial\s+position|income\s+statement|"
    r"statements?\s+of\s+(?:operations|income|cash\s+flows?|"
    r"comprehensive\s+income(?:\s*\(loss\))?|financial\s+position|profit)|"
    r"statement\s+of\s+(?:operations|income|cash\s+flows?|financial\s+position))"
    r"(?:\s*\([^)]*\))?\s*$"
)
_TITLE_STEM = re.compile(r"(?i)^\s*(?:(?:condensed|consolidated)\s+)*statements?\s*$")
_TITLE_CONTINUATION = re.compile(
    r"(?i)^\s*of\s+(?:profit|financial\s+position|comprehensive\s+income|income|cash\s+flows?)\b"
)
_MONTHS = {name.lower(): number for number, name in enumerate(MONTH_NAMES, 1)}
_NOT_A_YEAR_CELL = re.compile(rf"(?i)\b(?:notes?|references?|{_MONTH})\b")
_Header = tuple[str, ...]


def _cells(line: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s{2,}", line.strip()) if part.strip()]


def _iso(month: str, day: str, year: str) -> str | None:
    try:
        return date(int(year), _MONTHS[month.lower()], int(day)).isoformat()
    except (ValueError, KeyError):
        return None


def _duration_labels(line: str) -> list[str] | None:
    """Parse whole supported duration phrases plus the adopted decorations."""
    matches = list(_DURATION.finditer(line))
    if not matches:
        return None
    residue = line
    for found in reversed(matches):
        residue = residue[: found.start()] + " " + residue[found.end() :]
    residue = re.sub(r"(?i)\bfor\s+the\b", " ", residue)
    residue = re.sub(rf"(?i)\b(?:{_MONTH})\b", " ", residue)
    residue = re.sub(r"\d+|[^A-Za-z]+", " ", residue)
    if residue.strip():
        return None
    return [match.group(1).title() if match.group(1) else "Year" for match in matches]


def _statement_title_start(lines: list[str]) -> int | None:
    """Find a recognized title, including the common two-line IFRS title."""
    titles = []
    for index, line in enumerate(lines):
        if _TITLE.fullmatch(line) or (
            _TITLE_STEM.fullmatch(line)
            and index + 1 < len(lines)
            and _TITLE_CONTINUATION.match(lines[index + 1])
        ):
            titles.append(index)
    return titles[-1] if titles else None


def _mdy(found: tuple[str, ...]) -> tuple[str, str, str]:
    """(month, day, year) of a `_DATE` match, printed month-first or day-first."""
    return (found[0], found[1], found[2]) if found[0] else (found[4], found[3], found[5])


def _md(found: tuple[str, ...]) -> tuple[str, str]:
    """(month, day) of a `_MONTH_DAY` match, printed month-first or day-first."""
    return (found[0], found[1]) if found[0] else (found[3], found[2])


def _display(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%B %d, %Y")


def mapping_headers(
    page_text: str, *, first_data_line: int, statement: Literal["BS", "IS", "CFS"]
) -> _Header | None:
    """Recover coherent column headers from this page before its first data row."""
    lines = page_text.splitlines()[: max(0, first_data_line - 1)]
    # The unit's recognized title is the metadata boundary. A continuation
    # without a title must carry its own printed header; later row captions
    # cannot replace a valid header above them.
    title_start = _statement_title_start(lines)
    if title_start is not None:
        lines = lines[title_start:]
    candidates = [
        line
        for line in lines
        if _DURATION.search(line)
        or _YEARS.search(line)
        or _DATE.search(line)
        or _MONTH_DAY.search(line)
    ]
    if not candidates:
        return None
    # Most recent typed header controls flow semantics; a date-only row cannot
    # rescue a malformed or durationless income/cash-flow header.
    duration_lines = [line for line in candidates if _duration_labels(line)]
    if statement != "BS" and not duration_lines:
        return None
    years_line = next((line for line in reversed(candidates) if _YEARS.search(line)), None)
    if years_line is None:
        # Complete balance-sheet dates already carry their years. A flow header must print a
        # 19xx/20xx year row for its columns; without one it is not mapped.
        return _full_date_header(candidates) if statement == "BS" else None
    years = _YEARS.findall(years_line)
    if len(years) < 2 or not _only_years(years_line):
        return None
    if statement == "BS":
        return _balance_sheet_header(candidates, years)
    return _flow_header(lines, duration_lines[-1], years_line, years)


def _full_date_header(candidates: list[str]) -> _Header | None:
    """A balance-sheet header with no 19xx/20xx year row: its complete printed dates."""
    isos = [_iso(*_mdy(found)) for found in _DATE.findall(" ".join(candidates))]
    ends = [iso for iso in isos if iso is not None]
    return (" | ".join(_display(iso) for iso in ends),) if ends and len(ends) == len(isos) else None


def _only_years(years_line: str) -> bool:
    """Whether the year row prints nothing but years (and note, reference or month words)."""
    year_matches = list(_YEARS.finditer(years_line))
    gaps = [years_line[left.end() : right.start()] for left, right in pairwise(year_matches)]
    gaps.append(years_line[year_matches[-1].end() :])
    return not any(re.search(r"[A-Za-z]", _NOT_A_YEAR_CELL.sub(" ", gap)) for gap in gaps)


def _balance_sheet_header(candidates: list[str], years: list[str]) -> _Header | None:
    """Bind column-specific dates in order; a single explicit AS OF date can cover bare year
    columns only when that is what the page prints."""
    full_dates = [_iso(*_mdy(found)) for found in _DATE.findall(" ".join(candidates))]
    if any(iso is None for iso in full_dates):
        return None
    if len(full_dates) == 1 and str(date.fromisoformat(str(full_dates[0])).year) != years[0]:
        return None
    if len(full_dates) != len(years):
        md = [_md(found) for candidate in candidates for found in _MONTH_DAY.findall(candidate)]
        if len(md) == len(years):
            pairs = zip(md, years, strict=True)
            full_dates = [_iso(month, day, year) for (month, day), year in pairs]
        elif len(md) == 1:
            full_dates = [_iso(*md[0], year) for year in years]
        else:
            return None
    ends = [iso for iso in full_dates if iso is not None]
    return (" | ".join(_display(iso) for iso in ends),) if len(ends) == len(full_dates) else None


def _span_month_days(
    lines: list[str], dline: str, years_line: str
) -> list[tuple[str, str]]:
    """The month/day cells of the selected duration row and the rows below it, above the year
    row; earlier report banners frequently repeat the document end date. Else the duration
    row's own first month/day."""
    month_days = []
    for candidate in lines[lines.index(dline) :]:
        if candidate == years_line:
            break
        month_days += [_md(found) for found in _MONTH_DAY.findall(candidate)]
    if not month_days:
        # Normalize day-first span headings to month-first before matching.
        normalized = re.sub(rf"(?i)(\d{{1,2}})\s+({_MONTH})", r"\2 \1", dline)
        month_days = [_md(found) for found in _MONTH_DAY.findall(normalized)[:1]]
    return month_days


def _flow_header(
    lines: list[str], dline: str, years_line: str, years: list[str]
) -> _Header | None:
    """An income or cash-flow header: each year column takes its own printed duration and end."""
    durations = _duration_labels(dline) or []
    month_days = _span_month_days(lines, dline, years_line)
    complete_dates = [_mdy(found) for found in _DATE.findall(years_line)]
    if any(_iso(*found) is None for found in complete_dates):
        return None
    span_mds = [_md(found) for found in _MONTH_DAY.findall(dline)]
    if complete_dates and any(
        (month.lower(), str(int(day))) != (span_month.lower(), str(int(span_day)))
        for (month, day, _), (span_month, span_day) in zip(complete_dates, span_mds, strict=False)
    ):
        return None
    printed = [(month, day) for month, day, _ in complete_dates]
    month_days = month_days or printed
    if printed and len(printed) < len(years) and len(month_days) + len(printed) == len(years):
        month_days = printed + month_days
    elif len(printed) == len(years):
        month_days = printed
    if (
        not month_days
        or len(month_days) not in (1, len(durations), len(years))
        or (len(durations) > 1 and len(years) % len(durations))
    ):
        return None
    if all(duration == "Year" for duration in durations):
        return _fiscal_year_header(month_days, years)
    spanrow = []
    for i in range(len(years)):
        kind = durations[min(len(durations) - 1, i // max(1, len(years) // len(durations)))]
        month, day = month_days[_column_index(i, len(month_days), len(years))]
        if _iso(month, day, years[i]) is None:
            return None
        label = "Year Ended " if kind == "Year" else f"{kind} Months Ended "
        spanrow.append(label + month.title() + " " + day)
    # One span per column permits distinct ends under a mixed year/date header.
    return (" | ".join(spanrow), " | ".join(years))


def _column_index(column: int, cells: int, years: int) -> int:
    """The header cell that covers a year column: its own, its group's, or the only one."""
    if cells == years:
        return column
    return column // max(1, years // cells) if cells > 1 else 0


def _fiscal_year_header(month_days: list[tuple[str, str]], years: list[str]) -> _Header | None:
    ends = []
    for i, year in enumerate(years):
        month, day = month_days[_column_index(i, len(month_days), len(years))]
        end = _iso(month, day, year)
        if end is None:
            return None
        ends.append("FY " + end)
    return (" | ".join(ends),)
