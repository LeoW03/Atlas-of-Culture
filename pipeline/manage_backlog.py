#!/usr/bin/env python3
"""
manage_backlog.py — Keep the content backlog healthy.

Tracks what's in the pipeline and ensures we never run dry.
Target: 7+ posts always in queue. Warns at <5, critical at <3.

Also manages the idea bank — a pool of pre-researched pitches
ready to develop when the queue gets low.

Usage:
  python pipeline/manage_backlog.py status       # show current state
  python pipeline/manage_backlog.py replenish    # generate new pitches to fill the bank
  python pipeline/manage_backlog.py ideas        # list all banked ideas
  python pipeline/manage_backlog.py audit        # check health + recommend action
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from claude_client import ask_claude, ask_claude_json

ROOT = Path(__file__).parent.parent
IDEA_BANK_PATH = ROOT / "pipeline" / "idea_bank.json"

QUEUE_TARGET = 7     # ideal queue depth
QUEUE_WARN   = 5     # warn below this
QUEUE_CRIT   = 3     # critical below this
BANK_TARGET  = 15    # idea bank target size
BANK_MIN     = 8     # replenish when below this

PILLARS = ["mobility","economics","language","environment","information","health","democracy","education"]


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text)[:60].strip("-")


def load_idea_bank() -> list:
    if IDEA_BANK_PATH.exists():
        with open(IDEA_BANK_PATH) as f:
            return json.load(f).get("ideas", [])
    return []

def save_idea_bank(ideas: list):
    IDEA_BANK_PATH.parent.mkdir(exist_ok=True)
    with open(IDEA_BANK_PATH, "w") as f:
        json.dump({"ideas": ideas, "updated": datetime.now(timezone.utc).isoformat()}, f, indent=2)


def count_pipeline():
    """Count posts at each stage."""
    counts = {"queue": 0, "staged": 0, "pitched": 0}

    queue_file = ROOT / "content_queue.json"
    if queue_file.exists():
        with open(queue_file) as f:
            q = json.load(f)
        counts["queue"] = len([p for p in q.get("queue", []) if p.get("status") == "ready"])

    staged_dir = ROOT / "staged"
    if staged_dir.exists():
        for d in staged_dir.iterdir():
            if not d.is_dir(): continue
            pitch = d / "pitch.json"
            meta  = d / "metadata.json"
            if meta.exists():
                with open(meta) as f:
                    m = json.load(f)
                counts["staged"] += 1
            elif pitch.exists():
                counts["pitched"] += 1

    counts["bank"] = len(load_idea_bank())
    counts["total_pipeline"] = counts["queue"] + counts["staged"] + counts["pitched"]
    return counts


def get_existing_topics() -> list:
    """All topics already covered or in flight — for deduplication."""
    topics = []

    # Posted
    posted_path = ROOT / "posted_log.json"
    if posted_path.exists():
        with open(posted_path) as f:
            log = json.load(f)
        topics.extend([p.get("title","") for p in log.get("posts", [])])

    # Staged + queued
    for d in [ROOT / "staged", ROOT / "queue"]:
        if not d.exists(): continue
        for p in d.iterdir():
            for fname in ["metadata.json", "pitch.json"]:
                fpath = p / fname
                if fpath.exists():
                    with open(fpath) as f:
                        topics.append(json.load(f).get("title",""))
                    break

    # Idea bank
    topics.extend([i.get("title","") for i in load_idea_bank()])

    return [t for t in topics if t]


def generate_ideas(count: int, existing_topics: list) -> list:
    """Generate fresh post ideas, avoiding existing topics."""
    import random
    pillars = PILLARS.copy()
    random.shuffle(pillars)

    prompt = f"""You are generating content ideas for Atlas of Culture, a data visualization account.

Philosophy: Find questions worth answering through data. The interactive webpage is the product. The social posts are trailers.

The best ideas:
- Have a specific counterintuitive finding (surprise someone who thinks they're well-informed)
- Use peer comparison (wealthy nations vs each other) not just extreme comparison (rich vs poorest)
- Have real, verifiable data from World Bank, OECD, WHO, UNESCO, RAND, Henley, etc.
- Would make someone spend 10 minutes exploring an interactive map

Pillars to draw from: {', '.join(pillars[:5])}

Already covered (avoid these topics and close variations):
{chr(10).join(f"- {t}" for t in existing_topics[-20:] if t)}

Generate {count} distinct, high-quality ideas. Each must be genuinely different.

Return a JSON array:
[
  {{
    "title": "short evocative title",
    "slug": "url-slug",
    "pillar": "one of the pillars",
    "hook": "one sentence — most surprising specific fact with actual numbers",
    "peer_angle": "why the peer comparison is more surprising than extreme comparison",
    "research_question": "the genuine question this data answers",
    "data_source": "primary source (real, verifiable)",
    "viz_type": "map | scatter | timeline | comparison",
    "priority": "high | medium",
    "reason": "why this is timely or evergreen"
  }}
]

Return only valid JSON."""

    try:
        result = ask_claude_json(prompt)
        return result if isinstance(result, list) else [result]
    except Exception as e:
        print(f"   ⚠️  Could not parse ideas: {e}")
        return []


def cmd_status():
    counts = count_pipeline()
    bank = load_idea_bank()

    print("\n╔══════════════════════════════════╗")
    print("║  Atlas of Culture — Pipeline     ║")
    print("╚══════════════════════════════════╝\n")

    # Queue health
    q = counts["queue"]
    q_status = "✅" if q >= QUEUE_TARGET else "⚠️ " if q >= QUEUE_WARN else "🔴"
    print(f"  {q_status} Queue (ready to post): {q}/{QUEUE_TARGET} target")
    print(f"  📝 In staging:  {counts['staged']} posts")
    print(f"  💡 Pitched:     {counts['pitched']} ideas")
    print(f"  🗃  Idea bank:   {len(bank)} ideas")
    print()

    # Pipeline health
    total = counts["total_pipeline"]
    if q < QUEUE_CRIT:
        print(f"  🔴 CRITICAL: Queue at {q}. Post immediately or build more content.")
    elif q < QUEUE_WARN:
        print(f"  ⚠️  WARNING: Queue low at {q}. Run: python pipeline/manage_backlog.py replenish")
    else:
        print(f"  ✅ Queue is healthy.")

    if len(bank) < BANK_MIN:
        print(f"  ⚠️  Idea bank low ({len(bank)}). Run: python pipeline/manage_backlog.py replenish")

    # Next actions
    print("\n  Next actions:")
    if counts["staged"] > 0:
        print(f"    • {counts['staged']} post(s) in staging — review and approve")
    if q < QUEUE_WARN:
        print(f"    • Build more content (queue low)")
    if len(bank) > 0:
        print(f"    • {len(bank)} ideas in bank ready to develop")
        print(f"    → python pipeline/manage_backlog.py ideas")


def cmd_ideas():
    bank = load_idea_bank()
    if not bank:
        print("\n  Idea bank is empty. Run: python pipeline/manage_backlog.py replenish\n")
        return

    print(f"\n  📚 Idea Bank ({len(bank)} ideas)\n")
    for i, idea in enumerate(bank, 1):
        priority = idea.get("priority","?")
        icon = "🔥" if priority=="high" else "📌"
        print(f"  {icon} {i}. [{idea.get('pillar','?')}] {idea.get('title','?')}")
        print(f"     Hook: {idea.get('hook','?')[:90]}")
        print(f"     Source: {idea.get('data_source','?')}")
        print()


def cmd_replenish():
    bank = load_idea_bank()
    existing = get_existing_topics()
    needed = max(BANK_TARGET - len(bank), 5)

    print(f"\n  🔄 Replenishing idea bank ({len(bank)} → target {BANK_TARGET})...")
    print(f"  Generating {needed} new ideas...\n")

    new_ideas = generate_ideas(needed, existing)
    if not new_ideas:
        print("  ❌ Failed to generate ideas")
        return

    # Tag with metadata
    for idea in new_ideas:
        idea["added"] = datetime.now(timezone.utc).isoformat()
        idea["status"] = "banked"
        if "slug" not in idea:
            idea["slug"] = slugify(idea.get("title","idea"))

    bank.extend(new_ideas)
    # Keep highest priority first
    bank.sort(key=lambda x: 0 if x.get("priority")=="high" else 1)
    # Cap at 30
    bank = bank[:30]

    save_idea_bank(bank)
    print(f"  ✅ Added {len(new_ideas)} ideas. Bank now at {len(bank)}.\n")

    # Show the new ones
    print("  New ideas added:")
    for idea in new_ideas[:5]:
        print(f"  🔥 {idea.get('title')}")
        print(f"     {idea.get('hook','')[:90]}\n")


def cmd_audit():
    """Full health audit with recommendations."""
    counts = count_pipeline()
    bank = load_idea_bank()

    print("\n  📋 Full Pipeline Audit\n")
    print(f"  Queue:    {counts['queue']} ready  (target: {QUEUE_TARGET})")
    print(f"  Staging:  {counts['staged']} posts")
    print(f"  Pitched:  {counts['pitched']} ideas")
    print(f"  Bank:     {len(bank)} ideas")

    issues = []
    if counts["queue"] < QUEUE_CRIT:
        issues.append(("🔴 CRITICAL", f"Queue at {counts['queue']} — post backlog almost empty"))
    elif counts["queue"] < QUEUE_WARN:
        issues.append(("⚠️  WARN", f"Queue at {counts['queue']} — getting low"))

    if len(bank) < BANK_MIN:
        issues.append(("⚠️  WARN", f"Idea bank at {len(bank)} — below minimum {BANK_MIN}"))

    staged_without_qc = []
    staged_dir = ROOT / "staged"
    if staged_dir.exists():
        for d in staged_dir.iterdir():
            if d.is_dir() and not (d / "qc_report.json").exists():
                if (d / "metadata.json").exists():
                    staged_without_qc.append(d.name)

    if staged_without_qc:
        issues.append(("⚠️  WARN", f"{len(staged_without_qc)} staged post(s) haven't run QC: {', '.join(staged_without_qc)}"))

    if not issues:
        print("\n  ✅ Everything looks healthy.\n")
    else:
        print("\n  Issues found:")
        for severity, msg in issues:
            print(f"  {severity}: {msg}")

    print("\n  Recommended actions:")
    if counts["queue"] < QUEUE_WARN or len(bank) < BANK_MIN:
        print("  1. python pipeline/manage_backlog.py replenish")
    if counts["staged"] > 0:
        print(f"  2. python pipeline/qc_check.py staged/<slug>/  (for each staged post)")
        print(f"  3. python pipeline/approve_post.py staged/<slug>/")
    if not issues:
        print("  Keep building. 🌍")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["status","replenish","ideas","audit"],
                        nargs="?", default="status")
    args = parser.parse_args()

    {
        "status":    cmd_status,
        "replenish": cmd_replenish,
        "ideas":     cmd_ideas,
        "audit":     cmd_audit,
    }[args.command]()
