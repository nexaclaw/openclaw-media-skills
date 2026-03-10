#!/usr/bin/env python3
"""Render Xiaohongshu text cards to SVG, PNG, or JPG from a JSON spec."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Iterable

RATIO_SIZES = {
    "3:4": (1080, 1440),
    "4:5": (1080, 1350),
    "1:1": (1080, 1080),
    "9:16": (1080, 1920),
}

DEFAULT_THEME = {
    "background": "#FFF8F1",
    "panel_fill": "#FFFDFB",
    "panel_stroke": "#F4DDD4",
    "accent": "#EF5A47",
    "accent_soft": "#FFD9CF",
    "text_primary": "#231815",
    "text_secondary": "#6E5A53",
    "tag_bg": "#231815",
    "tag_text": "#FFF8F1",
    "highlight_bg": "#FFE7DE",
    "highlight_text": "#9A3528",
    "footer_fill": "#231815",
    "footer_text": "#FFF8F1",
    "font_family": "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif",
}


@dataclass
class RenderedCard:
    stem: str
    svg: str
    width: int
    height: int
    scene: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Xiaohongshu text-first cards to SVG, PNG, or JPG files."
    )
    parser.add_argument("--spec", required=True, help="Path to a JSON spec.")
    parser.add_argument(
        "--theme",
        help="Optional theme JSON path. The spec can still override individual keys.",
    )
    parser.add_argument(
        "--output-dir", required=True, help="Directory to write one or more output files."
    )
    parser.add_argument(
        "--format",
        default="svg",
        choices=["svg", "png", "jpg", "jpeg"],
        help="Output format. PNG/JPG rasterization uses macOS qlmanage + sips.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=1,
        help="Raster scale multiplier for PNG/JPG output. Ignored for SVG.",
    )
    args = parser.parse_args()
    if args.scale < 1:
        parser.error("--scale must be at least 1")
    return args


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def merge_dicts(*parts: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for part in parts:
        if not part:
            continue
        for key, value in part.items():
            if value is not None:
                merged[key] = value
    return merged


def char_units(char: str) -> float:
    if char == "\n":
        return 0.0
    if char.isspace():
        return 0.35
    if ord(char) < 128:
        return 0.58 if char.isalnum() else 0.45
    return 1.0


def measure_text_units(text: str) -> float:
    return sum(char_units(char) for char in text)


def trim_to_units(text: str, max_units: float) -> str:
    current = ""
    used = 0.0
    for char in text:
        next_units = used + char_units(char)
        if next_units > max_units:
            break
        current += char
        used = next_units
    return current.rstrip()


def wrap_text(text: str, max_units: float, max_lines: int | None = None) -> list[str]:
    text = str(text or "").strip()
    if not text:
        return []

    lines: list[str] = []
    current = ""
    current_units = 0.0

    for char in text:
        if char == "\n":
            if current.strip():
                lines.append(current.rstrip())
            current = ""
            current_units = 0.0
            continue
        if char.isspace() and not current:
            continue

        char_width = char_units(char)
        if current and current_units + char_width > max_units:
            lines.append(current.rstrip())
            current = ""
            current_units = 0.0
            if char.isspace():
                continue

        current += char
        current_units += char_width

    if current.strip():
        lines.append(current.rstrip())

    if max_lines and len(lines) > max_lines:
        visible = lines[: max_lines - 1]
        overflow = "".join(lines[max_lines - 1 :]).strip()
        visible.append(f"{trim_to_units(overflow, max_units - 1)}…")
        return visible

    return lines


def title_font_size(kind: str, title_lines: list[str], max_width: float) -> int:
    kind = kind.lower()
    if kind == "cover":
        base = 118
        if len(title_lines) >= 2:
            base = 102
        if len(title_lines) >= 3:
            base = 86
    elif kind == "quote":
        base = 96
    else:
        base = 74
        if len(title_lines) >= 3:
            base = 64

    longest_line = max((measure_text_units(line) for line in title_lines), default=0.0)
    if longest_line > 11.5:
        base -= 8
    if longest_line > 14:
        base -= 8

    min_size = 52
    while base > min_size:
        estimated_width = longest_line * base * 0.92
        if estimated_width <= max_width:
            break
        base -= 2

    return max(base, min_size)


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    radius: float = 0.0,
    stroke: str | None = None,
    stroke_width: float = 0.0,
    opacity: float | None = None,
) -> str:
    attrs = [
        f'x="{x:.1f}"',
        f'y="{y:.1f}"',
        f'width="{width:.1f}"',
        f'height="{height:.1f}"',
        f'fill="{fill}"',
    ]
    if radius:
        attrs.append(f'rx="{radius:.1f}"')
        attrs.append(f'ry="{radius:.1f}"')
    if stroke:
        attrs.append(f'stroke="{stroke}"')
        attrs.append(f'stroke-width="{stroke_width:.1f}"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity:.3f}"')
    return f"<rect {' '.join(attrs)} />"


def circle(cx: float, cy: float, radius: float, fill: str, opacity: float) -> str:
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" '
        f'fill="{fill}" opacity="{opacity:.3f}" />'
    )


def scene_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    radius: float = 0.0,
    stroke: str | None = None,
    stroke_width: float = 0.0,
    opacity: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "rect",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "fill": fill,
        "radius": radius,
    }
    if stroke:
        payload["stroke"] = stroke
        payload["stroke_width"] = stroke_width
    if opacity is not None:
        payload["opacity"] = opacity
    return payload


def scene_circle(
    cx: float,
    cy: float,
    radius: float,
    fill: str,
    opacity: float,
) -> dict[str, Any]:
    return {
        "type": "circle",
        "cx": cx,
        "cy": cy,
        "radius": radius,
        "fill": fill,
        "opacity": opacity,
    }


def scene_text(
    text: str,
    x: float,
    y: float,
    width: float,
    height: float,
    size: int,
    color: str,
    font_family: str,
    weight: int = 600,
    align: str = "left",
) -> dict[str, Any]:
    return {
        "type": "text",
        "text": text,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "size": size,
        "color": color,
        "font_family": font_family,
        "weight": weight,
        "align": align,
    }


def text_line(
    text: str,
    x: float,
    y: float,
    size: int,
    color: str,
    font_family: str,
    weight: int = 600,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-size="{size}" '
        f'font-family="{escape(font_family)}" font-weight="{weight}" '
        f'text-anchor="{anchor}">{escape(text)}</text>'
    )


def render_text_block(
    lines: Iterable[str],
    x: float,
    y: float,
    width: float,
    size: int,
    color: str,
    font_family: str,
    line_height: float = 1.22,
    weight: int = 700,
    anchor: str = "start",
) -> tuple[list[str], list[dict[str, Any]], float]:
    line_list = list(lines)
    rendered: list[str] = []
    scene_items: list[dict[str, Any]] = []
    step = size * line_height
    for index, line in enumerate(line_list):
        baseline_y = y + (index * step)
        rendered.append(
            text_line(
                line,
                x,
                baseline_y,
                size,
                color,
                font_family,
                weight=weight,
                anchor=anchor,
            )
        )
        scene_items.append(
            scene_text(
                line,
                x,
                baseline_y - size,
                width,
                step,
                size,
                color,
                font_family,
                weight=weight,
                align="center" if anchor == "middle" else "left",
            )
        )
    return rendered, scene_items, len(line_list) * step


def pill_width(label: str, font_size: int, padding_x: int = 24) -> float:
    return measure_text_units(label) * font_size * 0.72 + (padding_x * 2)


def render_pill(
    label: str,
    x: float,
    y: float,
    fill: str,
    text_fill: str,
    font_family: str,
    font_size: int = 24,
    padding_x: int = 24,
    height: int = 54,
) -> tuple[list[str], list[dict[str, Any]], float]:
    width = pill_width(label, font_size, padding_x=padding_x)
    parts = [
        rect(x, y, width, height, fill, radius=height / 2),
        text_line(
            label,
            x + (width / 2),
            y + (height * 0.68),
            font_size,
            text_fill,
            font_family,
            weight=700,
            anchor="middle",
        ),
    ]
    scene_items = [
        scene_rect(x, y, width, height, fill, radius=height / 2),
        scene_text(
            label,
            x,
            y + ((height - font_size) / 2) - 2,
            width,
            height,
            font_size,
            text_fill,
            font_family,
            weight=700,
            align="center",
        ),
    ]
    return parts, scene_items, width


def render_chips(
    labels: list[str],
    x: float,
    y: float,
    max_width: float,
    theme: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], float]:
    if not labels:
        return [], [], 0.0

    parts: list[str] = []
    scene_items: list[dict[str, Any]] = []
    cursor_x = x
    cursor_y = y
    row_height = 54
    gap_x = 16
    gap_y = 16

    for label in labels:
        width = pill_width(label, 24, padding_x=22)
        if cursor_x > x and cursor_x + width > x + max_width:
            cursor_x = x
            cursor_y += row_height + gap_y

        pill_parts, pill_scene, pill_rendered_width = render_pill(
            label,
            cursor_x,
            cursor_y,
            theme["highlight_bg"],
            theme["highlight_text"],
            theme["font_family"],
            font_size=24,
            padding_x=22,
            height=row_height,
        )
        parts.extend(pill_parts)
        scene_items.extend(pill_scene)
        cursor_x += pill_rendered_width + gap_x

    total_height = cursor_y - y + row_height
    return parts, scene_items, total_height


def normalize_body(body: Any) -> list[str]:
    if body is None:
        return []
    if isinstance(body, str):
        return [body]
    return [str(item) for item in body if str(item).strip()]


def render_bullets(
    body: list[str],
    x: float,
    y: float,
    max_width: float,
    theme: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], float]:
    if not body:
        return [], [], 0.0

    parts: list[str] = []
    scene_items: list[dict[str, Any]] = []
    font_size = 38
    line_gap = font_size * 1.4
    bullet_offset = 28
    text_x = x + bullet_offset
    current_y = y

    for item in body[:5]:
        lines = wrap_text(item, max_width / 55, max_lines=2)
        if not lines:
            continue

        parts.append(circle(x + 8, current_y - 14, 7, theme["accent"], 1.0))
        scene_items.append(scene_circle(x + 8, current_y - 14, 7, theme["accent"], 1.0))
        for line_index, line in enumerate(lines):
            line_y = current_y + (line_index * line_gap)
            parts.append(
                text_line(
                    line,
                    text_x,
                    line_y,
                    font_size,
                    theme["text_primary"],
                    theme["font_family"],
                    weight=600,
                )
            )
            scene_items.append(
                scene_text(
                    line,
                    text_x,
                    line_y - font_size,
                    max_width - bullet_offset,
                    line_gap,
                    font_size,
                    theme["text_primary"],
                    theme["font_family"],
                    weight=600,
                )
            )

        current_y += len(lines) * line_gap + 26

    return parts, scene_items, current_y - y


def background_elements(
    width: int, height: int, theme: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    svg_items = [
        rect(0, 0, width, height, theme["background"]),
        circle(width * 0.82, height * 0.16, width * 0.19, theme["accent_soft"], 0.7),
        circle(width * 0.14, height * 0.84, width * 0.12, theme["accent_soft"], 0.55),
        rect(width * 0.08, height * 0.08, 20, height * 0.18, theme["accent"], radius=10),
    ]
    scene_items = [
        scene_rect(0, 0, width, height, theme["background"]),
        scene_circle(width * 0.82, height * 0.16, width * 0.19, theme["accent_soft"], 0.7),
        scene_circle(width * 0.14, height * 0.84, width * 0.12, theme["accent_soft"], 0.55),
        scene_rect(width * 0.08, height * 0.08, 20, height * 0.18, theme["accent"], radius=10),
    ]
    return svg_items, scene_items


def footer_block(
    label: str,
    x: float,
    y: float,
    width: float,
    theme: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    height = 96
    parts = [
        rect(x, y, width, height, theme["footer_fill"], radius=34),
        text_line(
            label,
            x + 36,
            y + 60,
            32,
            theme["footer_text"],
            theme["font_family"],
            weight=700,
        ),
    ]
    scene_items = [
        scene_rect(x, y, width, height, theme["footer_fill"], radius=34),
        scene_text(
            label,
            x + 36,
            y + ((height - 32) / 2) - 2,
            width - 72,
            height,
            32,
            theme["footer_text"],
            theme["font_family"],
            weight=700,
        ),
    ]
    return parts, scene_items


def choose_title_wrap(kind: str) -> float:
    if kind == "cover":
        return 10.5
    if kind == "quote":
        return 12.5
    return 13.5


def cover_content_left(width: int, safe: int) -> int:
    del width
    return safe + 36


def title_baseline_after_tag(tag_y: float, tag_height: float, title_size: int) -> float:
    # Keep the title block visually below the tag so the badge never sits on top
    # of the first line in either SVG or raster output.
    return tag_y + tag_height + title_size + 12


def render_card(card: dict[str, Any], theme: dict[str, Any], index: int) -> RenderedCard:
    ratio = str(card.get("ratio", "3:4"))
    width, height = RATIO_SIZES.get(ratio, RATIO_SIZES["3:4"])
    kind = str(card.get("kind", "slide")).lower()
    safe = 84
    content_x = safe
    content_w = width - (safe * 2)
    y = safe + 32
    scene_elements: list[dict[str, Any]] = []
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
    ]
    background_svg, background_scene = background_elements(width, height, theme)
    parts.extend(background_svg)
    scene_elements.extend(background_scene)

    if kind in {"slide", "checklist"}:
        panel_svg = rect(
            safe,
            safe,
            width - (safe * 2),
            height - (safe * 2),
            theme["panel_fill"],
            radius=44,
            stroke=theme["panel_stroke"],
            stroke_width=3,
        )
        parts.append(panel_svg)
        scene_elements.append(
            scene_rect(
                safe,
                safe,
                width - (safe * 2),
                height - (safe * 2),
                theme["panel_fill"],
                radius=44,
                stroke=theme["panel_stroke"],
                stroke_width=3,
            )
        )
        y = safe + 74
        content_x = safe + 54
        content_w = width - (content_x * 2)
    elif kind == "cover":
        content_x = cover_content_left(width, safe)
        content_w = width - content_x - safe

    title_lines = wrap_text(
        str(card.get("title", "")).strip(),
        choose_title_wrap(kind),
        max_lines=3,
    )
    title_size = title_font_size(kind, title_lines, content_w)
    tag = str(card.get("tag") or card.get("step") or "").strip()
    if tag:
        tag_y = y
        tag_parts, tag_scene, _ = render_pill(
            tag,
            content_x,
            tag_y,
            theme["tag_bg"],
            theme["tag_text"],
            theme["font_family"],
        )
        parts.extend(tag_parts)
        scene_elements.extend(tag_scene)
        y = title_baseline_after_tag(tag_y, 54, title_size)

    title_block, title_scene, title_height = render_text_block(
        title_lines,
        content_x,
        y,
        content_w,
        title_size,
        theme["text_primary"],
        theme["font_family"],
        line_height=1.18,
        weight=700 if kind == "cover" else 800,
    )
    parts.extend(title_block)
    scene_elements.extend(title_scene)
    y += title_height + 26

    subtitle = str(card.get("subtitle") or card.get("summary") or "").strip()
    if subtitle:
        subtitle_lines = wrap_text(subtitle, 18, max_lines=2)
        subtitle_block, subtitle_scene, subtitle_height = render_text_block(
            subtitle_lines,
            content_x,
            y,
            content_w,
            34,
            theme["text_secondary"],
            theme["font_family"],
            line_height=1.35,
            weight=500,
        )
        parts.extend(subtitle_block)
        scene_elements.extend(subtitle_scene)
        y += subtitle_height + 28

    highlights = [str(item).strip() for item in card.get("highlights", []) if str(item).strip()]
    highlight_parts, highlight_scene, highlight_height = render_chips(
        highlights,
        content_x,
        y,
        content_w,
        theme,
    )
    parts.extend(highlight_parts)
    scene_elements.extend(highlight_scene)
    if highlight_height:
        y += highlight_height + 34

    body = normalize_body(card.get("body"))
    bullet_parts, bullet_scene, bullet_height = render_bullets(
        body, content_x, y + 16, content_w, theme
    )
    parts.extend(bullet_parts)
    scene_elements.extend(bullet_scene)
    if bullet_height:
        y += bullet_height + 24

    footer = str(card.get("footer") or card.get("cta") or "").strip()
    if footer:
        footer_y = min(max(y + 32, height - safe - 124), height - safe - 124)
        footer_parts, footer_scene = footer_block(footer, content_x, footer_y, content_w, theme)
        parts.extend(footer_parts)
        scene_elements.extend(footer_scene)

    parts.append("</svg>")

    slug = str(card.get("filename") or kind or "card").strip().lower().replace(" ", "-")
    stem = f"{index:02d}-{slug}"
    return RenderedCard(
        stem=stem,
        svg="\n".join(parts),
        width=width,
        height=height,
        scene={"width": width, "height": height, "elements": scene_elements},
    )


def normalize_cards(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(spec.get("cards"), list):
        defaults = {key: value for key, value in spec.items() if key != "cards"}
        cards: list[dict[str, Any]] = []
        for card in spec["cards"]:
            combined = dict(defaults)
            combined.update(card)
            cards.append(combined)
        return cards
    return [spec]


def rendered_cards(spec: dict[str, Any], theme_overrides: dict[str, Any]) -> list[RenderedCard]:
    cards = normalize_cards(spec)
    rendered: list[RenderedCard] = []
    for index, card in enumerate(cards, start=1):
        card_theme = merge_dicts(
            DEFAULT_THEME,
            theme_overrides,
            spec.get("theme"),
            card.get("theme"),
        )
        rendered.append(render_card(card, card_theme, index))
    return rendered


def ensure_raster_tools() -> None:
    missing = [name for name in ("xcrun",) if shutil.which(name) is None]
    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            "Raster export requires macOS xcrun/swift/AppKit support. "
            f"Missing: {missing_list}. Use --format svg instead."
        )


def run_command(command: list[str], env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode == 0:
        return
    details = result.stderr.strip() or result.stdout.strip() or "command failed"
    raise RuntimeError(f"{' '.join(command)}\n{details}")


def swift_raster_env() -> dict[str, str]:
    sdk_path = subprocess.run(
        ["xcrun", "--show-sdk-path"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    env = os.environ.copy()
    env["SDKROOT"] = sdk_path
    env["SWIFT_MODULECACHE_PATH"] = "/tmp/swift-module-cache"
    return env


def rasterize_scenes(
    cards: list[RenderedCard],
    output_dir: Path,
    output_format: str,
    scale: int,
) -> list[Path]:
    ensure_raster_tools()
    swift_script = Path(__file__).with_name("render_text_scene.swift")
    bundle = {
        "cards": [
            {
                "stem": card.stem,
                "width": card.width,
                "height": card.height,
                "scene": card.scene,
            }
            for card in cards
        ]
    }

    with tempfile.TemporaryDirectory(prefix="xhs-scene-") as temp_dir_raw:
        bundle_path = Path(temp_dir_raw) / "bundle.json"
        bundle_path.write_text(
            json.dumps(bundle, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        env = swift_raster_env()
        run_command(
            [
                "xcrun",
                "swift",
                "-module-cache-path",
                "/tmp/swift-module-cache",
                str(swift_script),
                "--bundle",
                str(bundle_path),
                "--output-dir",
                str(output_dir),
                "--format",
                output_format,
                "--scale",
                str(scale),
            ],
            env=env,
        )

    extension = "jpg" if output_format == "jpeg" else output_format
    return [output_dir / f"{card.stem}.{extension}" for card in cards]


def write_outputs(
    spec: dict[str, Any],
    theme_overrides: dict[str, Any],
    output_dir: Path,
    output_format: str,
    scale: int,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cards = rendered_cards(spec, theme_overrides)
    final_format = "jpg" if output_format == "jpeg" else output_format
    written: list[Path] = []

    if final_format == "svg":
        for card in cards:
            target = output_dir / f"{card.stem}.svg"
            target.write_text(card.svg, encoding="utf-8")
            written.append(target)
        return written

    return rasterize_scenes(cards, output_dir, final_format, scale)


def main() -> None:
    args = parse_args()
    spec = load_json(args.spec)
    theme = load_json(args.theme) if args.theme else {}
    output_dir = Path(args.output_dir)
    written = write_outputs(spec, theme, output_dir, args.format, args.scale)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
