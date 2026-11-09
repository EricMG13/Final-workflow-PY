"""What an ``ev-*`` span states about a TDR.6 figure's basis: its currency, scale, period length
and period end (S16 A02/C02).

A located figure's ``unit``, ``currency`` and ``period_end`` are model text; the review holds each
to the source. A property is read from the cited span when the span states it, else from the
item's ``Basis:`` lines (CP-1C's ``BASIS_PREFIX``, as a peer desk prints one basis above its
figure lines). The readers are deliberately narrow: what they do not recognise is not stated, so
the figure is refused (fail closed), never given a guessed basis.
"""

import re
import unicodedata
from collections.abc import Callable, Iterable
from datetime import date
from typing import Final

from deploy_vii.quotes import normalise

# Active ISO 4217 codes (2025 list): a three-capital word of a span is a currency only if listed.
_ISO_CODES: Final = """
    AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP
    BYN BZD CAD CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP
    GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR
    KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK
    MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR
    SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS
    UAH UGX USD UYU UZS VES VND VUV WST XAF XCD XCG XOF XPF YER ZAR ZMW ZWG
"""
ISO_4217: Final = frozenset(_ISO_CODES.split())
_CODE: Final = re.compile(r"(?<![A-Za-z])[A-Z]{3}(?![A-Z])")
# Codes that are also tickers or words (AMD, ALL, TOP): a currency only where one stands, after
# ``in`` or before a figure or a scale word, else the name of a company or a heading.
_WORD_CODES: Final = frozenset({"ALL", "AMD", "TOP", "CUP", "BOB", "SOS", "BAM"})
_CURRENCY_PLACE: Final = re.compile(r"\s?(?:[0-9]|(?i:thousands?|millions?|billions?|mn|bn|m|k)\b)")
# A symbol names its code only where it is unambiguous; any other currency symbol stands for
# itself, which no declared code equals.
_SYMBOL_CODE: Final = {"€": "EUR", "£": "GBP"}
# Currency names: a name the code list does not fix (a bare dollar, franc or crown) stands for
# itself, so a line naming one never borrows a code from a Basis line.
_NAME: Final = re.compile(
    r"\b(?i:(US dollars?|euros?|pounds? sterling|sterling|yen|yuan|renminbi|rmb|"
    r"dollars?|francs?|krona|krone|kronor|kroner|rupees?|pesos?|reais|rands?|lira|liras|"
    r"baht|ringgit|rupiah|shekels?|zlotys?|forints?|koruna|dirhams?|riyals?|rubles?|roubles?))\b"
)
_NAME_CODE: Final = {
    "us dollar": "USD",
    "us dollars": "USD",
    "euro": "EUR",
    "euros": "EUR",
    "pound sterling": "GBP",
    "pounds sterling": "GBP",
    "sterling": "GBP",
    "yen": "JPY",
    "yuan": "CNY",
    "renminbi": "CNY",
    "rmb": "CNY",
}

_SCALE: Final = re.compile(
    r"\b(?i:(thousands?|millions?|mn|mm|mio|mln|billions?|bn|bln|mrd|units))\b"
    r"|(?:(?<![A-Za-z])[A-Z]{3}|[$€£¥]|(?<=[0-9]))\s?(k|m|mn|bn)\b"
    r"|(?<![0-9,.])(?<![0-9] )'?(000)s?(?![0-9A-Za-z,.])"
)
_SCALE_OF: Final = {
    "thousand": "thousands",
    "thousands": "thousands",
    "k": "thousands",
    "million": "millions",
    "millions": "millions",
    "mn": "millions",
    "mm": "millions",
    "mio": "millions",
    "mln": "millions",
    "m": "millions",
    "billion": "billions",
    "billions": "billions",
    "bn": "billions",
    "bln": "billions",
    "mrd": "billions",
    "000": "thousands",
    "units": "units",
}

TWELVE_MONTHS: Final = "twelve months"
_OTHER_LENGTH: Final = "another period length"
_MONTHS: Final = re.compile(
    r"\b(?i:(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|[0-9]{1,2})"
    r"[ -]months?)\b"
)
_TWELVE_TAG: Final = re.compile(r"\b(?:LTM|TTM)\b")
_OTHER_PERIOD: Final = re.compile(
    r"\b(?i:quarter(?:ly|s)?|half[ -]year(?:ly)?|(?:first|second) half|interim|"
    r"year[ -]to[ -]date|weeks?)\b|\b(?:YTD|Q[1-4]|[1-4]Q|H[12]|[1-4]H|[369]M)(?:[0-9]{2})?\b"
)

_MONTH_NAMES: Final = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
_MONTH: Final = (
    r"(January|February|March|April|May|June|July|August|September|October|November|December"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.?"
)
_ISO_DATE: Final = re.compile(r"(?<![0-9])([0-9]{4})-([0-9]{2})-([0-9]{2})(?![0-9])")
_ORDINAL: Final = r"(?:st|nd|rd|th)?"
_MONTH_DAY_YEAR: Final = re.compile(rf"\b{_MONTH} ([0-9]{{1,2}}){_ORDINAL},? ([0-9]{{4}})\b")
_DAY_MONTH_YEAR: Final = re.compile(rf"\b([0-9]{{1,2}}){_ORDINAL} {_MONTH},? ([0-9]{{4}})\b")


def _is_currency(code: re.Match[str], text: str) -> bool:
    """An ISO 4217 code of the text; a word-like one (``_WORD_CODES``) only in a currency place."""
    if code.group() not in ISO_4217:
        return False
    in_place = text[: code.start()].lower().endswith("in ") or _CURRENCY_PLACE.match(
        text, code.end()
    )
    return code.group() not in _WORD_CODES or bool(in_place)


def currencies(text: str) -> frozenset[str]:
    """The ISO 4217 codes the text names (``US$`` as USD, ``€`` and euros as EUR, and so on) and
    any other currency symbol or name, which stands for itself."""
    text = text.replace("US$", " USD ")
    found = {m.group() for m in _CODE.finditer(text) if _is_currency(m, text)}
    found |= {_NAME_CODE.get(name.lower(), name.lower()) for name in _NAME.findall(text)}
    for char in text:
        if unicodedata.category(char) == "Sc":
            found.add(_SYMBOL_CODE.get(char, char))
    return frozenset(found)


def scales(text: str) -> frozenset[str]:
    """The scales the text states: thousands, millions, billions or units (a word, or ``m``,
    ``mn``, ``bn``, ``k`` after a currency code or symbol)."""
    return frozenset(
        _SCALE_OF[(match.group(1) or match.group(2) or match.group(3)).lower()]
        for match in _SCALE.finditer(text)
    )


def period_lengths(text: str) -> frozenset[str]:
    """``TWELVE_MONTHS`` for a twelve-month statement (``twelve months``, ``12-month``, LTM,
    TTM), another tag for any other length the text states (a quarter, a half year, nine
    months, year to date)."""
    found = {
        TWELVE_MONTHS if match.group(1).lower() in ("twelve", "12") else _OTHER_LENGTH
        for match in _MONTHS.finditer(text)
    }
    if _TWELVE_TAG.search(text):
        found.add(TWELVE_MONTHS)
    if _OTHER_PERIOD.search(text):
        found.add(_OTHER_LENGTH)
    return frozenset(found)


def _month(name: str) -> int:
    return next(i for i, full in enumerate(_MONTH_NAMES, 1) if full.startswith(name.lower()))


def _date(year: str, month: int, day: str) -> date | None:
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def period_ends(text: str) -> frozenset[date]:
    """The calendar dates the text states as ``2025-12-31``, ``December 31, 2025`` or
    ``31 December 2025`` (month names in full or abbreviated)."""
    found = [_date(y, int(m), d) for y, m, d in _ISO_DATE.findall(text)]
    found += [_date(y, _month(m), d) for m, d, y in _MONTH_DAY_YEAR.findall(text)]
    found += [_date(y, _month(m), d) for d, m, y in _DAY_MONTH_YEAR.findall(text)]
    return frozenset(day for day in found if day is not None)


def stated[T](read: Callable[[str], frozenset[T]], span: str, basis: Iterable[str]) -> frozenset[T]:
    """What the cited span states by ``read``; when it states nothing, what the item's ``Basis:``
    lines state together."""
    own = read(normalise(span))
    if own:
        return own
    return frozenset(item for line in basis for item in read(normalise(line)))
