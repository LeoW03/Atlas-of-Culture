#!/usr/bin/env python3
"""
generate_interactive.py — Build the interactive companion page first.

This is the primary creative step. The interactive IS the product.
Screenshots and thread copy come from this, not the other way around.

Usage:
  python pipeline/generate_interactive.py --from-pitch staged/<slug>/pitch.json
  python pipeline/generate_interactive.py --topic "teacher pay" --pillar education
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
STAGED_DIR = ROOT / "staged"
AUTH_PATH = Path.home() / ".openclaw/agents/main/agent/auth-profiles.json"
SKILL_PATH = Path(__file__).parent / "skills" / "ATLAS_POST_SKILL.md"

PILLARS = ["mobility","economics","language","environment","information","health","democracy","education"]

def get_key():
    with open(AUTH_PATH) as f:
        return json.load(f)["profiles"]["anthropic:claude"]["token"]

def ask_claude(prompt, max_tokens=8000):
    client = anthropic.Anthropic(api_key=get_key())
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text)[:60].strip("-")

async def verify_interactive(html_path: str) -> dict:
    """Run the interactive in Playwright and check it works."""
    from playwright.async_api import async_playwright
    results = {"ok": False, "countries": 0, "errors": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await page.goto(f"file://{Path(html_path).resolve()}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2.5)
        # Check map rendered
        try:
            count = await page.evaluate(
                'document.getElementById("countries") ? '
                'document.getElementById("countries").children.length : 0'
            )
            results["countries"] = count
        except:
            pass
        results["errors"] = errors[:5]
        results["ok"] = results["countries"] > 50 and len(errors) == 0
        await browser.close()
    return results


def generate(topic=None, pillar=None, pitch_path=None):
    skill_text = SKILL_PATH.read_text() if SKILL_PATH.exists() else ""

    # Load pitch if provided
    pitch = {}
    if pitch_path:
        with open(pitch_path) as f:
            pitch = json.load(f)
        topic = pitch.get("hook") or pitch.get("title")
        pillar = pitch.get("pillar", pillar)
        slug = slugify(pitch.get("slug", pitch.get("title", topic)))
        print(f"\n📋 Loaded pitch: {pitch.get('title')}")
        print(f"   Hook: {pitch.get('hook','')[:80]}")
    else:
        slug = slugify(topic or "atlas-post")

    post_dir = STAGED_DIR / slug
    post_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🌍 Atlas of Culture — Interactive Builder")
    print(f"   Topic: {topic}")
    print(f"   Slug: {slug}\n")

    # ── Step 1: Deep data research ────────────────────────────────────────────
    print("🔍 Researching data...")
    research_prompt = f"""You are a data journalist for Atlas of Culture.
Topic: {topic}
Pillar: {pillar or 'general'}

Research this topic deeply. Your goal: find the data that would power a rich, explorable interactive webpage.

Return JSON with:
{{
  "title": "evocative title",
  "slug": "url-slug",
  "key_insight": "the single most surprising finding (specific numbers, peer comparison)",
  "peer_angle": "why comparing to peer/similar countries is more surprising than extreme comparison",
  "data_points": [
    {{"country": "...", "value": 0.0, "pisa_or_secondary": null, "region": "oecd|asia|latam|africa|mideast", "note": "optional context"}}
  ],
  "data_min": 0.0,
  "data_max": 0.0,
  "unit": "% of national avg | USD | index score | etc",
  "color_direction": "high_good | high_bad | diverging_from_100",
  "sources": ["OECD EAG 2023", "..."],
  "narrative_sections": [
    {{"heading": "...", "body": "2-3 paragraphs of prose"}}
  ],
  "outliers": [
    {{"country": "...", "why_interesting": "..."}}
  ]
}}

Use real data from OECD, World Bank, WHO, UNESCO, RAND, Henley, etc.
Include at least 40 countries with real values.
Return only valid JSON."""

    raw = ask_claude(research_prompt, max_tokens=6000)
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        print(f"ERROR parsing research: {raw[:200]}")
        sys.exit(1)
    research = json.loads(m.group())
    print(f"   ✅ {len(research.get('data_points', []))} countries researched")
    print(f"   Key insight: {research.get('key_insight','')[:80]}")

    # Save research for later steps
    with open(post_dir / "research.json", "w") as f:
        json.dump(research, f, indent=2)

    # ── Step 2: Build interactive HTML ────────────────────────────────────────
    print("\n🌐 Building interactive page...")

    html_prompt = f"""You are building a premium interactive data journalism webpage for Atlas of Culture.

## Research data
{json.dumps(research, indent=2)}

## Production skill
{skill_text}

## What to build
A single self-contained HTML file (no build step, no external frameworks) that includes:

1. **Hero section** — headline (specific numbers, peer comparison), 3-4 stat pills, subhead
2. **Interactive choropleth map** — SVG world map, hover tooltip showing country + value + context
   - GeoJSON URL: https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson
   - Use equirectangular projection, sqrt color compression for visual range
   - Tooltip: country name, value, brief insight (e.g. "USA pays 8× more than Germany")
   - Map dims: viewBox="-40 33 984 330", preserveAspectRatio="xMidYMid meet"
3. **Scatter plot** (if secondary metric available) or **ranked bar chart** — with hover
4. **Filterable data table** — all countries, region filters, sortable
5. **Narrative** — 3-5 sections with headings, pull quotes, the "why this happens" explanation
6. **Sources & caveats section** — comes just before the footer. Two subsections:
   - "Data sources": each source as a linked item with name, URL, and one sentence on what it covers and data year
   - "Caveats & methodology notes": an honest list of the things a careful reader should know about this data — data age, methodology differences, what the metric does and doesn't capture, known gaps. Write ONLY the caveats that actually matter for this specific dataset. Do not pad to hit a number. Two real caveats is better than five generic ones. Things like "PISA only measures 15-year-olds" belong here; things like "data may be imperfect" do not.
7. **Footer** — @atlasofculture + sources

## Design requirements
- Dark background #07070c, Playfair Display + IBM Plex Mono + Inter (Google Fonts)
- Color scale depends on data direction: {research.get('color_direction','high_bad')}
  - high_bad: deep blue (low/good) → amber → gold (high/bad outlier)
  - high_good: terracotta (low/bad) → muted (average) → teal → gold (high/good)
  - diverging_from_100: red (below avg) → muted (parity) → teal → gold (above avg)
- Grain overlay (body::before), no vignette needed for interactive
- All text must be ≥ rgba(255,255,255,0.5) — legible on dark background
- Muted text: rgba(255,255,255,0.45), body: rgba(255,255,255,0.62), headlines: #f0ece0
- Sources section styles: `.sources-section` max-width 760px, padding 52px 64px 72px, border-top 1px solid rgba(255,255,255,0.06). Source items have a left border in gold. Caveats are an unstyled list where each item starts with an em-dash (—) in muted gold, font-size 13.5px, rgba(255,255,255,0.38).

## Critical
- The ENTIRE page should be a single HTML file, fully self-contained
- All data hardcoded (no external data fetches except GeoJSON + Google Fonts)
- Must work in Playwright headless Chrome
- Include id="countries" on the SVG group containing country paths (for verification)

Return ONLY the complete HTML. No explanation. No markdown fences."""

    html = ask_claude(html_prompt, max_tokens=8000)
    html = re.sub(r'^```html\n?', '', html, flags=re.MULTILINE)
    html = re.sub(r'^```\n?', '', html, flags=re.MULTILINE)
    html = html.strip()

    html_path = post_dir / f"{slug}-interactive.html"
    with open(html_path, "w") as f:
        f.write(html)
    print(f"   ✅ Wrote {len(html):,} chars → {html_path.name}")

    # ── Step 2b: Validate sources + caveats section ───────────────────────────
    import re as _re
    has_sources = 'sources-section' in html or 'Data sources' in html
    has_caveats = 'Caveats' in html or 'caveats' in html
    caveat_items = len(_re.findall(r'<li>', html.split('caveats')[1] if 'caveats' in html else ''))

    if not has_sources or not has_caveats:
        print(f"   ⚠️  Sources/caveats section missing — regenerating with stronger instruction...")
        # Retry with an explicit injection prompt
        inject_prompt = f"""The following HTML is missing a sources and caveats section. Add one just before the footer.

The section must:
1. Have a heading "Data sources" with each source as a linked item (name, URL, one sentence on what it covers)
2. Have a heading "Caveats & methodology notes" with an honest list of things a careful reader should know — data age, methodology differences, known gaps. Only real caveats, not generic disclaimers.
3. Use class="sources-section" on the wrapper div
4. Use class="caveats-list" on the ul

Sources for this post: {json.dumps(research.get('sources', []))}

Return the complete updated HTML. No explanation."""
        raw2 = ask_claude(inject_prompt + "\n\n" + html, max_tokens=8000)
        html2 = _re.sub(r'^```html\n?', '', raw2, flags=_re.MULTILINE)
        html2 = _re.sub(r'^```\n?', '', html2, flags=_re.MULTILINE).strip()
        if 'sources-section' in html2 or 'Data sources' in html2:
            html = html2
            with open(html_path, "w") as f:
                f.write(html)
            print(f"   ✅ Sources section added on retry")
        else:
            print(f"   ⚠️  Could not auto-add sources section — will need manual review")
    else:
        print(f"   ✅ Sources + caveats section present")

    # ── Step 3: Verify ────────────────────────────────────────────────────────
    print("\n🔍 Verifying in headless browser...")
    result = asyncio.run(verify_interactive(str(html_path)))
    if result["ok"]:
        print(f"   ✅ Map: {result['countries']} countries rendered, no errors")
    else:
        print(f"   ⚠️  Map: {result['countries']} countries, errors: {result['errors']}")
        if result['countries'] < 10:
            print("   Interactive may need manual review before proceeding.")

    # ── Step 4: Save metadata ─────────────────────────────────────────────────
    meta = {
        "slug": slug,
        "title": research.get("title", topic),
        "pillar": pillar,
        "status": "interactive_built",
        "interactive_html": str(html_path),
        "key_insight": research.get("key_insight"),
        "sources": research.get("sources", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "map_countries": result["countries"],
    }
    with open(post_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Interactive built: staged/{slug}/")
    print(f"\n   Review it:")
    print(f"   open staged/{slug}/{slug}-interactive.html")
    print(f"\n   Then generate screenshots + thread:")
    print(f"   python pipeline/generate_screenshots.py staged/{slug}/")

    return slug


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic")
    parser.add_argument("--pillar")
    parser.add_argument("--from-pitch", dest="pitch")
    args = parser.parse_args()
    generate(topic=args.topic, pillar=args.pillar, pitch_path=args.pitch)
