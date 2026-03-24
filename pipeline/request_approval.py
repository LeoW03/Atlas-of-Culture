#!/usr/bin/env python3
"""
request_approval.py — Request Leo's approval for a staged post.

Fires an OpenClaw system event to wake the agent, which then sends
the preview through whatever channel Leo is on (Telegram, webchat, etc).

Usage:
  python pipeline/request_approval.py staged/<slug>/
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
GITHUB_PAGES_URL = "https://leow03.github.io/Atlas-of-Culture"


def request_approval(post_dir_str: str):
    post_dir = Path(post_dir_str)
    meta_path = post_dir / "metadata.json"

    if not meta_path.exists():
        print(f"ERROR: No metadata.json in {post_dir_str}")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    slug = meta["slug"]
    title = meta.get("title", slug)
    slides = meta.get("slides", [])
    interactive_url = meta.get("interactive_url", f"{GITHUB_PAGES_URL}/{slug}/")
    image_count = len(list(post_dir.glob("image_*.png")))
    has_interactive = bool(list(post_dir.glob("*-interactive.html")))

    # Check QC
    qc_path = post_dir / "qc_report.json"
    if qc_path.exists():
        with open(qc_path) as f:
            qc = json.load(f)
        if qc.get("overall") == "fail":
            print(f"❌ QC failed — fix issues before requesting approval")
            sys.exit(1)

    # Build event text for the agent to deliver
    preview_lines = [
        f"ATLAS APPROVAL REQUEST",
        f"Post: {title} ({slug})",
        f"Slides: {image_count} | Interactive: {'yes' if has_interactive else 'no'}",
        f"Interactive URL: {interactive_url}",
        f"",
        f"TWEET 1: {slides[0][:200] if slides else '—'}",
        f"TWEET 2: {slides[1][:200] if len(slides)>1 else '—'}",
        f"TWEET 3: {slides[2][:200] if len(slides)>2 else '—'}",
        f"TWEET 4: Full dataset → {interactive_url}",
        f"",
        f"Approve with: python pipeline/approve_post.py {post_dir_str}",
    ]
    event_text = "\n".join(preview_lines)

    # Fire system event — agent wakes and delivers to Leo
    print(f"\n📨 Requesting approval for: {title}")
    try:
        result = subprocess.run(
            ["openclaw", "system", "event",
             "--text", event_text,
             "--mode", "now"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Approval request sent")
        else:
            print(f"⚠️  Could not send event: {result.stderr[:100]}")
            print(f"\nManual preview:\n{event_text}")
    except Exception as e:
        print(f"⚠️  Error: {e}")
        print(f"\nManual preview:\n{event_text}")

    # Update status
    meta["status"] = "awaiting_approval"
    meta["approval_requested_at"] = datetime.now(timezone.utc).isoformat()
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n   Approve: python pipeline/approve_post.py {post_dir_str}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline/request_approval.py staged/<slug>/")
        sys.exit(1)
    request_approval(sys.argv[1])
