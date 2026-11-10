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


def test_content_table_cards_are_bounded_and_keep_their_header_in_view() -> None:
    card = re.search(r"(?:^|[}\n])\.table-scroll\{([^}]*)\}", SCREEN)
    assert card, "no .table-scroll rule"
    assert "max-height:70vh" in card.group(1) and "overflow:auto" in card.group(1)
    head = re.search(r"\.table-scroll thead th\{([^}]*)\}", SCREEN)
    assert head, "no .table-scroll thead th rule"
    assert "position:sticky" in head.group(1) and "top:0" in head.group(1)
    assert "background:var(--gray-50)" in head.group(1)


def test_the_section_bar_is_sticky_with_its_run_and_module_prefix_at_720px_and_below() -> None:
    assert re.search(r"\.section-context\{display:none\}", SCREEN)
    media = "\n".join(re.findall(r"@media\(max-width:720px\)\{(.*)", SCREEN))
    bar = re.search(r"#section-nav\{[^}]*position:sticky[^}]*\}", media)
    assert bar, "no sticky #section-nav at 720px"
    for part in ("top:0", "background:#fff", "border-bottom:1px solid var(--rule)"):
        assert part in bar.group(0), part
    assert re.search(r"#section-nav \.section-context\{display:block", media)


def test_the_rail_opens_as_an_overlay_for_focus_too_and_stops_animating_under_reduced_motion() -> (
    None
):
    opened = re.findall(r"\.rail\.rail-open[^{}]*\{[^}]*\}", SCREEN)
    assert any("width:220px" in r for r in opened), "open rail is 220px wide"
    assert not re.search(r"\.app\{[^}]*margin-left:220px", SCREEN), "the page does not reflow"
    assert ".rail:focus-within" not in SCREEN, "a mouse click must not leave the rail open"
    covered = [line for line in SCREEN.split("\n") if re.match(r"\.rail\.rail-open", line)]
    assert len(covered) >= 4
    for line in covered:
        selectors = line[: line.index("{")]
        for sel in (s for s in selectors.split(",") if ".rail-open" in s):
            assert sel.replace(".rail-open", ":has(:focus-visible)") in selectors, sel
    assert re.search(
        r"\.rail:not\(\.rail-open\)[^{]*\.rail-label|\.rail-label\{[^}]*clip:rect\(0,0,0,0\)",
        SCREEN,
    ), "labels are clipped at rest"
    assert not re.search(r"\.rail-label\{[^}]*display:none", SCREEN)
    reduced = "".join(re.findall(r"@media\(prefers-reduced-motion:reduce\)\{(.*)\}", SCREEN))
    assert re.search(r"\.rail\{[^}]*transition:none", reduced)
    assert re.search(r"\.rail\{[^}]*transition:width", SCREEN)


def test_at_720px_the_section_bar_outranks_every_sticky_cell_and_row_labels_are_capped() -> None:
    start = "@media(max-width:720px){#section-nav{z-index:5}"
    mobile = SCREEN[SCREEN.rindex(start) :]
    bar = int(re.search(r"#section-nav\{z-index:(\d+)\}", mobile).group(1))  # type: ignore[union-attr]
    cells = [int(z) for z in re.findall(r"position:sticky[^}]*z-index:(\d+)", SCREEN)]
    assert cells
    assert all(z < bar for z in cells), f"a sticky cell reaches {max(cells)}, bar is {bar}"
    assert re.search(
        r"\.cashflow tbody th\[scope=row\]\{[^}]*white-space:normal"
        r"[^}]*min-width:12rem[^}]*max-width:12rem",
        mobile,
    )


def test_every_custom_property_screen_css_reads_without_a_fallback_is_defined_in_screen_css() -> (
    None
):
    defined = set(re.findall(r"(--[\w-]+)\s*:", SCREEN))
    bare = re.findall(r"var\((--[\w-]+)\)", SCREEN)
    assert sorted(set(bare) - defined) == []
    assert re.search(r"\.ref\{[^}]*color:var\(--muted\)", SCREEN)


def test_the_amber_run_mark_glyph_and_the_amber_strip_text_hold_4_5_to_1_on_their_backgrounds() -> (
    None
):
    def token(name: str) -> str:
        found = re.search(rf"--{name}:(#[0-9a-f]{{6}})", SCREEN, re.IGNORECASE)
        assert found, name
        return found.group(1)

    mark = re.search(
        r"\.run-mark\[data-state=stopped\]\{background:var\(--([a-z-]+)\);color:var\(--([a-z-]+)\)",
        SCREEN,
    )
    assert mark, "amber mark rule"
    assert contrast(token(mark.group(2)), token(mark.group(1))) >= 4.5
    assert contrast(token("amber"), token("amber-bg")) >= 4.5


def test_cash_flow_rows_are_32px_labels_hold_12rem_groups_ruled_scenarios_on_quiet() -> None:
    cell = re.search(r"\.cashflow tbody th,\.cashflow tbody td\{([^}]*)\}", SCREEN)
    assert cell, "no cash flow cell rule"
    for part in ("height:32px", "padding-top:5px", "padding-bottom:5px", "line-height:20px"):
        assert part in cell.group(1), part
    label = re.search(r"\.cashflow tbody th\[scope=row\]\{([^}]*min-width:12rem[^}]*)\}", SCREEN)
    assert label, "row labels have no 12rem minimum"
    assert "white-space:normal" in label.group(1)
    assert not re.search(r"\.cashflow[^{]*\{[^}]*text-overflow:ellipsis", SCREEN)
    assert ".cashflow .group-start{border-left:1px solid var(--rule)}" in SCREEN
    assert ".cashflow td.scenario{background:var(--quiet)}" in SCREEN


def test_the_published_model_disclosure_and_cash_flow_region_are_a_quiet_disclosure() -> None:
    assert re.search(r"\.model-original>summary\{[^}]*cursor:pointer[^}]*min-height:32px", SCREEN)


def test_the_run_strip_uses_the_card_radius_a_wide_supporting_line_and_24px_action_targets() -> (
    None
):
    def strip_rule(selector: str) -> str:
        found = re.search(rf"(?:^|\}}){re.escape(selector)}\{{([^}}]*)\}}", SCREEN, re.MULTILINE)
        return found.group(1) if found else ""

    assert "border-radius:var(--radius-card)" in strip_rule(".run-strip")
    assert "max-width:120ch" in strip_rule(".strip-text")
    assert "min-height:24px" in strip_rule(".strip-actions a")


def test_a_run_detail_with_a_64_character_deliverable_name_wraps_instead_of_widening_the_page() -> (
    None
):
    assert re.search(r"\.artifact-list li\{[^}]*overflow-wrap:anywhere", SCREEN)


def test_the_run_detail_head_wraps_and_breaks_a_long_run_id_at_390_px() -> None:
    assert re.search(r"\.detail-head\{[^}]*flex-wrap:wrap", SCREEN)
    assert re.search(r"\.detail-head>div:first-child\{[^}]*min-width:0", SCREEN)
    assert re.search(r"\.detail-head>div:first-child\{[^}]*overflow-wrap:anywhere", SCREEN)
