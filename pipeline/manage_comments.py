#!/usr/bin/env python3
"""
manage_comments.py — Fetches replies to recent posts and responds to substantive ones.

Strategy:
- Ignore: emoji-only, short (<15 chars), obvious spam, bots
- Respond to: questions, thoughtful observations, corrections, genuine debate
- Never: defend being AI, argue politics, engage trolls

Usage: python manage_comments.py
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import anthropic
import tweepy

AUTH_PATH = Path.home() / ".openclaw/agents/main/agent/auth-profiles.json"


def get_anthropic_key() -> str:
    with open(AUTH_PATH) as f:
        d = json.load(f)
    return d["profiles"]["anthropic:claude"]["token"]

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "CONFIG.json"
POSTED_LOG_PATH = ROOT / "posted_log.json"
COMMENTS_LOG_PATH = ROOT / "comments_log.json"

SPAM_PATTERNS = [
    "follow me", "follow back", "check my", "check out my",
    "dm me", "link in bio", "buy ", "sale ", "discount",
    "giveaway", "onlyfans", "crypto", "nft", "click here",
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_client(config):
    x = config["x"]
    return tweepy.Client(
        consumer_key=x["api_key"],
        consumer_secret=x["api_secret"],
        access_token=x["access_token"],
        access_token_secret=x["access_token_secret"],
        wait_on_rate_limit=True
    )


def should_respond(text: str) -> bool:
    t = text.strip().lower()
    if len(t) < 15:
        return False
    # Skip emoji-only (rough check: mostly non-ASCII, very short)
    non_ascii = sum(1 for c in t if ord(c) > 127)
    if non_ascii > len(t) * 0.6:
        return False
    if any(p in t for p in SPAM_PATTERNS):
        return False
    # Respond to questions or substantive comments
    if "?" in text or len(text) > 60:
        return True
    return False


def generate_response(post_title: str, post_caption: str, comment: str) -> str:
    prompt = f"""You run an anonymous X (Twitter) account that posts data visualizations about global culture and civilization.
Your voice: curious, precise, not preachy. You never reveal you are AI. You respond like a thoughtful person who loves data.

Post title: {post_title}
Post caption excerpt: {post_caption[:300]}
Reply to respond to: {comment}

Write a short reply (1-3 sentences max).
- Sound human and genuine
- Add a small insight or data point if relevant
- No exclamation points on serious topics
- Never start with "Great question!" or similar filler
- If it is a correction and they are right, acknowledge it briefly
- If it is a question you cannot fully answer, be honest and curious
- Do NOT mention AI, algorithms, or automation in any way
- Never take a political side

Reply only, no quotes, no explanation:"""

    client = anthropic.Anthropic(api_key=get_anthropic_key())
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()[:280]


def run():
    config = load_config()
    x = config["x"]

    if not x.get("access_token") or not x.get("api_key"):
        print("ERROR: X credentials not configured")
        return

    client = get_client(config)

    # Load or init comments log
    if COMMENTS_LOG_PATH.exists():
        with open(COMMENTS_LOG_PATH) as f:
            comments_log = json.load(f)
    else:
        comments_log = {"responded_ids": [], "skipped_ids": []}

    responded_ids = set(comments_log.get("responded_ids", []))
    skipped_ids = set(comments_log.get("skipped_ids", []))

    if not POSTED_LOG_PATH.exists():
        print("No posts logged yet.")
        return

    with open(POSTED_LOG_PATH) as f:
        log = json.load(f)

    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    recent_posts = [
        p for p in log.get("posts", [])
        if p.get("posted_at") and datetime.fromisoformat(p["posted_at"]) >= cutoff
    ]

    if not recent_posts:
        print("No recent posts to check.")
        return

    new_responses = 0

    for post in recent_posts:
        post_id = post["post_id"]
        print(f"\n🔍 Checking replies to: {post.get('title', post_id)}")

        try:
            # Search for recent replies to this tweet
            query = f"in_reply_to_tweet_id:{post_id} -is:retweet"
            results = client.search_recent_tweets(
                query=query,
                tweet_fields=["author_id", "text", "created_at"],
                max_results=20
            )
        except Exception as e:
            print(f"   WARNING: Could not fetch replies: {e}")
            continue

        if not results.data:
            print(f"   No replies found.")
            continue

        for tweet in results.data:
            cid = str(tweet.id)
            text = tweet.text or ""

            if cid in responded_ids or cid in skipped_ids:
                continue

            if not should_respond(text):
                skipped_ids.add(cid)
                continue

            print(f"   💬 Responding to: {text[:80]}...")

            # Get caption for context
            caption = ""
            content_dir = post.get("content_dir", "")
            caption_path = Path(content_dir) / "caption.txt"
            if caption_path.exists():
                with open(caption_path) as f:
                    caption = f.read().strip()[:300]

            response = generate_response(
                post.get("title", ""),
                caption,
                text
            )

            if not response:
                print(f"      ⚠️  Could not generate response, skipping")
                skipped_ids.add(cid)
                continue

            try:
                client.create_tweet(
                    text=response,
                    in_reply_to_tweet_id=cid
                )
                print(f"      ✅ Replied: {response[:80]}...")
                responded_ids.add(cid)
                new_responses += 1
            except Exception as e:
                print(f"      ❌ Reply failed: {e}")
                skipped_ids.add(cid)

    # Save log
    comments_log["responded_ids"] = list(responded_ids)
    comments_log["skipped_ids"] = list(skipped_ids)
    comments_log["last_run"] = datetime.now(timezone.utc).isoformat()

    with open(COMMENTS_LOG_PATH, "w") as f:
        json.dump(comments_log, f, indent=2)

    print(f"\n✅ Done. {new_responses} new replies sent.")


if __name__ == "__main__":
    run()
