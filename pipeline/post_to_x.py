#!/usr/bin/env python3
"""
post_to_x.py — Posts an image + caption to X (Twitter) via API v2.

Usage: python post_to_x.py <content_dir>

Supports single posts and threads (multiple slides).
Requires CONFIG.json with valid x credentials (OAuth 1.0a).

metadata.json schema:
  post_type: "single" | "thread"
  slides: ["caption for tweet 1", "caption for tweet 2", ...]  (thread only)
  poll: null | { "options": ["A", "B"], "duration_minutes": 1440 }  (optional)
  alt_text: "description of image"  (optional but recommended)
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import tweepy


CONFIG_PATH = Path(__file__).parent.parent / "CONFIG.json"
QUEUE_PATH = Path(__file__).parent.parent / "content_queue.json"
POSTED_LOG_PATH = Path(__file__).parent.parent / "posted_log.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_client(config):
    x = config["x"]
    client = tweepy.Client(
        consumer_key=x["api_key"],
        consumer_secret=x["api_secret"],
        access_token=x["access_token"],
        access_token_secret=x["access_token_secret"],
        wait_on_rate_limit=True
    )
    return client


def get_api_v1(config):
    """v1.1 API — needed for media upload (v2 media upload requires elevated access)."""
    x = config["x"]
    auth = tweepy.OAuth1UserHandler(
        x["api_key"],
        x["api_secret"],
        x["access_token"],
        x["access_token_secret"]
    )
    return tweepy.API(auth, wait_on_rate_limit=True)


def upload_image(api_v1, image_path: Path, alt_text: str = None) -> str:
    """Upload image via v1.1 media upload, return media_id string."""
    print(f"📤 Uploading image: {image_path.name}")
    media = api_v1.media_upload(filename=str(image_path))
    media_id = str(media.media_id)

    if alt_text:
        api_v1.create_media_metadata(media_id, alt_text)
        print(f"   ✅ Alt text set.")

    print(f"   ✅ Media ID: {media_id}")
    return media_id


def post_tweet(client, text: str, media_ids=None, reply_to_id=None, poll=None) -> str:
    """Post a tweet, return tweet ID."""
    kwargs = {"text": text}

    if media_ids:
        kwargs["media_ids"] = media_ids

    if reply_to_id:
        kwargs["in_reply_to_tweet_id"] = reply_to_id

    if poll:
        kwargs["poll_options"] = poll["options"]
        kwargs["poll_duration_minutes"] = poll.get("duration_minutes", 1440)

    response = client.create_tweet(**kwargs)
    tweet_id = str(response.data["id"])
    print(f"   ✅ Tweet posted: {tweet_id}")
    return tweet_id


def post(content_dir: str):
    config = load_config()
    client = get_client(config)
    api_v1 = get_api_v1(config)

    content_path = Path(content_dir)
    meta_path = content_path / "metadata.json"
    caption_path = content_path / "caption.txt"

    if not meta_path.exists():
        print(f"ERROR: No metadata.json in {content_dir}")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    post_type = meta.get("post_type", "single")
    alt_text = meta.get("alt_text", "")
    poll = meta.get("poll", None)

    # --- SINGLE POST ---
    if post_type == "single":
        image_path = content_path / "image.png"
        if not image_path.exists():
            print(f"ERROR: No image.png in {content_dir}")
            sys.exit(1)

        with open(caption_path) as f:
            caption = f.read().strip()

        # X: keep tweet text under 280 chars
        if len(caption) > 280:
            # Truncate to hook line (first line) for the tweet; full caption goes in reply
            hook = caption.split("\n")[0][:277] + "…"
            full_caption = caption
        else:
            hook = caption
            full_caption = None

        media_id = upload_image(api_v1, image_path, alt_text=alt_text or meta.get("title", ""))
        print(f"📝 Posting tweet...")
        tweet_id = post_tweet(client, hook, media_ids=[media_id], poll=poll)

        # If full caption exists, post as reply thread
        if full_caption:
            time.sleep(2)
            print(f"💬 Adding caption thread reply...")
            post_tweet(client, full_caption[280:].strip(), reply_to_id=tweet_id)

        first_tweet_id = tweet_id

    # --- THREAD POST ---
    elif post_type == "thread":
        slides = meta.get("slides", [])
        if not slides:
            print("ERROR: post_type is 'thread' but no slides defined in metadata.json")
            sys.exit(1)

        # Always append tweet 4 (interactive link) if not already present
        interactive_url = meta.get("interactive_url", "[link]")
        sources = meta.get("sources", [])
        source_line = sources[0] if sources else "Atlas of Culture"
        slug = meta.get("slug", "")

        # Check if last slide is already a link tweet
        last_is_link = slides and (
            "interactive" in slides[-1].lower() or
            "[link]" in slides[-1] or
            "full dataset" in slides[-1].lower()
        )
        if not last_is_link:
            # Build tweet 4 from metadata
            hashtags = meta.get("hashtags", "")
            tweet4 = f"Full dataset, hover any country → {interactive_url}"
            if source_line and source_line != "Atlas of Culture":
                tweet4 += f"\n\nData: {source_line}"
            if hashtags:
                tweet4 += f" | {hashtags}"
            slides = list(slides) + [tweet4]
            print(f"📎 Added interactive link as tweet 4")

        print(f"🧵 Posting thread ({len(slides)} tweets)...")
        first_tweet_id = None
        reply_to = None

        for i, slide_caption in enumerate(slides):
            # Slide images for tweets 1-3; tweet 4 has no image
            image_path = content_path / f"image_{i+1}.png"

            media_ids = None
            if image_path.exists():
                media_id = upload_image(api_v1, image_path,
                                        alt_text=f"{alt_text} ({i+1}/{len(slides)-1})" if alt_text else "")
                media_ids = [media_id]

            # Truncate if needed
            text = slide_caption[:280]
            if len(slide_caption) > 280:
                text = slide_caption[:277] + "…"

            tweet_id = post_tweet(client, text, media_ids=media_ids, reply_to_id=reply_to)

            if first_tweet_id is None:
                first_tweet_id = tweet_id
            reply_to = tweet_id

            if i < len(slides) - 1:
                time.sleep(2)  # small delay between thread tweets

    else:
        print(f"ERROR: Unknown post_type '{post_type}'")
        sys.exit(1)

    print(f"\n✅ Done! First tweet: https://x.com/{config['x']['handle'].lstrip('@')}/status/{first_tweet_id}")

    # --- LOG IT ---
    with open(POSTED_LOG_PATH) as f:
        log = json.load(f)

    if "posts" not in log:
        log["posts"] = []

    log["posts"].append({
        "post_id": first_tweet_id,
        "content_dir": str(content_path),
        "slug": meta.get("slug"),
        "title": meta.get("title"),
        "post_type": post_type,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "likes": 0,
        "bookmarks": 0,
        "retweets": 0,
        "impressions": 0,
        "replies": 0
    })

    with open(POSTED_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)

    # --- UPDATE POSTING SCHEDULE LOG ---
    ROOT = Path(__file__).parent.parent
    schedule_path = ROOT / "POSTING_SCHEDULE.md"
    if schedule_path.exists():
        sched = schedule_path.read_text()
        from datetime import datetime as dt
        posted_date = dt.now().strftime("%a %b %d")
        new_row = f"| {posted_date} | {meta.get('slug')} | {first_tweet_id} | — |"
        sched = sched.replace("| — | — | — | Nothing posted yet |", new_row)
        # If already replaced, append
        if new_row not in sched and "Nothing posted yet" not in sched:
            # Find the log table and append
            marker = "| — | — | — |"
            if marker not in sched:
                last_row_idx = sched.rfind(f"\n| ")
                if last_row_idx > 0:
                    sched = sched[:last_row_idx] + f"\n{new_row}" + sched[last_row_idx:]
        schedule_path.write_text(sched)

    # --- UPDATE QUEUE ---
    with open(QUEUE_PATH) as f:
        queue = json.load(f)

    queue["queue"] = [p for p in queue["queue"] if p.get("content_dir") != str(content_path)]

    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)

    return first_tweet_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python post_to_x.py <content_dir>")
        sys.exit(1)
    post(sys.argv[1])
