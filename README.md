# Content Production Skills

## Xiaohongshu Car Style

**小红书汽车图文风格工坊** learns reusable copywriting and visual rules from accessible Xiaohongshu account or post links and creates original new-car or used-car posts with finished cover and carousel images.

- `xhs-car-style/SKILL.md` — link-only input, account style profile, fact verification, image generation and composition workflow
- `xhs-car-style/references/style-profile.md` — reusable evidence-backed profile fields
- `xhs-car-style/agents/openai.yaml` — UI metadata

Invoke `$xhs-car-style` with an account or post link and an optional topic. Image production requires an available image generation tool and a deterministic text compositor such as Pillow/Sharp or browser screenshot rendering. Blocked links and missing tools are reported explicitly; the skill does not contain a scraper or publish posts automatically.

## Golden Quote Cover

**金句封面工坊** extracts high-impact Chinese quotes from a video subtitle transcript and composes them onto a cover image with segmented horizontal slices, translucent bands, and subject-safe typography.

## Contents

- `golden-quote-cover/SKILL.md` — Codex skill instructions
- `golden-quote-cover/agents/openai.yaml` — UI metadata and invocation settings
- `golden-quote-cover/scripts/compose_cover.py` — deterministic PIL compositor for exact Chinese text

## Use

Provide a cover image, subtitle transcript, and optional visual reference. The skill selects quote candidates, preserves the source wording, and renders the final text with a deterministic image compositor so Chinese characters remain exact.

Covers for Douyin and Xiaohongshu default to **3:4 (width:height)**. The compositor crops the source to an exact 3:4 canvas before placing text, without stretching the image. It retains the largest crop at the source resolution. Inspect the crop and adjust `--crop-position X Y` (0–1) to preserve the subject; the default is `0.5 0.5`, and `0.5 0` keeps the top. Use `--aspect-ratio W:H` only when another ratio is requested, or `--aspect-ratio source` to keep the original ratio explicitly.

For a manually selected quote set:

```bash
python3 golden-quote-cover/scripts/compose_cover.py \
  --input cover.jpg \
  --output cover-with-quotes.png \
  --line "AI时代，把事情做成的能力" \
  --line "可能比聪明更加重要" \
  --line "行动主体性，决定你能不能做成"
```

Use `--start-ratio`, `--band-height-ratio`, and `--gap-ratio` to move the slice stack around a portrait subject.
