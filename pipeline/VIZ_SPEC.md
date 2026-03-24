# Visualization Specification — Atlas of Culture

Every visualization is a 1080×1080px HTML file rendered to PNG via Playwright (headless Chrome).

---

## Design Philosophy

**One post = one insight.** The visual exists to make one fact land in the first 2 seconds of scroll. Everything else supports that moment.

**X feed reality:**
- Viewed at ~400px on mobile. Text must be legible at half its rendered size.
- Min font size in final HTML: 18px effective (9px CSS at 2× DPR is fine).
- The "wow" must be visible before any text is read.

---

## Layout System

Every post uses a **three-zone grid** filling exactly 1080×1080px:

```
┌─────────────────────────────────┐
│  ZONE 1: HOOK          ~285px   │  eyebrow + hero number(s) + tagline
├─────────────────────────────────┤
│  ZONE 2: DATA          ~595px   │  bars / map / chart — fills 1fr
├─────────────────────────────────┤
│  ZONE 3: FOOTER        ~100px   │  context sentence + handle + source
└─────────────────────────────────┘
```

CSS skeleton:
```css
.canvas {
  position: absolute; inset: 0;
  padding: 52px 68px 46px;
  display: grid;
  grid-template-rows: 285px 1fr 100px;
}
```

The `1fr` zone must contain content that fills its space — use `flex: 1` on bar rows, or `justify-content: space-evenly` for sparse charts.

---

## Typography Stack

Always load via Google Fonts:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700;1,900&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
```

| Role | Font | Weight | Notes |
|------|------|--------|-------|
| Hero number / title | Playfair Display | 900 | Italic for emphasis phrases |
| Tagline / section titles | Playfair Display | 700 | |
| Eyebrow / labels / values | IBM Plex Mono | 400–500 | ALL CAPS + letter-spacing |
| Context / body text | Inter | 300–400 | Light weight only |

**Never use:** Inter for headlines, system fonts, generic sans.

---

## Color Palette

```
Background:     #07070c  (near-black)
Parchment alt:  #F5F0E8  (for historical / geographic pieces)

Gold (primary): #e8c547  — hero numbers, key data, US bars
Muted gold:     rgba(232,197,71,0.5–0.6) — labels, eyebrow
Steel blue:     gradient #122030→#2c6080  — secondary data bars
Terracotta:     #C45C3A  — danger / decline data
Muted green:    #7DB87D  — growth / positive data

Text primary:   rgba(255,255,255,0.65–0.75)
Text secondary: rgba(255,255,255,0.22–0.30)
Labels/meta:    rgba(255,255,255,0.10–0.18)
```

**Rule:** Never use more than 3 data colors in one viz. Restraint = sophistication.

---

## Required Visual Treatments

Every post must include:

1. **Grain overlay** — 4% opacity SVG fractalNoise, `position: absolute; inset: 0; z-index: 100`
2. **Vignette** — `radial-gradient(ellipse at 50% 25%, transparent 35%, rgba(0,0,0,0.65) 100%)`
3. **Handle** — `@atlasofculture` bottom-left, IBM Plex Mono, ~10px, very muted
4. **Source credit** — bottom-right, Inter, 9px, very muted

```css
/* Grain */
body::before {
  content: '';
  position: absolute; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  opacity: 0.04; pointer-events: none; z-index: 100;
}
/* Vignette */
body::after {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(ellipse at 50% 25%, transparent 35%, rgba(0,0,0,0.65) 100%);
  pointer-events: none; z-index: 99;
}
```

---

## Zone 1: Hook Patterns

The hook establishes the story. Choose one:

### Pattern A: Number Clash (for price/comparison stories)
Two giant numbers side by side — one gold (outlier), one ghosted (baseline).
```
[eyebrow: category · source year]
[$98]  vs  [$4]                  ← Playfair 116px, gold vs 9% opacity
[UNITED STATES]  [PAKISTAN]      ← Mono 10px, caps
[Tagline sentence. Italic emphasis.]  ← Playfair 700, 23px
```

### Pattern B: Single Hero Stat
One number dominates with a label and framing sentence.
```
[eyebrow]
[XXX] [unit label]
[Playfair tagline with em emphasis]
```

### Pattern C: Map Header
Title-first with geographic framing.
```
[TITLE IN PLAYFAIR 900]
[Subtitle / what the colors mean]
```

---

## Zone 2: Data Patterns

### Horizontal Bar Chart
- Max 8–10 rows. Never more. Fewer = clearer.
- Outlier row always highlighted (gold gradient, glow shadow).
- Separator line after outlier: `border-top: 1px solid rgba(255,255,255,0.05)`
- Use `flex: 1` on `.bar-row` so rows expand to fill the zone.
- Track background: `rgba(255,255,255,0.025)` — shows the scale.
- Bar fill: gradient, not flat color.
- Country labels: right-aligned, IBM Plex Mono, 10.5px.
- Values: right of bar, 10px mono, very muted for non-outliers.

### Choropleth Map (for geographic data)
- Use SVG paths from `visionscarto-world-atlas` (GeoJSON via CDN).
- Equirectangular projection (manual, no D3 required).
- Color scale: CSS linear interpolation with 6–8 stops.
- Graticule lines at 30° intervals: `rgba(255,255,255,0.03)`.
- No borders except on hover (if interactive).

### Scatter / Bubble
- Background grid: `rgba(255,255,255,0.03)`.
- Labeled outliers only — no labels on every point.
- Trend line if applicable: dashed, muted color.

---

## Zone 3: Footer Pattern

```html
<div class="footer-area">
  <div class="context">One sentence of human stakes or tension.</div>
  <div class="meta">
    <div class="handle">@atlasofculture</div>
    <div class="source">Data: [Source] [Year]</div>
  </div>
</div>
```

Context sentence rules:
- One sentence only. Human stakes, not methodology.
- 12.5px Inter Light, `rgba(255,255,255,0.22)`.
- No line breaks.

---

## Content Selection Rules (for LLM)

Before generating HTML, decide:
1. **Hook pattern** — which type fits the data?
2. **Hero moment** — what is the single most arresting number or fact?
3. **Data selection** — which N data points tell the story? (N ≤ 8 for bars)
4. **Outlier** — which data point should be highlighted in gold?
5. **Context sentence** — what's the human stakes in one line?

The LLM should answer these 5 questions in a `<!-- design-brief: ... -->` HTML comment before the `<style>` tag.

---

## Rendering

```python
# render.py — render HTML to 1080×1080 PNG
from playwright.async_api import async_playwright
import asyncio

async def render(html_path, output_path, w=1080, h=1080):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": w, "height": h})
        await page.goto(f"file://{Path(html_path).resolve()}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1.5)  # Google Fonts buffer
        await page.screenshot(path=output_path, full_page=False,
                              clip={"x":0,"y":0,"width":w,"height":h})
        await browser.close()
```

---

## Anti-Patterns (Never Do)

- matplotlib, seaborn, or any Python plotting library for final output
- Flat solid fills on bars (use gradients)
- More than 3 data colors
- Generic fonts (Inter/Roboto/Arial for headlines)
- Dead zones — every pixel of the canvas must feel intentional
- Context sentence that explains the chart ("This bar chart shows...")
- More than 8 data rows in a single chart
- Emojis anywhere in the image
