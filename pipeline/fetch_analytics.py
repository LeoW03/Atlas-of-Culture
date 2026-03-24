#!/usr/bin/env python3
"""
fetch_analytics.py — Pulls engagement metrics for recent posts via X API v2.
Updates analytics_log.json and posted_log.json with latest numbers.

Usage: python fetch_analytics.py
"""

import json
import tweepy
from pathlib import Path
from datetime import datetime, timezone


CONFIG_PATH = Path(__file__).parent.parent / "CONFIG.json"
POSTED_LOG_PATH = Path(__file__).parent.parent / "posted_log.json"
ANALYTICS_LOG_PATH = Path(__file__).parent.parent / "analytics_log.json"


def fetch():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    x = config["x"]
    if not x["access_token"] or not x["api_key"]:
        print("ERROR: X credentials not configured")
        return

    client = tweepy.Client(
        consumer_key=x["api_key"],
        consumer_secret=x["api_secret"],
        access_token=x["access_token"],
        access_token_secret=x["access_token_secret"],
        wait_on_rate_limit=True
    )

    with open(POSTED_LOG_PATH) as f:
        log = json.load(f)

    updated = []
    for post in log.get("posts", []):
        post_id = post["post_id"]

        try:
            response = client.get_tweet(
                post_id,
                tweet_fields=["public_metrics", "non_public_metrics", "organic_metrics"],
                user_auth=True  # required for non_public_metrics (impressions, bookmarks)
            )
        except Exception as e:
            print(f"WARNING: Could not fetch metrics for {post_id}: {e}")
            updated.append(post)
            continue

        if not response.data:
            print(f"WARNING: No data for tweet {post_id}")
            updated.append(post)
            continue

        pub = response.data.public_metrics or {}
        # non_public_metrics requires Elevated access; fall back gracefully
        non_pub = {}
        organic = {}
        if hasattr(response.data, "non_public_metrics") and response.data.non_public_metrics:
            non_pub = response.data.non_public_metrics
        if hasattr(response.data, "organic_metrics") and response.data.organic_metrics:
            organic = response.data.organic_metrics

        post["likes"] = pub.get("like_count", post.get("likes", 0))
        post["retweets"] = pub.get("retweet_count", post.get("retweets", 0))
        post["replies"] = pub.get("reply_count", post.get("replies", 0))
        post["quotes"] = pub.get("quote_count", post.get("quotes", 0))
        post["bookmarks"] = pub.get("bookmark_count", post.get("bookmarks", 0))
        post["impressions"] = (
            non_pub.get("impression_count")
            or organic.get("impression_count")
            or post.get("impressions", 0)
        )
        post["last_updated"] = datetime.now(timezone.utc).isoformat()

        print(
            f"✅ {post.get('title', post_id)}: "
            f"{post['likes']} likes  "
            f"{post['retweets']} RTs  "
            f"{post['bookmarks']} bookmarks  "
            f"{post['impressions']} impressions"
        )
        updated.append(post)

    log["posts"] = updated
    with open(POSTED_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)

    # Append snapshot to analytics log
    if ANALYTICS_LOG_PATH.exists():
        with open(ANALYTICS_LOG_PATH) as f:
            analytics = json.load(f)
    else:
        analytics = {"posts": []}

    analytics["posts"].append({
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "posts": [
            {k: v for k, v in p.items()
             if k in ["post_id", "slug", "title", "posted_at",
                      "likes", "bookmarks", "retweets", "replies", "impressions"]}
            for p in updated
        ]
    })

    with open(ANALYTICS_LOG_PATH, "w") as f:
        json.dump(analytics, f, indent=2)

    print("✅ Analytics updated.")


if __name__ == "__main__":
    fetch()
