#!/usr/bin/env python3
"""
weekly_insights.py — Analyses post performance and generates a weekly insights report.

Usage: python pipeline/weekly_insights.py

Outputs: reports/YYYY-MM-DD_insights.md
"""

import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
POSTED_LOG_PATH = ROOT / "posted_log.json"
ANALYTICS_LOG_PATH = ROOT / "analytics_log.json"
REPORTS_DIR = ROOT / "reports"


def avg(values):
    return sum(values) / len(values) if values else 0


def generate_report():
    REPORTS_DIR.mkdir(exist_ok=True)

    if not POSTED_LOG_PATH.exists():
        print("No posted_log.json found. Nothing to analyse yet.")
        return

    with open(POSTED_LOG_PATH) as f:
        log = json.load(f)

    posts = log.get("posts", [])
    if not posts:
        print("No posts logged yet.")
        return

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Enrich with parsed dates
    for p in posts:
        try:
            p["_dt"] = datetime.fromisoformat(p["posted_at"])
        except Exception:
            p["_dt"] = None

    valid = [p for p in posts if p.get("_dt")]

    # ── Top 5 by bookmarks ────────────────────────────────────────────────────
    top5 = sorted(valid, key=lambda p: p.get("bookmarks", 0), reverse=True)[:5]

    # ── By pillar ────────────────────────────────────────────────────────────
    by_pillar = defaultdict(list)
    for p in valid:
        pillar = p.get("pillar", "unknown")
        by_pillar[pillar].append(p)

    pillar_stats = {}
    for pillar, ps in by_pillar.items():
        pillar_stats[pillar] = {
            "count": len(ps),
            "avg_bookmarks": avg([p.get("bookmarks", 0) for p in ps]),
            "avg_impressions": avg([p.get("impressions", 0) for p in ps]),
        }

    # ── By post type ─────────────────────────────────────────────────────────
    by_type = defaultdict(list)
    for p in valid:
        by_type[p.get("post_type", "single")].append(p)

    type_stats = {}
    for pt, ps in by_type.items():
        type_stats[pt] = {
            "count": len(ps),
            "avg_bookmarks": avg([p.get("bookmarks", 0) for p in ps]),
            "avg_impressions": avg([p.get("impressions", 0) for p in ps]),
        }

    # ── By day of week ────────────────────────────────────────────────────────
    by_day = defaultdict(list)
    for p in valid:
        day = p["_dt"].strftime("%A")
        by_day[day].append(p)

    day_stats = {
        day: avg([p.get("bookmarks", 0) for p in ps])
        for day, ps in by_day.items()
    }
    best_days = sorted(day_stats.items(), key=lambda x: x[1], reverse=True)

    # ── By hour ───────────────────────────────────────────────────────────────
    by_hour = defaultdict(list)
    for p in valid:
        hour = p["_dt"].hour
        by_hour[hour].append(p)

    hour_stats = {
        hour: avg([p.get("bookmarks", 0) for p in ps])
        for hour, ps in by_hour.items()
    }
    best_hours = sorted(hour_stats.items(), key=lambda x: x[1], reverse=True)[:3]

    # ── Bookmark rate trend (4 weeks) ─────────────────────────────────────────
    weeks = []
    for w in range(4):
        week_start = now - timedelta(weeks=w+1)
        week_end = now - timedelta(weeks=w)
        week_posts = [p for p in valid if week_start <= p["_dt"] < week_end]
        if week_posts:
            weeks.append({
                "label": f"Week -{w+1}",
                "count": len(week_posts),
                "avg_bookmarks": avg([p.get("bookmarks", 0) for p in week_posts]),
            })

    # ── Recommendations ───────────────────────────────────────────────────────
    recs = []

    # Best pillar
    if pillar_stats:
        best_pillar = max(pillar_stats.items(), key=lambda x: x[1]["avg_bookmarks"])
        recs.append(f"**More {best_pillar[0]}** — averaging {best_pillar[1]['avg_bookmarks']:.1f} bookmarks/post, highest of any pillar")

    # Best format
    if len(type_stats) > 1:
        best_type = max(type_stats.items(), key=lambda x: x[1]["avg_bookmarks"])
        recs.append(f"**More {best_type[0]} posts** — outperforming other formats with {best_type[1]['avg_bookmarks']:.1f} avg bookmarks")

    # Best day
    if best_days:
        recs.append(f"**Post on {best_days[0][0]}s** — best average bookmark rate ({best_days[0][1]:.1f}/post)")

    if not recs:
        recs = ["Not enough data yet — keep posting and check back next week."]

    # ── Build report ──────────────────────────────────────────────────────────
    lines = [
        f"# Atlas of Culture — Weekly Insights",
        f"*Generated {today} · {len(valid)} total posts*\n",
        "---\n",
        "## 🔖 Top 5 Posts (by bookmarks)\n",
    ]

    for i, p in enumerate(top5, 1):
        lines.append(f"{i}. **{p.get('title', p['post_id'])}**")
        lines.append(f"   {p.get('bookmarks', 0)} bookmarks · {p.get('impressions', 0):,} impressions · {p.get('likes', 0)} likes")
        lines.append(f"   Posted: {p['_dt'].strftime('%b %-d')} | Pillar: {p.get('pillar', '—')} | Type: {p.get('post_type', '—')}\n")

    lines += ["\n## 📊 Performance by Pillar\n"]
    for pillar, stats in sorted(pillar_stats.items(), key=lambda x: x[1]["avg_bookmarks"], reverse=True):
        lines.append(f"- **{pillar}** ({stats['count']} posts) — avg {stats['avg_bookmarks']:.1f} bookmarks, {stats['avg_impressions']:,.0f} impressions")

    lines += ["\n## 📝 Performance by Format\n"]
    for pt, stats in sorted(type_stats.items(), key=lambda x: x[1]["avg_bookmarks"], reverse=True):
        lines.append(f"- **{pt}** ({stats['count']} posts) — avg {stats['avg_bookmarks']:.1f} bookmarks, {stats['avg_impressions']:,.0f} impressions")

    lines += ["\n## 📅 Best Days to Post\n"]
    for day, score in best_days[:4]:
        count = len(by_day[day])
        lines.append(f"- **{day}** — avg {score:.1f} bookmarks ({count} posts)")

    if best_hours:
        lines += ["\n## ⏰ Best Posting Hours (UTC)\n"]
        for hour, score in best_hours:
            lines.append(f"- **{hour:02d}:00 UTC** — avg {score:.1f} bookmarks")

    if weeks:
        lines += ["\n## 📈 Bookmark Trend (last 4 weeks)\n"]
        for w in reversed(weeks):
            bar = "█" * max(1, int(w["avg_bookmarks"]))
            lines.append(f"- {w['label']}: {w['avg_bookmarks']:.1f} avg {bar} ({w['count']} posts)")

    lines += ["\n## 💡 What to Make More Of\n"]
    for rec in recs:
        lines.append(f"- {rec}")

    lines.append(f"\n---\n*Next report: run `python pipeline/weekly_insights.py` after more posts*")

    report = "\n".join(lines)

    report_path = REPORTS_DIR / f"{today}_insights.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(report)
    print(f"\n✅ Report saved to {report_path}")


if __name__ == "__main__":
    generate_report()
