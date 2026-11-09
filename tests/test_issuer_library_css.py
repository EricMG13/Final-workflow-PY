"""Stylesheet rules of the Issuer Library, read as text; answer keys are written here by hand.

These check the declared rules, not how a browser lays them out.
"""

from __future__ import annotations

import re

from issuer_library_browser import WEB

FILES = ("screen.css", "report-adapter.css", "context-embed.css")
SCREEN = (WEB / "screen.css").read_text(encoding="utf-8")


def luminance(colour: str) -> float:
    value = colour.removeprefix("#")
    channels = []
    for start in (0, 2, 4):
        c = int(value[start : start + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def rule(selector: str) -> list[str]:
    """The declaration blocks whose selector list names this selector exactly."""
    return [
        body
        for head, body in re.findall(r"([^{}]+)\{([^}]*)\}", SCREEN)
        if selector in [part.strip() for part in head.strip().split(",")]
    ]


def media_blocks(first: str, second: str | None) -> list[str]:
    """The bodies of @media blocks with these conditions, nested braces included."""
    blocks = []
    for match in re.finditer(r"@media\(([^)]*)\)(?: and \(([^)]*)\))?\{", SCREEN):
        if match.group(1) != first or match.group(2) != second:
            continue
        depth, index = 1, match.end()
        while depth and index < len(SCREEN):
            depth += {"{": 1, "}": -1}.get(SCREEN[index], 0)
            index += 1
        blocks.append(SCREEN[match.end() : index - 1])
    return blocks


def test_primary_hover_excludes_disabled_and_keeps_white_text() -> None:
    found = re.search(r"(\.primary-action:hover[^{]*)\{([^}]*)\}", SCREEN)
    assert found, "no .primary-action:hover rule"
    assert found.group(1) == ".primary-action:hover:not(:disabled)"
    assert "color:#fff" in found.group(2)


def test_no_text_below_11px_and_no_em_or_rem_below_1() -> None:
    offenders = []
    for name in FILES:
        text = (WEB / name).read_text(encoding="utf-8")
        for match in re.finditer(r"font(?:-size)?:\s*(?:\d{3}\s+)?([\d.]+)(px|em|rem)", text):
            value, unit = float(match.group(1)), match.group(2)
            if (unit == "px" and value < 11) or (unit != "px" and value < 1):
                offenders.append(f"{name}: {match.group(0)}")
    assert offenders == []


def test_type_ramp_tokens_are_declared_and_used() -> None:
    root = next(block for block in SCREEN.split("}") if ":root{" in block)
    for token in ("--fs-label:11px", "--fs-compact:12px", "--fs-body:13px", "--fs-control:14px"):
        assert token in root, token
    assert not re.search(r"font-size:1[1-4]px", SCREEN)
    assert not re.search(r"font:(?:\d{3}\s+)?1[1-4]px", SCREEN)


def test_text_quaternary_contrast_on_white() -> None:
    found = re.search(r"--text-quaternary:(#[0-9a-fA-F]{6})", SCREEN)
    assert found, "token missing"
    ratio = contrast(found.group(1), "#ffffff")
    assert ratio >= 5.5 and f"{ratio:.2f}" == "6.06"


def test_report_adapter_css_declares_every_fs_token_it_uses() -> None:
    adapter = (WEB / "report-adapter.css").read_text(encoding="utf-8")
    brand = (WEB / "brand.css").read_text(encoding="utf-8")
    used = {token[4:-1] for token in re.findall(r"var\(--fs-[a-z]+\)", adapter)}
    block = (re.search(r"\.library-report\s*\{[^}]*\}", adapter) or [""])[0]
    missing = sorted(t for t in used if f"{t}:" not in block and f"{t}:" not in brand)
    assert missing == [], "undeclared in the report document"


def test_tools_workspace_opened_navigator_takes_a_238px_column() -> None:
    found = re.findall(
        r"([^{}]*\.tools-workspace[^{}]*:has\(\.navigator\.mobile-open\)[^{}]*)\{([^}]*)\}", SCREEN
    )
    assert any(
        re.search(r"grid-template-columns:\s*238px minmax\(0,\s*1fr\)\s*(;|$)", body)
        for _, body in found
    )


def test_tools_workspace_modules_toggle_spans_every_column() -> None:
    assert any(
        re.search(r"grid-column:\s*1/-1", b) for b in rule(".tools-workspace .mobile-modules")
    )


def test_border_radii_use_only_the_design_scale() -> None:
    allowed = {
        "0",
        "1px",
        "50%",
        "999px",
        "var(--radius-inline)",
        "var(--radius-control)",
        "var(--radius-card)",
    }
    values = [v for m in re.findall(r"border-radius:([^;}]*)", SCREEN) for v in m.strip().split()]
    assert sorted(set(values) - allowed) == []
    assert re.search(r":root\{[^}]*--radius-inline:4px", SCREEN)


def test_forced_colours_keep_pills_buttons_and_the_active_rail_item_visible() -> None:
    block = re.search(r"@media\(forced-colors:active\)\{(.*)\}\s*$", SCREEN, re.MULTILINE)
    assert block, "no forced-colors block"
    assert ".rail a[aria-current]" in block.group(1) and ".badge" in block.group(1)
    assert any("white-space:nowrap" in b for b in rule(".issuer-meta a"))


def test_layout_an_opened_navigator_keeps_two_columns_at_1000px() -> None:
    blocks = media_blocks("min-width:721px", "max-width:1050px")
    for selector in (
        r"\.workbench\.tools-workspace:has",
        r"\.workbench\.tools-workspace\.has-evidence:has",
    ):
        pattern = (
            r"(^|[{};])" + selector + r"\(\.navigator\.mobile-open\)\{grid-template-columns:220px "
            r"minmax\(0,1fr\)\}"
        )
        assert any(re.search(pattern, block) for block in blocks), selector


def test_layout_the_tools_browse_modules_toggle_is_auto_width() -> None:
    found = ";".join(rule(".tools-workspace .mobile-modules"))
    assert "width:auto" in found and "width:100%" not in found


def test_layout_filters_flow_long_names_truncate_groups_fit() -> None:
    assert any("auto-fit" in b for b in rule(".library-filters"))
    assert any("text-overflow:ellipsis" in b for b in rule(".issuer h1"))
    assert any("auto-fit" in b for b in rule(".question-map>section>div"))


def test_layout_controls_reach_32px() -> None:
    for selector in (
        ".output-select select",
        "#report-select",
        ".module-catalogue>summary",
        ".issuer-meta a",
        "#section-nav select",
        "#section-nav button",
    ):
        assert any(re.search(r"(^|;)(min-)?height:32px", b) for b in rule(selector)), selector
