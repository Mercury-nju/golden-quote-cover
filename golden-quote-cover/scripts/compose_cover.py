#!/usr/bin/env python3
"""Compose exact Chinese quote text over a segmented video-cover layout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFont


FONT_CANDIDATES = (
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)


def find_font(explicit: str | None) -> str:
    if explicit:
        if not os.path.exists(explicit):
            raise FileNotFoundError(f"Font not found: {explicit}")
        return explicit
    for candidate in FONT_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "No CJK font found. Pass --font with a .ttf/.ttc font that supports Chinese."
    )


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text.strip():
        candidate = current + char
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def luminance(image: Image.Image) -> float:
    sample = image.resize((1, 1)).convert("RGB").getpixel((0, 0))
    return 0.2126 * sample[0] + 0.7152 * sample[1] + 0.0722 * sample[2]


def crop_with_horizontal_shift(image: Image.Image, y: int, height: int, shift: int) -> Image.Image:
    width, image_height = image.size
    y = max(0, min(y, image_height - height))
    band = image.crop((0, y, width, y + height))
    # Wrap the strip instead of padding with transparency, which would create
    # visible seams after alpha compositing.
    return ImageChops.offset(band, max(-width // 10, min(width // 10, shift)), 0)


def draw_cover(
    image: Image.Image,
    quotes: Iterable[str],
    font_path: str,
    font_size: int,
    start_ratio: float | None = None,
    band_height_ratio: float | None = None,
    gap_ratio: float | None = None,
) -> Image.Image:
    base = image.convert("RGBA")
    width, height = base.size
    quotes = [quote.strip() for quote in quotes if quote.strip()]
    if not quotes:
        raise ValueError("At least one non-empty quote is required.")

    band_count = len(quotes)
    band_height = max(56, int(height * (band_height_ratio or (0.13 if band_count <= 5 else 0.105))))
    gap = max(8, int(height * (gap_ratio or 0.025)))
    total_height = band_count * band_height + (band_count - 1) * gap
    if start_ratio is None:
        start_y = max(0, (height - total_height) // 2)
    else:
        start_y = max(0, min(height - total_height, int(height * start_ratio)))
    font = ImageFont.truetype(font_path, font_size)
    draw_probe = ImageDraw.Draw(base)
    canvas = base.copy()

    for index, quote in enumerate(quotes):
        target_y = start_y + index * (band_height + gap)
        # Keep source strips close to their target position so a portrait face
        # is not unexpectedly duplicated behind lower quote bands.
        source_y = target_y + int((index - (band_count - 1) / 2) * band_height * 0.28)
        source_y = max(0, min(height - band_height, source_y))
        shift = int(width * (0.08 if index % 2 else -0.05))
        band = crop_with_horizontal_shift(base, source_y, band_height, shift)
        shade_alpha = 150 if luminance(band) > 145 else 95
        shade = Image.new("RGBA", band.size, (0, 0, 0, shade_alpha))
        band = Image.alpha_composite(band, shade)
        canvas.alpha_composite(band, (0, target_y))

        text_lines = wrap_text(draw_probe, quote, font, int(width * 0.88))
        line_boxes = [draw_probe.textbbox((0, 0), line, font=font, stroke_width=2) for line in text_lines]
        line_heights = [box[3] - box[1] for box in line_boxes]
        line_gap = max(2, int(font_size * 0.14))
        text_block_height = sum(line_heights) + line_gap * (len(text_lines) - 1)
        text_y = target_y + (band_height - text_block_height) // 2
        draw = ImageDraw.Draw(canvas)
        for line, line_height in zip(text_lines, line_heights):
            bbox = draw.textbbox((0, 0), line, font=font, stroke_width=2)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text(
                (text_x, text_y),
                line,
                font=font,
                fill=(255, 255, 255, 255),
                stroke_width=max(2, font_size // 18),
                stroke_fill=(0, 0, 0, 220),
            )
            text_y += line_height + line_gap

    return canvas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Source cover image")
    parser.add_argument("--output", required=True, help="Output PNG/JPG path")
    parser.add_argument("--line", action="append", dest="lines", required=True, help="One quote line; repeat for each band")
    parser.add_argument("--font", help="Optional CJK .ttf/.ttc font path")
    parser.add_argument("--font-size", type=int, default=52, help="Font size in pixels")
    parser.add_argument("--start-ratio", type=float, help="Top of first band as a fraction of image height")
    parser.add_argument("--band-height-ratio", type=float, help="Band height as a fraction of image height")
    parser.add_argument("--gap-ratio", type=float, help="Gap between bands as a fraction of image height")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Image.open(args.input)
    font_path = find_font(args.font)
    result = draw_cover(
        source,
        args.lines,
        font_path,
        args.font_size,
        start_ratio=args.start_ratio,
        band_height_ratio=args.band_height_ratio,
        gap_ratio=args.gap_ratio,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        result.convert("RGB").save(output, quality=95, optimize=True)
    else:
        result.save(output)


if __name__ == "__main__":
    main()
