"""Source identities and exact dates from an SEC inline-XBRL document.

No expected values are read. Unsupported numeric formats and dimensional contexts
are excluded from consolidated financial input rather than guessed.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from html.parser import HTMLParser
from typing import Any

from deploy_workflow.html_text import decode_html


@dataclass(frozen=True)
class Context:
    context_id: str
    entity: str
    scheme: str
    start: date | None
    end: date | None
    instant: date | None
    dimensional: bool


@dataclass(frozen=True)
class Fact:
    fact_id: str
    concept: str
    context_id: str
    unit_id: str
    lexeme: str
    scale: int
    negative: bool
    nil: bool
    format: str
    table: int | None
    row: int | None

    def amount(self) -> Decimal | None:
        if self.nil:
            return None
        transform = self.format.split(":")[-1]
        # The issuer's fixed-zero tag supplies the numeric meaning; keep lexeme
        # untouched so a reported dash remains distinguishable in the handoff.
        if transform == "fixed-zero":
            return Decimal(0)
        if transform not in {"num-dot-decimal", "numdotdecimal", "zerodash", "numdash", ""}:
            raise ValueError(f"unsupported numeric format on {self.fact_id}")
        text = re.sub(r"[\s,]", "", self.lexeme)
        if text in {"-", "—", "–"} and transform in {"zerodash", "numdash"}:
            return Decimal(0)
        if (
            not re.fullmatch(r"(?:\d+(?:\.\d+)?|\.\d+)", text)
            or len(text) > 100
            or abs(self.scale) > 30
        ):
            raise ValueError(f"unsupported numeric lexeme on {self.fact_id}")
        with localcontext() as ctx:
            ctx.prec = 150
            value = Decimal(text).scaleb(self.scale)
        return value.copy_negate() if self.negative else value


@dataclass(frozen=True)
class Document:
    sha256: str
    contexts: dict[str, Context]
    units: dict[str, tuple[str, ...]]
    facts: tuple[Fact, ...]


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.context: dict[str, Any] | None = None
        self.unit: dict[str, Any] | None = None
        self.active_facts: list[dict[str, Any]] = []
        self.contexts: dict[str, Context] = {}
        self.units: dict[str, tuple[str, ...]] = {}
        self.facts: list[Fact] = []
        self.tables: list[list[int]] = []
        self.table_index = -1
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        local = tag.split(":")[-1]
        if tag not in {"br", "img", "meta", "link", "input", "hr", "wbr", "area", "col"}:
            self.stack.append(tag)
        if local == "context" and a.get("id"):
            if self.context is not None:
                raise ValueError("nested source contexts")
            self.context = {"id": a["id"], "dimensional": False}
        if self.context is not None:
            if local in {"segment", "scenario", "explicitmember", "typedmember"}:
                self.context["dimensional"] = True
            if local == "identifier":
                self.context["scheme"] = a.get("scheme", "")
        if local == "unit" and a.get("id"):
            self.unit = {"id": a["id"], "measures": [], "divide": False}
        if self.unit is not None and local == "divide":
            self.unit["divide"] = True
        if tag == "table":
            self.table_index += 1
            self.tables.append([self.table_index, -1])
        elif tag == "tr" and self.tables:
            self.tables[-1][1] += 1
        if tag == "ix:nonfraction":
            self.active_facts.append({"attrs": a, "text": [], "table": self.tables[-1][0] if self.tables else None,
                         "row": self.tables[-1][1] if self.tables else None})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        local = self.stack[-1].split(":")[-1] if self.stack else ""
        if self.context is not None and local in {"identifier", "startdate", "enddate", "instant"}:
            self.context[local] = self.context.get(local, "") + data
        if self.unit is not None and local == "measure":
            self.unit["measures"].append(data.strip())
        if "ix:exclude" not in self.stack:
            for fact in self.active_facts:
                fact["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        local = tag.split(":")[-1]
        if local == "context" and self.context is not None:
            c = self.context
            value = Context(
                c["id"],
                c.get("identifier", "").strip(),
                c.get("scheme", ""),
                date.fromisoformat(c["startdate"].strip()) if c.get("startdate") else None,
                date.fromisoformat(c["enddate"].strip()) if c.get("enddate") else None,
                date.fromisoformat(c["instant"].strip()) if c.get("instant") else None,
                c["dimensional"],
            )
            if value.context_id in self.contexts:
                raise ValueError("duplicate source context id")
            self.contexts[value.context_id] = value
            self.context = None
        if local == "unit" and self.unit is not None:
            u = self.unit
            if u["id"] in self.units:
                raise ValueError("duplicate source unit id")
            self.units[u["id"]] = () if u["divide"] else tuple(u["measures"])
            self.unit = None
        if tag == "ix:nonfraction" and self.active_facts:
            f = self.active_facts.pop()
            a = f["attrs"]
            # The id attribute is optional in Inline XBRL 1.1; a fact without one keeps "".
            identifier = a.get("id") or ""
            if identifier in self.ids:
                raise ValueError("duplicate inline fact id")
            if identifier:
                self.ids.add(identifier)
            self.facts.append(
                Fact(
                    identifier,
                    a.get("name", ""),
                    a.get("contextref", ""),
                    a.get("unitref", ""),
                    "".join(f["text"]).strip(),
                    int(a.get("scale", "0")),
                    a.get("sign") == "-",
                    a.get("xsi:nil", "false") in {"true", "1"},
                    a.get("format", ""),
                    f["table"],
                    f["row"],
                )
            )
        if tag == "table" and self.tables:
            self.tables.pop()
        if tag in self.stack:
            del self.stack[len(self.stack) - 1 - self.stack[::-1].index(tag) :]


def parse(raw: bytes) -> Document:
    """Raises ``ValueError`` (``UndecodableHtml`` included) for a document it cannot read."""
    # Decoded exactly as convert_html decodes the same bytes (UTF-8, or a declared
    # windows-1252 / iso-8859-1 / ascii charset), so both read the same text.
    text, _ = decode_html(raw)
    parser = _Parser()
    parser.feed(text)
    parser.close()
    if parser.context is not None or parser.active_facts or parser.unit is not None:
        raise ValueError("unfinished inline-XBRL structure")
    return Document(
        hashlib.sha256(raw).hexdigest(), parser.contexts, parser.units, tuple(parser.facts)
    )


def period_lines(document: Document) -> tuple[str, ...]:
    """Citable exact source dates, attached after the visible text without moving its lines."""
    return tuple(
        f"XBRL context {c.context_id}; entity {c.entity}; scheme {c.scheme}; "
        + (f"duration {c.start.isoformat()} through {c.end.isoformat()}" if c.start and c.end
           else f"instant {c.instant.isoformat()}" if c.instant else "period unspecified")
        for c in document.contexts.values() if not c.dimensional
    )
