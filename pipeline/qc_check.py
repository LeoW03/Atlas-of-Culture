#!/usr/bin/env python3
"""
qc_check.py — Automated quality control for Atlas of Culture posts.

Runs three checks:
  1. Slide QC         — visual: dead zones, text legibility, layout issues
  2. Data accuracy    — fact-check key claims against known ranges + source plausibility
  3. Caption review   — brand voice: peer comparison, no editorializing, specific numbers

Each check returns a score (pass/warn/fail) and findings.
The pipeline calls this automatically; it can also be run manually.

Usage:
  python pipeline/qc_check.py staged/<slug>/
  python pipeline/qc_check.py staged/<slug>/ --fix   # attempt auto-fixes
"""

import argparse
import asyncio
import base64
import json
import re
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
AUTH_PATH = Path.home() / ".openclaw/agents/main/agent/auth-profiles.json"

# Brand voice rules for caption checking
CAPTION_RULES = """
PASS if caption:
- Opens with a specific number pair or arresting fact (not vague claim)
- Compares to a peer/similar country, not just the poorest or most extreme
- Uses third-person observation ("The US pays..." not "We found...")
- Has a closing question or tension, not a call to action
- Is 100-250 words total across all tweets
- No exclamation points on serious topics
- Has specific data source cited

FAIL if caption:
- Uses words: "fascinating", "shocking", "incredible", "amazing", "unbelievable"
- Editorializes about what should be done ("This needs to change", "We must...")
- Takes a political side explicitly
- Uses "we" or "I" as the account voice
- Lacks specific numbers (vague like "much more expensive")
- Leads with the most extreme comparison (US vs poorest country) rather than peer comparison
- Includes exclamation points
- No source cited

WARN if caption:
- Peer comparison present but not the lead
- Numbers present but could be more specific
- Closing line is weak (no tension/question)
"""

SLIDE_VISUAL_RULES = """
Check each 1080x1080px slide for:

FAIL if:
- Dead zone: large empty black area (>15% of canvas with no content)
- Text cropped at edges (labels cut off)
- Text too small to read at 400px (mobile scroll size) — anything under 12px effective
- No visible data (chart/map is all one color or blank)
- Handle (@atlasofculture) or source credit missing
- Background visible through content gaps

WARN if:
- Eyebrow/label text appears faint (below 40% opacity on dark bg)
- Minor spacing inconsistency
- Legend present but hard to read

PASS if:
- Canvas filled intentionally top to bottom
- All text legible at half scale
- Clear visual hierarchy (one thing draws the eye first)
- Handle and source credit present
- Data is visible and differentiated
"""


def get_key():
    with open(AUTH_PATH) as f:
        return json.load(f)["profiles"]["anthropic:claude"]["token"]


def ask_claude(prompt, max_tokens=2000, images=None):
    client = anthropic.Anthropic(api_key=get_key())
    content = []
    if images:
        for img_path in images:
            with open(img_path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": data}
            })
    content.append({"type": "text", "text": prompt})
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}]
    )
    return msg.content[0].text.strip()


# ── 1. Slide QC ───────────────────────────────────────────────────────────────

def check_slides(post_dir: Path) -> dict:
    """Visual QC on rendered PNG slides using vision model."""
    slides = sorted(post_dir.glob("slide-*.png"))
    if not slides:
        return {"status": "skip", "reason": "No slides found", "findings": []}

    findings = []
    overall = "pass"

    for slide_path in slides:
        prompt = f"""You are quality-checking a 1080x1080px data visualization slide for a social media account.

{SLIDE_VISUAL_RULES}

Look at this slide carefully. Return JSON:
{{
  "status": "pass" | "warn" | "fail",
  "issues": ["list of specific problems found"],
  "dead_zone": true | false,
  "text_legible": true | false,
  "handle_present": true | false,
  "source_present": true | false,
  "notes": "brief overall assessment"
}}

Return only valid JSON."""

        raw = ask_claude(prompt, max_tokens=600, images=[str(slide_path)])
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            findings.append({"slide": slide_path.name, "status": "warn", "issues": ["Could not parse QC response"]})
            continue

        result = json.loads(m.group())
        result["slide"] = slide_path.name
        findings.append(result)

        if result.get("status") == "fail":
            overall = "fail"
        elif result.get("status") == "warn" and overall == "pass":
            overall = "warn"

    return {"status": overall, "findings": findings}


# ── 2. Data accuracy ──────────────────────────────────────────────────────────

def check_data_accuracy(post_dir: Path) -> dict:
    """Cross-check key data claims against known ranges and source plausibility."""
    research_path = post_dir / "research.json"
    meta_path = post_dir / "metadata.json"

    if not research_path.exists():
        return {"status": "skip", "reason": "No research.json found", "findings": []}

    with open(research_path) as f:
        research = json.load(f)

    prompt = f"""You are a data accuracy checker for a data journalism account.

Review this research data and flag any issues:

{json.dumps(research, indent=2)}

Check for:
1. **Plausibility** — do the numbers fall within reasonable known ranges for this metric?
2. **Internal consistency** — do the data points relate to each other sensibly?
3. **Source credibility** — are the cited sources real and appropriate for this data?
4. **Outlier sanity** — does the claimed outlier actually stand out from the data?
5. **Unit clarity** — is it clear what unit/year/methodology the data uses?
6. **Suspicious values** — any numbers that seem hallucinated or rounded suspiciously?

Known reference points to check against:
- PISA scores range ~300-590, OECD average ~490
- Teacher salary ratios: typically 60-200% of national average in OECD
- Insulin prices: US ~$98, most wealthy nations $7-15, developing $4-6 (RAND 2021)
- Passport visa-free access: 30-199 countries (Henley Index)
- Press freedom scores: 17-92 (RSF 2024)
- Life expectancy: 50-85 years

Return JSON:
{{
  "status": "pass" | "warn" | "fail",
  "confidence": 0.0-1.0,
  "flagged_claims": [
    {{"claim": "...", "concern": "...", "severity": "fail|warn"}}
  ],
  "source_assessment": "real sources cited | plausible sources | unverifiable | fabricated",
  "recommended_action": "post as-is | verify before posting | do not post",
  "notes": "overall data quality assessment"
}}

Return only valid JSON."""

    raw = ask_claude(prompt, max_tokens=1500)
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        return {"status": "warn", "reason": "Could not parse data check response"}

    result = json.loads(m.group())

    # Hard fail if Claude says don't post
    if result.get("recommended_action") == "do not post":
        result["status"] = "fail"

    return result


# ── 3. Caption review ─────────────────────────────────────────────────────────

def check_captions(post_dir: Path) -> dict:
    """Brand voice + editorial standards check on thread captions."""
    captions_path = post_dir / "captions.txt"
    if not captions_path.exists():
        return {"status": "skip", "reason": "No captions.txt found"}

    captions = captions_path.read_text()

    prompt = f"""You are a brand voice editor for Atlas of Culture, a data journalism account.

{CAPTION_RULES}

Review these thread captions:

{captions}

Return JSON:
{{
  "status": "pass" | "warn" | "fail",
  "issues": ["specific problems found"],
  "forbidden_words": ["any banned words found"],
  "has_peer_comparison": true | false,
  "has_specific_numbers": true | false,
  "has_source_citation": true | false,
  "editorializes": true | false,
  "opening_hook_strength": "strong" | "moderate" | "weak",
  "suggested_rewrites": {{
    "tweet_1": "improved version if needed, else null"
  }},
  "notes": "overall assessment"
}}

Return only valid JSON."""

    raw = ask_claude(prompt, max_tokens=1500)
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        return {"status": "warn", "reason": "Could not parse caption check"}

    return json.loads(m.group())


# ── 4. Sources & caveats check ───────────────────────────────────────────────

def check_sources(post_dir: Path) -> dict:
    """Verify the interactive has a real sources + caveats section."""
    interactives = list(post_dir.glob("*-interactive.html"))
    if not interactives:
        return {"status": "skip", "reason": "No interactive HTML found"}

    html = interactives[0].read_text()

    has_sources_section = 'sources-section' in html or 'Data sources' in html
    has_caveats = 'caveats-list' in html or ('Caveats' in html and '<li>' in html)

    import re
    # Count caveat items
    m = re.search(r'caveats-list.*?</ul>', html, re.DOTALL)
    caveat_count = len(re.findall(r'<li>', m.group())) if m else 0

    # Check for generic/padded caveats
    generic_phrases = [
        'data may be imperfect',
        'results may vary',
        'for informational purposes',
        'should not be relied upon',
    ]
    html_lower = html.lower()
    generic_found = [p for p in generic_phrases if p in html_lower]

    if not has_sources_section:
        return {"status": "fail", "issues": ["No sources section found in interactive HTML"], "caveat_count": 0}
    if not has_caveats:
        return {"status": "fail", "issues": ["No caveats section found in interactive HTML"], "caveat_count": 0}
    if caveat_count == 0:
        return {"status": "warn", "issues": ["Caveats section is empty"], "caveat_count": 0}
    if generic_found:
        return {"status": "warn", "issues": [f"Generic caveat language found: {generic_found}"], "caveat_count": caveat_count}

    return {"status": "pass", "caveat_count": caveat_count, "notes": f"{caveat_count} specific caveat(s) found"}


# ── 5. Duplicate detection ────────────────────────────────────────────────────

def check_duplicates(post_dir: Path) -> dict:
    """Check if this topic overlaps with already-staged or posted content."""
    meta_path = post_dir / "metadata.json"
    if not meta_path.exists():
        return {"status": "skip"}

    with open(meta_path) as f:
        meta = json.load(f)

    current_title = meta.get("title", "")
    current_insight = meta.get("key_insight", "")

    # Collect existing post titles/insights
    existing = []
    for d in [ROOT / "staged", ROOT / "queue"]:
        if not d.exists(): continue
        for p in d.iterdir():
            if p.name == post_dir.name: continue  # skip self
            m_path = p / "metadata.json"
            if m_path.exists():
                with open(m_path) as f:
                    existing.append(json.load(f).get("title", ""))

    posted_path = ROOT / "posted_log.json"
    if posted_path.exists():
        with open(posted_path) as f:
            log = json.load(f)
        existing.extend([e.get("title", "") for e in log.get("posts", [])])

    if not existing:
        return {"status": "pass", "notes": "No existing posts to compare against"}

    prompt = f"""Check if this new post is too similar to existing posts.

New post title: {current_title}
New post key insight: {current_insight}

Existing post titles:
{chr(10).join(f"- {t}" for t in existing if t)}

Return JSON:
{{
  "status": "pass" | "warn" | "fail",
  "overlap_detected": true | false,
  "similar_to": "title of most similar existing post, or null",
  "notes": "brief assessment"
}}

FAIL only if near-identical topic and angle. WARN if related but different angle."""

    raw = ask_claude(prompt, max_tokens=400)
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(m.group()) if m else {"status": "warn", "reason": "Parse failed"}


# ── Main QC runner ────────────────────────────────────────────────────────────

def run_qc(post_dir_str: str, fix: bool = False, verbose: bool = True) -> dict:
    post_dir = Path(post_dir_str)
    if not post_dir.exists():
        print(f"ERROR: {post_dir_str} not found")
        sys.exit(1)

    slug = post_dir.name
    print(f"\n{'='*60}")
    print(f"  QC CHECK: {slug}")
    print(f"{'='*60}\n")

    results = {}
    overall = "pass"

    # Run all checks
    checks = [
        ("slides",    "🖼  Slide visual check",   lambda: check_slides(post_dir)),
        ("data",      "📊 Data accuracy check",   lambda: check_data_accuracy(post_dir)),
        ("captions",  "✍️  Caption review",         lambda: check_captions(post_dir)),
        ("sources",   "📚 Sources & caveats",      lambda: check_sources(post_dir)),
        ("duplicate", "🔍 Duplicate detection",   lambda: check_duplicates(post_dir)),
    ]

    for key, label, fn in checks:
        print(f"{label}...")
        try:
            result = fn()
            results[key] = result
            status = result.get("status", "skip")

            icon = {"pass":"✅","warn":"⚠️ ","fail":"❌","skip":"⏭ "}.get(status, "?")
            print(f"  {icon} {status.upper()}")

            if verbose and status in ("warn", "fail"):
                issues = result.get("issues", result.get("flagged_claims", []))
                if issues:
                    for issue in (issues[:3] if isinstance(issues, list) else [str(issues)]):
                        if isinstance(issue, dict):
                            print(f"     • [{issue.get('severity','?')}] {issue.get('claim','')} — {issue.get('concern','')}")
                        else:
                            print(f"     • {issue}")
                if result.get("notes"):
                    print(f"     → {result['notes']}")
                if result.get("suggested_rewrites", {}).get("tweet_1"):
                    print(f"     💬 Suggested tweet 1: {result['suggested_rewrites']['tweet_1'][:120]}...")

            if status == "fail":
                overall = "fail"
            elif status == "warn" and overall == "pass":
                overall = "warn"

        except Exception as e:
            print(f"  ⚠️  CHECK ERROR: {e}")
            results[key] = {"status": "warn", "error": str(e)}
            if overall == "pass": overall = "warn"

    # Save QC report
    report = {
        "slug": slug,
        "overall": overall,
        "checks": results,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }
    with open(post_dir / "qc_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    icon = {"pass":"✅","warn":"⚠️ ","fail":"❌"}.get(overall,"?")
    print(f"  {icon} OVERALL: {overall.upper()}")
    if overall == "pass":
        print(f"  Post is ready for approval.")
    elif overall == "warn":
        print(f"  Post has warnings — review before approving.")
    else:
        print(f"  Post FAILED QC — do not approve until issues resolved.")
    print(f"{'='*60}\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("post_dir", help="Path to staged/<slug>/")
    parser.add_argument("--fix", action="store_true", help="Attempt auto-fixes")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = run_qc(args.post_dir, fix=args.fix, verbose=not args.quiet)
    sys.exit(0 if report["overall"] != "fail" else 1)
