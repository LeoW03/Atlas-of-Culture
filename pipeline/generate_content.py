#!/usr/bin/env python3
"""
generate_content.py — Researches a topic and stages a complete post for review.

Usage:
  python pipeline/generate_content.py
  python pipeline/generate_content.py --topic "passport inequality" --pillar "mobility"
  python pipeline/generate_content.py --topic "insulin prices" --pillar "health" --type thread

Stages output to staged/<slug>/ for Leo to review and approve.
Run: python pipeline/approve_post.py staged/<slug> to queue it.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
STAGED_DIR = ROOT / "staged"
CONFIG_PATH = ROOT / "CONFIG.json"
AUTH_PATH = Path.home() / ".openclaw/agents/main/agent/auth-profiles.json"

PILLARS = [
    "mobility",
    "economics",
    "language",
    "environment",
    "information",
    "health",
    "democracy",
]

PILLAR_DESCRIPTIONS = {
    "mobility":    "Who can go where. Passports, visas, immigration, movement. The geography of freedom of movement.",
    "economics":   "What things cost. What people earn. What a dollar buys. PPP-adjusted reality of daily life.",
    "language":    "How languages spread, borrow, die. How culture moves — music, film, food, words.",
    "environment": "Cities, trees, concrete, air, water. How humans have shaped the physical world.",
    "information": "Censorship, surveillance, press freedom, AI governance. Who controls what you know.",
    "health":      "Drug prices, life expectancy, disease, healthcare access. The body as political terrain.",
    "democracy":   "Elections, governance, institutional trust. How power is organized and transferred.",
}

BRAND_COLORS = {
    "bg":        "#0F0F0F",
    "parchment": "#F5F0E8",
    "gold":      "#E8C547",
    "blue":      "#4A9EBF",
    "terracotta":"#C45C3A",
    "green":     "#7DB87D",
    "text":      "#FFFFFF",
    "ink":       "#1A1A1A",
    "muted":     "#888888",
}


def get_anthropic_key() -> str:
    if AUTH_PATH.exists():
        with open(AUTH_PATH) as f:
            d = json.load(f)
        return d["profiles"]["anthropic:claude"]["token"]
    raise RuntimeError("No Anthropic key found in auth-profiles.json")


def ask_claude(prompt: str) -> str:
    """Call Claude API directly, return response text."""
    client = anthropic.Anthropic(api_key=get_anthropic_key())
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-")


def generate(topic: str = None, pillar: str = None, post_type: str = "single"):
    import random

    if not pillar:
        pillar = random.choice(PILLARS)
    if pillar not in PILLARS:
        print(f"Unknown pillar '{pillar}'. Choose from: {', '.join(PILLARS)}")
        sys.exit(1)

    print(f"\n🌍 Atlas of Culture — Content Generator")
    print(f"   Pillar: {pillar} | Type: {post_type}")
    if topic:
        print(f"   Topic: {topic}")
    print()

    # ── Step 1: Research ────────────────────────────────────────────────────
    print("🔍 Researching data angle...")

    research_prompt = f"""You are a data journalist for an anonymous data visualization account called Atlas of Culture.
The account posts data and maps about the strangeness of human civilization — curious, precise, never preachy.

Pillar: {pillar} — {PILLAR_DESCRIPTIONS[pillar]}
{"Topic: " + topic if topic else "Pick a compelling topic within this pillar."}

Find ONE specific, counterintuitive, or surprising data story. Requirements:
- Must be based on real, verifiable data from sources like World Bank, WHO, UNESCO, Our World in Data, Freedom House, SIPRI, UN FAO, Eurostat
- Should make someone pause and think "I didn't know that" or "why is it like that?"
- Prefer: geographic surprise, scale contrast, historical depth, human stakes
- Avoid: obvious stories, US-centric takes, anything that requires a political stance

Return a JSON object with these exact fields:
{{
  "title": "short evocative title (5-8 words)",
  "slug": "url-friendly-slug",
  "data_story": "2-3 sentences describing the specific data angle",
  "hook": "one arresting sentence — the most surprising fact, under 200 chars",
  "source": "primary data source name and URL",
  "viz_description": "what the ideal visualization looks like (chart type, what's on axes, what pattern emerges)",
  "use_parchment": false
}}

use_parchment should be true only for geographic/historical posts.
Return only valid JSON, no explanation."""

    research_raw = ask_claude(research_prompt)
    # Extract JSON from response
    json_match = re.search(r'\{.*\}', research_raw, re.DOTALL)
    if not json_match:
        print(f"ERROR: Could not parse research JSON:\n{research_raw}")
        sys.exit(1)
    research = json.loads(json_match.group())

    title = research["title"]
    slug = slugify(research.get("slug", title))
    print(f"   ✅ Story: {title}")
    print(f"   📊 {research['data_story'][:100]}...")

    # ── Step 2: Viz code ─────────────────────────────────────────────────────
    print("\n📊 Generating visualization code...")

    bg_color = BRAND_COLORS["parchment"] if research.get("use_parchment") else BRAND_COLORS["bg"]
    text_color = BRAND_COLORS["ink"] if research.get("use_parchment") else BRAND_COLORS["text"]

    # Load production skill + viz spec for the prompt
    skill_path = Path(__file__).parent / "skills" / "ATLAS_POST_SKILL.md"
    viz_spec_path = Path(__file__).parent / "VIZ_SPEC.md"
    skill_text = skill_path.read_text() if skill_path.exists() else ""
    viz_spec = viz_spec_path.read_text() if viz_spec_path.exists() else ""
    production_guide = f"{skill_text}\n\n---\n\n{viz_spec}"

    viz_prompt = f"""You are building a 1080×1080px HTML visualization for a data journalism account called Atlas of Culture.

## Story
Title: {title}
Data story: {research['data_story']}
Viz type needed: {research['viz_description']}
Source: {research['source']}
Background: {"parchment (#F5F0E8)" if research.get("use_parchment") else "near-black (#07070c)"}

## Production Guide (follow precisely)
{production_guide}

## Your task
Write a single self-contained HTML file that:
1. Starts with a `<!-- design-brief: [hook pattern, hero moment, data selection, outlier, context sentence] -->` comment
2. Loads Google Fonts: Playfair Display (400,700,900 + italic), IBM Plex Mono (400,500), Inter (300,400,600)
3. Uses the exact three-zone grid layout (285px / 1fr / 100px) from the spec
4. Includes grain overlay and vignette as `body::before` and `body::after`
5. Has `body` exactly 1080×1080px, overflow:hidden
6. Hardcodes real, accurate data values (no external fetches, no placeholders)
7. Uses JS only if needed to render bars dynamically (optional for simple layouts)
8. Ends with @atlasofculture handle and source credit

CRITICAL LAYOUT RULE: The three zones MUST fill the full 1080px canvas with no dead space.
Use `grid-template-rows: 285px 1fr 100px` and ensure the data zone content expands to fill `1fr`.
For bar charts: use `flex: 1` on each `.bar-row` inside a flex-direction:column container that fills the zone.

Return ONLY the complete HTML, no explanation, no markdown fences."""

    viz_html = ask_claude(viz_prompt)
    # Strip markdown fences if present
    viz_html = re.sub(r'^```html\n?', '', viz_html, flags=re.MULTILINE)
    viz_html = re.sub(r'^```\n?', '', viz_html, flags=re.MULTILINE)
    viz_html = viz_html.strip()
    print(f"   ✅ Viz HTML generated ({len(viz_html)} chars)")

    # ── Step 3: Caption ──────────────────────────────────────────────────────
    print("\n✍️  Writing caption...")

    caption_prompt = f"""Write a caption for this data visualization post on X (Twitter).

Title: {title}
Hook: {research['hook']}
Data story: {research['data_story']}
Source: {research['source']}

Caption rules (from the brand guidelines):
- Structure: [one-line hook] → [2-4 lines of context, no jargon] → [one closing line: question, tension, or small provocation] → [Source line: Data: [source] | #tags]
- Length: 100-200 words total
- Third-person observation, never "we" or "I"
- Never editorialize about what should be done
- Never take political sides
- No exclamation points on serious topics
- No word "fascinating"
- Start with the fact, let it land
- 2-3 relevant hashtags at the end (lowercase, specific not generic)

Also write a tweet-length hook (under 280 chars) — just the most arresting first line + relevant emoji if it fits naturally. This will be the actual tweet text.

Return JSON:
{{
  "caption": "full caption text",
  "caption_tweet": "under-280-char hook for the tweet itself"
}}

Return only valid JSON."""

    caption_raw = ask_claude(caption_prompt)
    json_match = re.search(r'\{.*\}', caption_raw, re.DOTALL)
    if not json_match:
        print(f"ERROR: Could not parse caption JSON:\n{caption_raw}")
        sys.exit(1)
    captions = json.loads(json_match.group())
    print(f"   ✅ Caption written")

    # ── Step 4: Thread slides (if thread) ────────────────────────────────────
    slides = []
    if post_type == "thread":
        print("\n🧵 Writing thread slides...")
        thread_prompt = f"""Write a 3-5 tweet thread for this data story. Each tweet is one slide with an image.

Title: {title}
Data story: {research['data_story']}
Hook: {research['hook']}
Source: {research['source']}

Rules:
- Tweet 1: the hook — most arresting fact, with image
- Tweets 2-4: context, depth, geographic/historical angle
- Final tweet: closing provocation or question + source line + 2-3 hashtags
- Each tweet under 280 chars
- Same voice rules: third-person, no editorializing, no exclamation points on serious topics

Return JSON array of strings, one per tweet:
["tweet 1 text", "tweet 2 text", ...]

Return only valid JSON."""

        slides_raw = ask_claude(thread_prompt)
        json_match = re.search(r'\[.*\]', slides_raw, re.DOTALL)
        if json_match:
            slides = json.loads(json_match.group())
            print(f"   ✅ {len(slides)} slides written")

    # ── Step 4b: Companion interactive HTML ──────────────────────────────────
    print("\n🌐 Generating companion interactive HTML...")
    companion_prompt = f"""You are building a full interactive HTML companion page for an Atlas of Culture post.

## Story
Title: {title}
Data story: {research['data_story']}
Source: {research['source']}

## Production guide
{skill_text}

Build a self-contained single HTML file (no build step, no external JS frameworks) that:
1. Has a hero section with headline, stat pills, and subhead
2. Has an interactive SVG world map with hover tooltips (country name + value + "USA/outlier pays N× more")
3. Has a filterable data table (by region) showing all countries sorted by value
4. Has a narrative section: why this happens, what's surprising, historical context
5. Has dark editorial design — same color system as the static post
6. Is responsive (works on desktop and mobile)
7. Uses the exact GeoJSON URL: https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson
8. Tooltip shows on hover, positioned near cursor, hides on mouse leave

Return ONLY the complete HTML, no explanation, no markdown fences."""

    companion_html = ask_claude(companion_prompt)
    companion_html = re.sub(r'^```html\n?', '', companion_html, flags=re.MULTILINE)
    companion_html = re.sub(r'^```\n?', '', companion_html, flags=re.MULTILINE)
    companion_html = companion_html.strip()
    print(f"   ✅ Companion HTML generated ({len(companion_html)} chars)")

    # ── Step 5: Write staged files ───────────────────────────────────────────
    print(f"\n💾 Staging to staged/{slug}/...")
    STAGED_DIR.mkdir(exist_ok=True)
    post_dir = STAGED_DIR / slug
    post_dir.mkdir(exist_ok=True)

    metadata = {
        "slug": slug,
        "title": title,
        "pillar": pillar,
        "post_type": post_type,
        "alt_text": research['data_story'][:125],
        "viz_html": viz_html,
        "source": research["source"],
        "use_parchment": research.get("use_parchment", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "staged",
    }
    if slides:
        metadata["slides"] = slides

    with open(post_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    with open(post_dir / "caption.txt", "w") as f:
        f.write(captions["caption"])

    with open(post_dir / "caption_tweet.txt", "w") as f:
        f.write(captions["caption_tweet"])

    # REVIEW.md
    review = f"""# {title}
**Pillar:** {pillar} | **Type:** {post_type} | **Slug:** {slug}

## Hook Tweet
{captions['caption_tweet']}

## Full Caption
{captions['caption']}

## Data Story
{research['data_story']}

## Viz Description
{research['viz_description']}

## Source
{research['source']}

---

    Approve: python pipeline/approve_post.py staged/{slug}
    Reject:  rm -rf staged/{slug}
"""
    with open(post_dir / "REVIEW.md", "w") as f:
        f.write(review)

    with open(post_dir / f"{slug}-interactive.html", "w") as f:
        f.write(companion_html)

    print(f"\n✅ Staged: staged/{slug}/")
    print(f"\n{'='*60}")
    print(f"HOOK TWEET:\n{captions['caption_tweet']}")
    print(f"{'='*60}")
    print(f"\nReview at: staged/{slug}/REVIEW.md")
    print(f"Approve:   python pipeline/approve_post.py staged/{slug}")
    print(f"Reject:    rm -rf staged/{slug}")

    return slug


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a staged Atlas of Culture post")
    parser.add_argument("--topic", help="Specific topic to cover")
    parser.add_argument("--pillar", choices=PILLARS, help="Content pillar")
    parser.add_argument("--type", dest="post_type", choices=["single", "thread"], default="single")
    parser.add_argument("--from-pitch", dest="from_pitch", help="Path to approved pitch.json")
    args = parser.parse_args()

    # Load from approved pitch if provided
    topic = args.topic
    pillar = args.pillar
    if args.from_pitch:
        pitch_path = Path(args.from_pitch)
        if not pitch_path.exists():
            print(f"ERROR: pitch file not found: {args.from_pitch}")
            sys.exit(1)
        with open(pitch_path) as f:
            pitch = json.load(f)
        if pitch.get("status") not in ("approved",):
            print(f"WARNING: pitch status is '{pitch.get('status')}', not 'approved'. Continuing anyway.")
        topic = pitch.get("hook") or pitch.get("title")
        pillar = pitch.get("pillar", pillar)
        print(f"📋 Loaded pitch: {pitch.get('title')}")
        print(f"   Hook: {pitch.get('hook','')[:80]}...")

    generate(topic=topic, pillar=pillar, post_type=args.post_type)
