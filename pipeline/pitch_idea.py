#!/usr/bin/env python3
"""
pitch_idea.py — Research + pitch a post idea to Leo for approval before generating.

Usage:
  python pipeline/pitch_idea.py
  python pipeline/pitch_idea.py --topic "coffee trade routes" --pillar economics
  python pipeline/pitch_idea.py --count 3  # pitch 3 ideas at once

Leo reviews the pitch and approves one before generate_content.py runs.
Approved pitches are saved to staged/<slug>/pitch.json.
"""

import argparse
import json
import re
import sys
import random
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
STAGED_DIR = ROOT / "staged"
AUTH_PATH = Path.home() / ".openclaw/agents/main/agent/auth-profiles.json"

PILLARS = ["mobility", "economics", "language", "environment", "information", "health", "democracy"]
PILLAR_DESCRIPTIONS = {
    "mobility":    "Who can go where. Passports, visas, immigration, movement.",
    "economics":   "What things cost. What people earn. PPP-adjusted reality of daily life.",
    "language":    "How languages spread, borrow, die. How culture moves.",
    "environment": "Cities, trees, concrete, air, water. How humans shaped the physical world.",
    "information": "Censorship, surveillance, press freedom, AI governance.",
    "health":      "Drug prices, life expectancy, disease, healthcare access.",
    "democracy":   "Elections, governance, institutional trust, power transfer.",
}

def get_anthropic_key():
    if AUTH_PATH.exists():
        with open(AUTH_PATH) as f:
            return json.load(f)["profiles"]["anthropic:claude"]["token"]
    raise RuntimeError("No Anthropic key found")

def ask_claude(prompt):
    client = anthropic.Anthropic(api_key=get_anthropic_key())
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text)[:60].strip("-")

def generate_pitches(topic=None, pillar=None, count=1):
    if not pillar:
        pillar = random.choice(PILLARS)

    prompt = f"""You are a data journalist for Atlas of Culture, an anonymous data visualization account.
The account posts data and maps about the strangeness of human civilization — curious, precise, never preachy.
Audience: globally literate, 25-40, would read The Economist but finds it too dry.

Pillar: {pillar} — {PILLAR_DESCRIPTIONS[pillar]}
{"Topic hint: " + topic if topic else "Pick a compelling topic within this pillar."}

Generate {count} distinct post idea{"s" if count > 1 else ""}.

For each idea, the KEY test: Would this surprise someone who already considers themselves well-informed?
Not "X is expensive" — everyone knows that.
YES: "X pays 8× more than comparable peers for the same thing" — the peer comparison is the surprise.

For each pitch include:
- title: 5-8 word evocative title
- slug: url-friendly
- hook: ONE sentence — the most surprising specific fact (include actual numbers)
- peer_angle: why the peer comparison is more surprising than the extreme comparison
- data_source: real, verifiable source (World Bank, WHO, UNESCO, RAND, etc.)
- viz_type: "map" (preferred for geographic data) or "comparison" or "timeline"
- pillar: which pillar

Return a JSON array of {count} pitch object{"s" if count > 1 else ""}.
Return ONLY valid JSON, no explanation."""

    raw = ask_claude(prompt)
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        # Try single object
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return [json.loads(match.group())]
        raise ValueError(f"Could not parse pitch JSON:\n{raw}")
    return json.loads(match.group())


def format_pitch(p, i=None):
    prefix = f"\n{'='*60}\n"
    if i is not None:
        prefix += f"  IDEA {i+1}\n{'='*60}\n"
    else:
        prefix += f"{'='*60}\n"
    return f"""{prefix}
  📌 {p['title'].upper()}

  Hook:    {p['hook']}

  Why it's surprising:
           {p.get('peer_angle', '—')}

  Viz:     {p.get('viz_type','map')} | Pillar: {p.get('pillar','—')}
  Source:  {p.get('data_source', p.get('source','—'))}
  Slug:    {p.get('slug','—')}
"""


def main():
    parser = argparse.ArgumentParser(description="Pitch an Atlas of Culture post idea")
    parser.add_argument("--topic", help="Topic hint")
    parser.add_argument("--pillar", choices=PILLARS)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--auto", action="store_true", help="Skip interactive prompt (for pipeline use)")
    args = parser.parse_args()

    print("\n🌍 Atlas of Culture — Idea Pitcher")
    print(f"   Generating {args.count} idea{'s' if args.count > 1 else ''}...\n")

    pitches = generate_pitches(topic=args.topic, pillar=args.pillar, count=args.count)

    for i, p in enumerate(pitches):
        print(format_pitch(p, i if len(pitches) > 1 else None))

    if args.auto:
        # Non-interactive: save all pitches and exit, Leo reviews separately
        STAGED_DIR.mkdir(exist_ok=True)
        saved = []
        for p in pitches:
            slug = slugify(p.get('slug', p['title']))
            pitch_data = {**p, "slug": slug, "status": "pitched",
                          "created_at": datetime.now(timezone.utc).isoformat()}
            post_dir = STAGED_DIR / slug
            post_dir.mkdir(exist_ok=True)
            with open(post_dir / "pitch.json", "w") as f:
                json.dump(pitch_data, f, indent=2)
            saved.append(slug)
            print(f"📋 Saved pitch: staged/{slug}/pitch.json")
        print(f"\n✅ {len(saved)} pitch(es) saved. Review and approve with:")
        print(f"   python pipeline/pitch_idea.py --approve <slug>")
        return

    # Interactive mode
    if len(pitches) == 1:
        print("\nApprove this idea? [y/n/edit] ", end="", flush=True)
        choice = input().strip().lower()
    else:
        print(f"\nWhich idea to develop? [1-{len(pitches)}/n] ", end="", flush=True)
        choice = input().strip().lower()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(pitches):
                choice = 'y'
                pitches = [pitches[idx]]
            else:
                choice = 'n'

    if choice in ('y', 'yes'):
        p = pitches[0]
        slug = slugify(p.get('slug', p['title']))
        pitch_data = {**p, "slug": slug, "status": "approved",
                      "created_at": datetime.now(timezone.utc).isoformat()}
        STAGED_DIR.mkdir(exist_ok=True)
        post_dir = STAGED_DIR / slug
        post_dir.mkdir(exist_ok=True)
        with open(post_dir / "pitch.json", "w") as f:
            json.dump(pitch_data, f, indent=2)
        print(f"\n✅ Approved! Now generate the post:")
        print(f"   python pipeline/generate_content.py --from-pitch staged/{slug}/pitch.json")
    else:
        print("\n↩ Discarded. Run again for new ideas.")


if __name__ == "__main__":
    main()
