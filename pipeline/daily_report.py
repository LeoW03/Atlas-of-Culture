#!/usr/bin/env python3
"""
daily_report.py — Compiles daily analytics and sends a Telegram report.

Usage: python daily_report.py
"""

import json
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta


CONFIG_PATH = Path(__file__).parent.parent / "CONFIG.json"
POSTED_LOG_PATH = Path(__file__).parent.parent / "posted_log.json"
QUEUE_PATH = Path(__file__).parent.parent / "content_queue.json"


def send_telegram(bot_token: str, chat_id: str, message: str):
    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    )
    if resp.status_code != 200:
        print(f"ERROR sending Telegram: {resp.json()}")
    else:
        print("✅ Telegram report sent.")


def build_report() -> str:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    with open(POSTED_LOG_PATH) as f:
        log = json.load(f)
    with open(QUEUE_PATH) as f:
        queue = json.load(f)

    posts = log.get("posts", [])
    queued = queue.get("queue", [])
    now = datetime.now(timezone.utc)
    today = now.date()

    # Posts from today
    todays_posts = [
        p for p in posts
        if p.get("posted_at") and 
        datetime.fromisoformat(p["posted_at"]).date() == today
    ]

    # Best performer this week
    week_ago = now - timedelta(days=7)
    weekly_posts = [
        p for p in posts
        if p.get("posted_at") and
        datetime.fromisoformat(p["posted_at"]) >= week_ago
    ]
    best = max(weekly_posts, key=lambda p: p.get("saves", 0)) if weekly_posts else None

    # Build message
    handle = config["x"].get("handle", "@atlasofculture")
    date_str = now.strftime("%a %b %-d")

    lines = [f"<b>📊 Atlas Daily — {date_str}</b>\n"]

    if todays_posts:
        for p in todays_posts:
            lines.append(f"<b>Posted:</b> {p.get('title', 'Untitled')}")
            lines.append(f"❤️ {p.get('likes', 0):,} likes  📌 {p.get('saves', 0):,} saves  👁 {p.get('reach', 0):,} reach\n")
    else:
        lines.append("No posts today (queue may be empty or posting pending).\n")

    lines.append(f"<b>Queue:</b> {len(queued)} posts ready")

    if best:
        lines.append(f"<b>Best this week:</b> {best.get('title', 'Untitled')} ({best.get('saves', 0):,} saves)")

    if len(queued) < 5:
        lines.append(f"\n⚠️ <b>Queue low ({len(queued)} posts).</b> Refilling soon.")

    lines.append(f"\n<i>{handle}</i>")

    return "\n".join(lines)


def run():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    tg = config.get("telegram", {})
    bot_token = tg.get("bot_token")
    chat_id = tg.get("chat_id")

    if not bot_token or not chat_id:
        print("ERROR: Telegram credentials not configured in CONFIG.json")
        return

    report = build_report()
    print(report)
    send_telegram(bot_token, chat_id, report)


if __name__ == "__main__":
    run()
