#!/usr/bin/env python3
"""
generate_screenshots.py — Extract thread slides from the interactive page.

Playwright explores the interactive and captures:
- Default state (the establishing shot)
- Key hover states (surprising countries)
- Interesting filtered views

Then picks the best 3 as thread slides and writes thread captions.

Usage:
  python pipeline/generate_screenshots.py staged/<slug>/
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
AUTH_PATH = Path.home() / ".openclaw/agents/main/agent/auth-profiles.json"
SKILL_PATH = Path(__file__).parent / "skills" / "ATLAS_POST_SKILL.md"


def get_key():
    with open(AUTH_PATH) as f:
        return json.load(f)["profiles"]["anthropic:claude"]["token"]

def ask_claude(prompt, max_tokens=4000):
    client = anthropic.Anthropic(api_key=get_key())
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


async def capture_screenshots(post_dir: Path, slug: str, research: dict) -> list:
    """Capture candidate screenshots from the interactive."""
    from playwright.async_api import async_playwright

    html_path = post_dir / f"{slug}-interactive.html"
    if not html_path.exists():
        # Try to find it
        candidates = list(post_dir.glob("*-interactive.html"))
        if not candidates:
            raise FileNotFoundError(f"No interactive HTML found in {post_dir}")
        html_path = candidates[0]

    screenshots = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 1280})
        await page.goto(f"file://{html_path.resolve()}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2.0)

        # ── Shot 1: Hero + map (top of page) ─────────────────────────────────
        await page.evaluate("window.scrollTo(0,0)")
        await asyncio.sleep(0.3)
        path1 = post_dir / "shot-1-hero.png"
        await page.screenshot(
            path=str(path1), full_page=False,
            clip={"x":0,"y":0,"width":1280,"height":1280}
        )
        screenshots.append({"path": str(path1), "label": "hero_map", "desc": "Hero + map overview"})

        # ── Shot 2: Hover the key outlier country ─────────────────────────────
        outliers = research.get("outliers", [])
        if outliers:
            outlier_name = outliers[0]["country"]
            try:
                # Try to hover a country path
                # Look for SVG paths in the countries group
                hovered = await page.evaluate(f"""() => {{
                    const paths = document.querySelectorAll('#countries path');
                    for (const p of paths) {{
                        const bb = p.getBoundingClientRect();
                        if (bb.width > 10 && bb.height > 10) {{
                            const evt = new MouseEvent('mouseenter', {{bubbles:true, clientX: bb.left+bb.width/2, clientY: bb.top+bb.height/2}});
                            p.dispatchEvent(evt);
                            const move = new MouseEvent('mousemove', {{bubbles:true, clientX: bb.left+bb.width/2, clientY: bb.top+bb.height/2}});
                            p.dispatchEvent(move);
                            return true;
                        }}
                    }}
                    return false;
                }}""")
                await asyncio.sleep(0.5)
                path2 = post_dir / "shot-2-hover.png"
                await page.screenshot(
                    path=str(path2), full_page=False,
                    clip={"x":0,"y":0,"width":1280,"height":1280}
                )
                screenshots.append({"path": str(path2), "label": "hover_outlier", "desc": f"Map with tooltip hover"})
            except Exception as e:
                print(f"   ⚠️  Hover shot failed: {e}")

        # ── Shot 3: Scroll to chart / scatter ─────────────────────────────────
        chart_y = await page.evaluate("""() => {
            const s = document.querySelector('.scatter-wrap, .chart-section, #scatter-svg, #scatter');
            return s ? s.getBoundingClientRect().top + window.scrollY - 80 : 600;
        }""")
        await page.evaluate(f"window.scrollTo(0, {chart_y})")
        await asyncio.sleep(0.4)
        path3 = post_dir / "shot-3-chart.png"
        await page.screenshot(
            path=str(path3), full_page=False,
            clip={"x":0,"y":0,"width":1280,"height":1280}
        )
        screenshots.append({"path": str(path3), "label": "chart", "desc": "Chart / scatter view"})

        # ── Shot 4: Table with OECD filter ────────────────────────────────────
        try:
            oecd_btn = await page.query_selector('.filter-btn:nth-child(2), [onclick*="oecd"]')
            if oecd_btn:
                table_y = await page.evaluate("""() => {
                    const t = document.querySelector('.table-section, table');
                    return t ? t.getBoundingClientRect().top + window.scrollY - 80 : 900;
                }""")
                await page.evaluate(f"window.scrollTo(0, {table_y})")
                await asyncio.sleep(0.3)
                await oecd_btn.click()
                await asyncio.sleep(0.4)
                path4 = post_dir / "shot-4-table.png"
                await page.screenshot(
                    path=str(path4), full_page=False,
                    clip={"x":0,"y":0,"width":1280,"height":1280}
                )
                screenshots.append({"path": str(path4), "label": "table_filtered", "desc": "Filtered data table"})
        except Exception as e:
            print(f"   ⚠️  Table shot failed: {e}")

        await browser.close()

    return screenshots


async def render_slide(html: str, output_path: str, w=1080, h=1080):
    """Render a slide HTML to PNG."""
    from playwright.async_api import async_playwright
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp:
        tmp.write(html); tmp_path = tmp.name
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": w, "height": h})
            await page.goto(f"file://{Path(tmp_path).resolve()}")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1.5)
            await page.screenshot(path=output_path, full_page=False,
                                  clip={"x":0,"y":0,"width":w,"height":h})
            await browser.close()
    finally:
        os.unlink(tmp_path)


def generate_slides_and_thread(post_dir: Path, slug: str, research: dict, screenshots: list):
    """Use Claude to design 3 slides based on what was found in the interactive."""
    skill_text = SKILL_PATH.read_text() if SKILL_PATH.exists() else ""

    print("\n🎨 Designing thread slides from interactive moments...")

    slides_prompt = f"""You are creating a 3-slide Twitter/X thread for Atlas of Culture.

## The interactive webpage you built covers:
{json.dumps(research, indent=2)}

## What the interactive contains
{json.dumps([s['desc'] for s in screenshots], indent=2)}

## Your job
Design 3 slides (1080×1080px HTML each) that work as a thread:
- Slide 1: The hook — most surprising fact, establishes the story. MUST include a choropleth world map.
- Slide 2: The depth — a chart, scatter plot, or comparison that shows the pattern/correlation.
- Slide 3: The "why" — text-forward, 3 key facts explaining what drives the data.

Plus write 4 tweet captions (tweets 1-3 accompany the slides, tweet 4 is a text-only link to the interactive).

## Production skill (follow precisely)
{skill_text}

## Output format
Return a JSON object:
{{
  "slide_1_html": "complete 1080x1080 HTML for slide 1",
  "slide_2_html": "complete 1080x1080 HTML for slide 2",
  "slide_3_html": "complete 1080x1080 HTML for slide 3",
  "tweet_1": "caption for slide 1 (hook)",
  "tweet_2": "caption for slide 2 (depth)",
  "tweet_3": "caption for slide 3 (why)",
  "tweet_4": "text-only tweet with interactive link placeholder [LINK]"
}}

Each HTML slide must:
- Be exactly 1080×1080px, overflow:hidden
- Include grain overlay (body::before SVG fractalNoise, opacity:0.04)
- Use Playfair Display + IBM Plex Mono + Inter (Google Fonts)
- All text rgba(255,255,255,0.62) minimum — no unreadably dim text
- Dark background #07070c
- Slide 1 must use the GeoJSON map (https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson)
- US/Canada labels in header text, not on SVG map (they get cropped)
- flex layout, no fixed grid-template-rows — let content fill naturally

Return ONLY valid JSON. No explanation. No markdown fences."""

    raw = ask_claude(slides_prompt, max_tokens=8000)
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        print(f"ERROR parsing slides JSON")
        sys.exit(1)
    slides = json.loads(m.group())

    # Render slides
    print("\n🖼  Rendering slides...")
    for i, key in enumerate(['slide_1_html', 'slide_2_html', 'slide_3_html'], 1):
        html = slides.get(key, '')
        if html:
            out = str(post_dir / f"slide-{i}.png")
            asyncio.run(render_slide(html, out))
            with open(post_dir / f"slide-{i}.html", "w") as f:
                f.write(html)
            print(f"   ✅ slide-{i}.png")

    # Write captions
    captions = "\n\n".join([
        f"== TWEET 1 (slide-1.png) ==\n{slides.get('tweet_1','')}",
        f"== TWEET 2 (slide-2.png) ==\n{slides.get('tweet_2','')}",
        f"== TWEET 3 (slide-3.png) ==\n{slides.get('tweet_3','')}",
        f"== TWEET 4 (no image — link) ==\n{slides.get('tweet_4','')}",
    ])
    with open(post_dir / "captions.txt", "w") as f:
        f.write(captions)
    print("   ✅ captions.txt")

    return slides


def main(post_dir_str: str):
    post_dir = Path(post_dir_str)
    if not post_dir.exists():
        print(f"ERROR: {post_dir_str} does not exist")
        sys.exit(1)

    # Load metadata + research
    meta_path = post_dir / "metadata.json"
    research_path = post_dir / "research.json"
    if not meta_path.exists():
        print("ERROR: No metadata.json — run generate_interactive.py first")
        sys.exit(1)

    with open(meta_path) as f: meta = json.load(f)
    research = json.loads(research_path.read_text()) if research_path.exists() else {}
    slug = meta["slug"]

    print(f"\n📸 Atlas of Culture — Screenshot Generator")
    print(f"   Post: {meta.get('title')}")

    # Capture screenshots from interactive
    print("\n🔍 Exploring interactive page...")
    shots = asyncio.run(capture_screenshots(post_dir, slug, research))
    print(f"   ✅ {len(shots)} screenshots captured")

    # Generate slides + thread
    generate_slides_and_thread(post_dir, slug, research, shots)

    # Update metadata
    meta["status"] = "slides_built"
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Thread ready for review: staged/{slug}/")
    print(f"\n   Review:")
    print(f"   open staged/{slug}/slide-1.png")
    print(f"   cat staged/{slug}/captions.txt")
    print(f"\n   Approve:")
    print(f"   python pipeline/approve_post.py staged/{slug}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("post_dir", help="Path to staged/<slug>/")
    args = parser.parse_args()
    main(args.post_dir)
