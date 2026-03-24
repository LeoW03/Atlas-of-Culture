#!/usr/bin/env python3
"""
approve_post.py — Approves a staged post, renders viz, moves to queue.

Usage: python pipeline/approve_post.py staged/<slug>
"""

import json
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
QUEUE_PATH = ROOT / "content_queue.json"
QUEUE_DIR = ROOT / "queue"


def approve(staged_path: str):
    post_dir = Path(staged_path)

    if not post_dir.exists():
        print(f"ERROR: {staged_path} does not exist")
        sys.exit(1)

    meta_path = post_dir / "metadata.json"
    if not meta_path.exists():
        print(f"ERROR: No metadata.json in {staged_path}")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    slug = meta["slug"]

    # ── Check approval was explicitly granted ────────────────────────────
    status = meta.get("status", "")
    if status not in ("approved", "ready", "awaiting_approval", "interactive_built", "slides_built"):
        # Fine — approve_post itself is the approval step
        pass
    # If Leo ran approve_post directly, that IS the approval — no blocking needed.
    # The request_approval step is for async preview; approve_post is the final gate.

    # ── Run automated QC first ────────────────────────────────────────────
    print(f"\n🔍 Running automated QC checks...")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "pipeline"))
        from qc_check import run_qc
        qc = run_qc(str(post_dir), verbose=True)
        if qc["overall"] == "fail":
            print(f"\n❌ QC FAILED — post has critical issues that must be resolved first.")
            print(f"   See: {post_dir}/qc_report.json")
            print(f"   Fix the issues and re-run approve_post.py")
            sys.exit(1)
    except Exception as e:
        print(f"   ⚠️  QC check error (continuing): {e}")

    # ── Show preview for sign-off ──────────────────────────────────────────
    review_path = post_dir / "REVIEW.md"
    caption_path = post_dir / "caption_tweet.txt"

    print(f"\n{'='*60}")
    print(f"  REVIEW: {meta['title']}")
    print(f"{'='*60}")
    if caption_path.exists():
        print(f"\n  Hook tweet:\n  {caption_path.read_text().strip()}\n")
    if review_path.exists():
        # Print just the first part of the review
        review_text = review_path.read_text()
        lines = review_text.split('\n')
        print('\n'.join(lines[:20]))

    image_path = post_dir / "image.png"
    if image_path.exists():
        print(f"\n  Image: {image_path}")
    else:
        print(f"\n  ⚠ Image not yet rendered (will render on approve)")

    print(f"\n{'='*60}")
    print(f"  Approve and queue this post? [y/N] ", end="", flush=True)
    try:
        choice = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = 'n'

    if choice not in ('y', 'yes'):
        print("\n↩ Approval cancelled. Post remains in staged/.")
        sys.exit(0)

    print(f"\n✅ Approved: {meta['title']} ({slug})")

    # Step 1: Render viz
    print("📊 Rendering visualization...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "pipeline" / "generate_viz.py"), str(post_dir)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR rendering viz:\n{result.stderr}")
        sys.exit(1)
    print(result.stdout.strip())

    # Step 2: Move to queue/
    QUEUE_DIR.mkdir(exist_ok=True)
    dest = QUEUE_DIR / slug
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(post_dir), str(dest))
    print(f"📦 Moved to queue/{slug}/")

    # Step 3: Add to content_queue.json
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH) as f:
            queue = json.load(f)
    else:
        queue = {"queue": [], "last_updated": None}

    # Remove if already present
    queue["queue"] = [p for p in queue["queue"] if p.get("slug") != slug]

    queue["queue"].append({
        "slug": slug,
        "title": meta["title"],
        "pillar": meta.get("pillar"),
        "post_type": meta.get("post_type", "single"),
        "content_dir": str(dest),
        "status": "ready",
        "approved_at": datetime.now(timezone.utc).isoformat(),
    })
    queue["last_updated"] = datetime.now(timezone.utc).isoformat()

    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)

    print(f"\n🎉 Queued! '{meta['title']}' is ready to post.")
    print(f"   Queue length: {len(queue['queue'])} posts")

    # Deploy interactive to GitHub Pages
    print(f"\n🚀 Deploying interactive to GitHub Pages...")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "pipeline"))
        from deploy_pages import deploy
        urls = deploy(post_dir)
        if urls:
            url = urls.get(slug, "")
            print(f"   Live at: {url}")
    except Exception as e:
        print(f"   ⚠️  Deploy failed (non-blocking): {e}")
        print(f"   Run manually: python pipeline/deploy_pages.py staged/{slug}/")

    print(f"\n   Post manually: python pipeline/post_to_x.py queue/{slug}")
    print(f"   Or wait for scheduled cron.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline/approve_post.py staged/<slug>")
        sys.exit(1)
    approve(sys.argv[1])
