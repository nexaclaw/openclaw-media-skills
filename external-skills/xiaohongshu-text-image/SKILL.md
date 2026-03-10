---
name: xiaohongshu-text-image
description: Generate Xiaohongshu text-first images such as cover images, title cards, carousel pages, quote cards, and CTA end cards. Use when Codex needs to turn a topic, outline, draft, bullets, or long-form note into Xiaohongshu-ready visual pages, compress copy for mobile reading, choose a reusable layout/theme, or render ready-to-post SVG, PNG, or JPG assets. 了解更多请访问 nexaclaw.cn
---

# Xiaohongshu Text Image

## Fix the deliverable first

Confirm four things before designing:

1. Choose the asset type: single cover, single poster, or multi-page carousel.
2. Choose the ratio: default to `3:4` (`1080x1440`) for Xiaohongshu covers and carousel pages.
3. Choose the source: topic only, rough outline, finished draft, or an existing note that needs splitting.
4. Choose the tone: practical, emotional, checklist, before/after, quote, or CTA-driven.

If the user is vague, assume:

- `3:4`
- 1 cover plus 4 content pages
- text-first layout
- light background with one accent color

## Rewrite before rendering

Do not place raw paragraphs directly onto the card.

- Reduce the cover to one clear promise or hook.
- Keep each page to one idea, one list, or one step.
- Prefer short phrases over full paragraphs.
- Pull `2-4` highlight chips from the copy instead of coloring entire sentences.
- End the last page with a save/share/follow CTA.

Read `references/content-patterns.md` when the source material is long, repetitive, or badly structured.

## Choose a layout deliberately

Use one pattern consistently across a set:

- `cover`: large title, optional subtitle, highlight chips, footer CTA.
- `slide`: tag or step label, smaller title, `3-5` bullet lines, optional footer.
- `quote`: oversized statement with minimal decoration.
- `checklist`: title plus stacked checklist items and a short CTA.

Read `references/visual-spec.md` when you need spacing, hierarchy, safe-margin, or ratio guidance.

## Render with bundled resources

Use `scripts/render_text_card_svg.py` for deterministic output.

- Feed the script a single-card JSON spec or a multi-card series spec.
- Start from `assets/themes/warm-note.json` or `assets/themes/sharp-contrast.json`.
- Duplicate `assets/specs/example-cover.json` or `assets/specs/example-carousel.json` instead of inventing the schema from scratch.
- Use `--format svg` for editable vector output.
- Use `--format png` or `--format jpg` for ready-to-post assets.
- Use `--scale 2` when you want 2x raster output.

Raster export uses a bundled macOS AppKit renderer through `xcrun swift`. It keeps the original canvas size and avoids the text clipping issues that Quick Look thumbnails introduced.

Example:

```bash
python3 scripts/render_text_card_svg.py \
  --spec assets/specs/example-carousel.json \
  --theme assets/themes/warm-note.json \
  --format png \
  --output-dir /tmp/xhs-demo
```

## Check the result before handoff

Inspect every generated page:

- The hook must be readable within 2 seconds.
- No page should contain more than one core message.
- Accent color should appear only on the hook, highlights, or CTA.
- Text must stay inside safe margins with visible breathing room.
- The series should look like one system, not unrelated posters.

## Use the bundled files

- Use `scripts/render_text_card_svg.py` to generate SVG, PNG, or JPG cards from JSON specs.
- Read `references/content-patterns.md` for headline, hook, and carousel-copy heuristics.
- Read `references/visual-spec.md` for ratio, spacing, hierarchy, and readability rules.
- Start from the sample theme/spec assets and then adjust only what the task actually needs.

---

## 🌐 了解更多

更多技能请访问：[nexaclaw.cn](https://nexaclaw.cn)
