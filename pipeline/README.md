# Atlas of Culture — Pipeline

## Philosophy
**The interactive is the product. The thread is the trailer.**

Build the real thing first. Discover the story by exploring it. Screenshot the moments that make you go "wait, really?" Those become the thread.

---

## Full pipeline

```bash
# 0. Check backlog health first
python pipeline/manage_backlog.py audit
# → shows queue depth, idea bank, any warnings

# 1. Pitch an idea — get Leo's approval first
python pipeline/pitch_idea.py --count 3
# → pick one, it saves to staged/<slug>/pitch.json

# 2. Build the interactive page
python pipeline/generate_interactive.py --from-pitch staged/<slug>/pitch.json
# → builds staged/<slug>/<slug>-interactive.html
# → verifies it renders (Playwright)
# → LEO REVIEWS the interactive

# 3. Generate screenshots + thread slides
python pipeline/generate_screenshots.py staged/<slug>/
# → Playwright explores the page, captures key moments
# → Claude designs 3 slides from those moments
# → renders slide-1/2/3.png + writes captions.txt

# 4. Automated QC (runs automatically inside approve)
python pipeline/qc_check.py staged/<slug>/
# → checks: slide visuals, data accuracy, caption voice, duplicate detection
# → FAIL blocks approval. WARN flags for human review.

# 4b. Request approval (sends preview to Leo)
python pipeline/request_approval.py staged/<slug>/
# → Sends slide images + captions to Leo for review
# → Leo replies "approve" or sends notes
# → Nothing queues until Leo approves

# 5. Approve (Leo runs this, or approves via chat)
python pipeline/approve_post.py staged/<slug>/
# → QC runs automatically, then asks y/N
# → shows preview, asks y/N
# → moves to queue/

# 6. Post
python pipeline/post_to_x.py queue/<slug>/
```

## Key files

| File | Purpose |
|------|---------|
| `pitch_idea.py` | Generate + pitch ideas. Gate 1. |
| `generate_interactive.py` | Build the full interactive HTML. The real product. |
| `generate_screenshots.py` | Explore interactive, capture moments, render slides + captions. |
| `approve_post.py` | Preview + confirmation gate before queue. |
| `post_to_x.py` | Post thread to @atlasofculture. |
| `skills/ATLAS_POST_SKILL.md` | Full production standard. Read before building anything. |
| `generate_viz.py` | Render arbitrary HTML → PNG (used by generate_screenshots). |
| `qc_check.py` | Automated QC: slide visuals, data accuracy, captions, duplicates. Runs inside approve_post. |
| `manage_backlog.py` | Track queue depth, idea bank, replenish ideas. Run on heartbeat. |

## What "good" looks like

**Interactive page:**
- Hero with specific number pair (peer comparison, not extremes)
- Choropleth map with hover tooltips
- Secondary chart (scatter, bars) with hover
- Filterable data table (region filters)
- Narrative: why it happens, outliers, historical context
- All 258 countries on map, no console errors

**Thread slides:**
- Slide 1: Map + hook headline. Numbers in the title.
- Slide 2: Chart showing pattern/correlation. Labeled outliers.
- Slide 3: Text-forward. 3 facts that explain the why.
- Tweet 4: Link to interactive. "Hover any country. Explore all X countries."

**Captions:**
- Lead with specific numbers, not vague claims
- Peer comparison ("US pays 8× more than Germany"), not extreme ("US vs Pakistan")
- Third person, no editorializing, no "fascinating"
- Tweet 4 always drives to the interactive
