# Atlas of Culture — Post Production Skill

## The Only Rule That Matters

**Make something cool first. The story will come naturally.**

1. Find a question worth answering through data
2. Build the interactive — make it genuinely explorable
3. Screenshot what you discovered — those are the slides

If you're designing slides before building the interactive, stop. You're doing it backwards.

The thread is a trailer. The interactive is the film.

---

## Pipeline Philosophy

**The interactive is the product. The thread is the trailer.**

Build the real thing first — a rich, explorable webpage where someone can spend 10 minutes going deep. Then extract the best moments from it as screenshots. The thread shows people what they'll find if they click through.

This produces better posts because:
- You discover surprises by actually exploring the data, not by predicting them upfront
- Screenshots of real hover states / filtered views look authentic, not constructed
- The interactive rewards curiosity — saves/shares go up when there's more to find
- The story emerges from the artifact, not the other way around

## Pipeline Flow (always follow this order)

```
1. PITCH         pitch_idea.py
                 → 1-3 ideas with hook, peer angle, source
                 → LEO APPROVES one before anything is built

2. BUILD         generate_interactive.py --from-pitch staged/<slug>/pitch.json
                 → Deep data research
                 → Builds the full interactive HTML (map, charts, table, narrative)
                 → Verifies it renders correctly (Playwright check)
                 → LEO REVIEWS the interactive before screenshots are taken

3. DISCOVER      generate_screenshots.py staged/<slug>/
                 → Playwright explores the interactive automatically:
                     • Renders default state
                     • Hovers key countries/data points
                     • Activates interesting filters
                     • Captures 6-10 candidate screenshots
                 → Picks best 3 as thread slides

4. STORY         generate_thread.py staged/<slug>/
                 → Reads the screenshots + interactive content
                 → Writes thread captions that point at what each screenshot shows
                 → Captions feel like "I found this when I was exploring" not "here is a chart"

5. SIGN-OFF      → LEO APPROVES thread before anything posts

6. POST          post_to_x.py queue/<slug>
                 → Posts 3-4 tweet thread to @atlasofculture
                 → Tweet 4 always = link to interactive
```

**Gate 1 (after pitch): Leo approves idea before building.**
**Gate 2 (after interactive): Leo reviews interactive before slides are made.**
**Gate 3 (after thread): Leo sees preview and says "approve" before anything queues.**
**Gate 4 (posting): Leo has approved. Pipeline posts on schedule.**

Leo never has to think about running a command. The pipeline sends previews; Leo approves or sends notes. Nothing moves without an explicit approval.

This document is the complete production standard for every Atlas of Culture post.
Read it before generating any content. Follow it precisely.

---

## The Core Question

Before touching any code, answer this:

**What is the single most surprising fact in this data — specifically one that would surprise people who already consider themselves well-informed?**

Not "the US has expensive healthcare" — everyone knows that.
YES: "The US pays *8× more than Germany* for the same insulin — not 8× more than Pakistan. 8× more than a comparable wealthy nation."

That inversion — the comparison *within* a peer group — is almost always more surprising than the comparison against the poorest country. Lead with peer comparisons, not extreme outliers.

---

## Anatomy of a Great Atlas Post

### 1. The Hook (headline)
- Leads with a specific number pair, not a vague claim
- Surprises someone who thinks they already know this
- Creates a "wait, really?" reaction
- Examples:
  - ❌ "US insulin is very expensive"
  - ✓ "Germany pays $11. The US pays $98.70."
  - ✓ "A Kenyan passport opens 74 doors. A German passport opens 190."
  - ✓ "In 1960, French was the language of diplomacy. By 2020, English was spoken in 80% of international treaties."

### 2. The Subhead
- One sentence that names *why* this is surprising
- Calls out the peer comparison explicitly
- "Same insulin. Same molecule. **Not the same country.** The US pays more than 8× the price of comparable wealthy nations."

### 3. The Visual (map preferred)
- Maps > bar charts for geographic stories (always default to maps when the data is geographic)
- Color scale: near-black background, blue→teal→amber→gold (cheap→expensive)
- Color must be distinguishable even for the cheap end — use sqrt compression
- Data source: `https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson` (property: `name`)
- SVG viewBox: `"-40 33 984 340"` (crops polar regions, shifts slightly west for Americas)
- Country labels: pill-style background, monospace, gold for outlier
- **The outlier country must be immediately visually obvious** — gold vs everything else being blue

### 4. The Comparison Strip
- After the map: show 5–7 countries, sorted descending
- Lead with the outlier, then peer countries, then cheapest
- Label the multiplier inline: "← 8× the price of Germany"
- Bars fill the available space using `flex: 1` on `.compare-row`

### 5. The Context (footer)
- One sentence, human stakes, no jargon
- Historical fact if compelling: "Insulin's patent was sold for $1..."
- The "combined" stat if true: "pays more than the next 10 countries combined"
- Legible at 12px, muted color — for readers who lean in

---

## Layout System (static 1080×1080 PNG)

```
┌────────────────────────────────────┐
│  eyebrow (mono, 10px, muted gold)  │  ~20px
│  headline (Playfair 900, ~46px)    │  ~105px
│  subhead (Inter 300, 14px)         │  ~40px
│                                    │
│  ──── MAP (natural aspect ratio) ──│  ~330px
│                                    │
│  RETAIL PRICE · STANDARD VIAL     │
│  USA ████████████████████ $98.70   │  ~180px
│  Japan ████ $14.40                 │
│  Germany ███ $11.00                │
│  ...                               │
│                                    │
│  Context text · Legend · Source    │  ~60px
└────────────────────────────────────┘
```

**Critical CSS rules:**
- `body`: 1080×1080px exactly, overflow:hidden
- Canvas: `flex-direction:column`, no fixed heights
- Map zone: `flex-shrink:0`, width:100%, SVG height:auto
- Compare zone: `flex:1`, rows use `flex:1` to fill vertically
- Footer: `flex-shrink:0`
- Result: map takes natural height, compare fills remaining space

**Never use fixed `grid-template-rows` with pixel values** — content varies per post and will leave dead zones.

---

## Color System

```js
// Sqrt-compressed color scale (cheap→expensive)
// Sqrt gives visual range to the cheap end where most countries cluster
const STOPS = [
  [0.00, [28,55,115]],   // deep blue   ($4)
  [0.18, [38,95,135]],   // steel blue  (~$6)
  [0.35, [52,125,115]],  // teal        (~$9)
  [0.50, [85,125,75]],   // olive       (~$13)
  [0.65, [145,115,38]],  // warm        (~$20)
  [0.80, [192,138,28]],  // amber       (~$40)
  [0.92, [218,175,48]],  // pale gold   (~$70)
  [1.00, [232,197,71]],  // #e8c547     (max)
];

function getColor(v, min, max) {
  const t = Math.sqrt(Math.max(0, Math.min(1, (v - min) / (max - min))));
  // ... interpolate between stops
}
```

**Background**: `#07070c` (near-black, not pure black)
**No-data countries**: `#111126` (visible but clearly different)
**Grain overlay**: `body::before`, SVG fractalNoise, `opacity: 0.035`

---

## Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Headline | Playfair Display | 900 | 44–54px |
| Headline emphasis | Playfair Display | 900 italic | same |
| Eyebrow / labels | IBM Plex Mono | 500 | 9–11px + letter-spacing |
| Subhead / body | Inter | 300–400 | 13–15px |
| Data values | IBM Plex Mono | 400 | 10–12px |

Always load via Google Fonts CDN. Render waits for `networkidle` + 1.5s buffer.

---

## GeoJSON

**Source (use this exact URL):**
```
https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson
```
Property: `name`. 258 features. Works with Playwright headless.

**Name map (required for matching):**
```js
const NAME_MAP = {
  "United States of America": "United States",
  "Türkiye": "Turkey",
  "Czech Republic": "Czechia",
  "S. Korea": "South Korea",
  "Dem. Rep. Congo": "Democratic Republic of the Congo",
  "N. Macedonia": "North Macedonia",
  "eSwatini": "Eswatini",
  "Dominican Rep.": "Dominican Republic",
  "Bosnia and Herz.": "Bosnia and Herzegovina",
  "Somaliland": "Somalia",
  "N. Cyprus": "Cyprus",
};
```

**Equirectangular projection:**
```js
const W=944, H=490;
function proj(lon,lat) { return [((lon+180)/360)*W, ((90-lat)/180)*H]; }
```

**Anti-meridian handling (required):**
```js
function ring2path(ring) {
  const T=W*0.4, segs=[[]];
  ring.forEach(([lo,la])=>{
    const[x,y]=proj(lo,la);
    const s=segs[segs.length-1];
    if(s.length>0&&Math.abs(x-s[s.length-1][0])>T) segs.push([[x,y]]);
    else s.push([x,y]);
  });
  return segs.filter(s=>s.length>1)
    .map(s=>s.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`).join('')+'Z')
    .join(' ');
}
```

**Render order:** Sort features cheap→expensive so the outlier renders on top.

---

## Rendering Pipeline

```python
# generate_viz.py calls this
async def render_html(html_content, output_path, w=1080, h=1080):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": w, "height": h})
        await page.goto(f"file://{tmp_html_path}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1.5)  # Google Fonts buffer
        await page.screenshot(path=output_path, full_page=False,
                              clip={"x":0,"y":0,"width":w,"height":h})
```

---

## The Companion HTML

**Every post that can support it should have a companion interactive HTML file.**

The companion:
- Is a full responsive webpage, not a screenshot
- Includes the map with hover tooltips (country name + price + "USA pays N× more")
- Includes a full sortable/filterable data table
- Includes the narrative: why this happens, what's surprising, historical context
- Has a clean dark editorial design (not an app, not a dashboard)
- Is self-contained (no build step, single HTML file)
- Named: `<slug>-interactive.html`

The X post shows the static image. The post caption says:
> "Full interactive map at [link] — hover any country, filter by region."

This is the two-step hook: image stops the scroll, interactive rewards curiosity.

**Companion file structure:**
```
Hero section (headline, stats pills)
Map section (interactive SVG with tooltip)
Table section (all countries, filterable by region)
Narrative section (why this happens, historical context, what's surprising)
Footer (handle, source)
```

---

## Thread Structure (always 4 tweets)

Every thread is exactly 4 tweets. No exceptions.

```
Tweet 1 (with slide 1 image): The hook — stops the scroll
Tweet 2 (with slide 2 image): The depth — one more surprising fact
Tweet 3 (with slide 3 image): The why — the mechanism, not a summary
Tweet 4 (no image): The interactive link
```

**Tweet 4 is mandatory.** Without it, the interactive — the actual product — is invisible.
Tweet 4 format:
> Full interactive: hover any country, explore the full dataset → [link]
> 
> Data: [Source] [Year] | #tag1 #tag2

---

## Copy Rules

### The voice
The account has no author. It observes. It points. It does not explain what you're looking at — it shows you something and trusts you to understand it.

**Not a journalist summarising.** Not a teacher explaining. Not an activist making a point.
More like: a very well-read person who found something and says "look at this."

### What kills the voice
- **Explaining rather than showing.** "This shows us that..." "The data reveals..." — no. Just say the thing.
- **Profundity that hasn't been earned.** "Status is the actual variable." Sounds deep, means nothing without the data behind it. Let the data be the profound thing.
- **Generic observations.** "More time in class doesn't mean better outcomes" — everyone assumes this already. "Poland has 635 hours and outscores the US at 1,016" — now you've said something.
- **Vague closers.** "The data reflects that signal back." What does that mean? Nothing. Cut it.
- **#dataviz as a hashtag.** It's a filing system for data nerds, not a hook for curious humans.

### What works
- **The specific unexpected number.** Not "low pay" — "64%." Not "better outcomes" — "PISA 516 vs 497."
- **The comparison that shouldn't be true.** Poland outscores the US. Rwanda leads the world in women in parliament. Switzerland has the lowest turnout and the highest democratic satisfaction.
- **The human-scale fact.** "9 million Americans ration their insulin." "Finland rejects 9 in 10 teacher applicants." These land because they're concrete.
- **The question left open.** End on something unresolved. Not a rhetorical flourish — an actual question the data raises but doesn't answer.

### Tweet-by-tweet craft

**Tweet 1 — the hook:**
One or two short sentences. A number and its contrast. Nothing more.
- ✅ "Luxembourg pays teachers 198% of the average salary. The US pays 64%."
- ✅ "Finland: 593 hours in school per year. The US: 1,016. Finland scores higher."
- ❌ "That gap — not just the number, but what it signals about how a society values the profession — shows up directly in outcomes." (explaining the hook instead of letting it land)

**Tweet 2 — the surprise in the pattern:**
Don't summarise the scatter. Find the one data point that breaks what people would expect and name it specifically.
- ✅ "Poland: 635 hours, PISA 516. The US: 1,016 hours, PISA 497. More hours, worse outcomes."
- ✅ "Singapore tops the world with PISA 569. It also pays teachers from the top third of graduates."
- ❌ "The correlation between teacher pay and PISA scores is real. But the outliers are more interesting." (setting up instead of delivering)

**Tweet 3 — the mechanism:**
One concrete thing that explains *why* the pattern exists. Not a summary of everything. The single most illuminating structural fact.
- ✅ "Finland accepts fewer than 10% of teacher training applicants. Teaching is harder to get into than medicine."
- ✅ "Insulin's patent sold for $1 in 1921. The inventor refused to profit from something people need to survive."
- ❌ "The US accepts the majority. The signal sent: this is not a prestige career. The data reflects that signal back." (three ideas collapsed together, the last one is empty)

**Tweet 4 — the link:**
Short. Functional. Points to the interactive.
> Full dataset, hover any country → [link]
> Data: OECD EAG 2023 · PISA 2022

### Hashtags
2 maximum. Specific, not generic.
- ✅ `#teacherpay #education`
- ✅ `#insulin #healthpolicy`
- ❌ `#dataviz` (filing system, not a hook)
- ❌ `#teachers #education #dataviz` (three hashtags looks spammy)

### What never appears
- "This is outrageous / shocking / surprising"
- "We" or "I"
- "The data shows us that..."
- "This chart/map/thread explores..."
- Exclamation points on serious topics
- "Fascinating"
- Telling people to retweet or share

---

## Rewrite test
Before finalising any caption, ask: **would a curious, well-read person forward this to a friend?**
Not share it on their feed — forward it privately with "look at this."
If the answer is yes, the copy is working. If it reads like a content account, it isn't.

---

## Slide 1 Map: Label Placement Rules
- Never put country labels on SVG countries that are near the left edge under `slice` mode (US, Canada, Mexico will always crop)
- Instead: mention those countries in the **header text** (headline or subhead), and only put SVG labels on countries in the safe central zone (Europe, Asia, Middle East)
- Luxembourg, Germany, Japan, South Korea — safe to label on map
- United States, Canada — label in header only

## Scatter Plot: Sizing
- SVG `viewBox` height must be ≥ 700 for a full 1080px canvas with header (~250px) and footer (~80px)
- Use `preserveAspectRatio="xMidYMid meet"` and set `width:100%; height:100%` on the SVG inside a `flex:1` container
- PAD = `{ l:70, r:30, t:20, b:60 }`, CW = 800, CH = viewBox_height - PAD.t - PAD.b

## Anti-Patterns

| ❌ Never | ✓ Instead |
|---------|-----------|
| matplotlib for final output | HTML + Playwright |
| Fixed grid-template-rows px values | flex with flex:1 on middle zone |
| US vs poorest country as the headline | US vs comparable wealthy peers |
| Vague headline ("US insulin is expensive") | Specific numbers ("Germany $11. US $98.70") |
| More than 8 comparison bars | 5–7 max |
| All countries as flat solid colors | sqrt-compressed color scale |
| Dead zones in the layout | Every pixel intentional |
| Generic GeoJSON CDN that 404s | `raw.githubusercontent.com/datasets/geo-countries` |
| Dark colors on dark background | Ensure cheap countries are `rgb(28,55,115)` or brighter |
| Explain the chart ("This map shows...") | Trust the viewer, title does the work |

---

## Sources & Caveats (required in every interactive)

Every interactive HTML must end with a sources + caveats section **before** the footer.

**Sources:** Each source as a linked item — name, URL, one sentence on what it covers and the data year.

**Caveats:** An honest list of what a careful reader should know about this specific data:
- Data age and whether it's still current
- What the metric does and doesn't capture
- Countries or regions where data is estimated rather than measured
- Methodological differences between datasets being compared on the same chart
- Known gaps (e.g. China PISA being provinces-only, not national)

**Rules:**
- Write only the caveats that actually matter. Two real ones beats five generic ones.
- "Data may be imperfect" is not a caveat. "This data is from 2018 and X has changed materially since" is.
- If you're putting two structurally different metrics on a scatter plot, that must be caveated.
- Flag countries with compulsory voting, non-representative sampling, or authoritarian survey contexts.

**CSS structure:**
```css
.sources-section { padding: 52px 64px 72px; max-width: 760px; margin: 0 auto; border-top: 1px solid rgba(255,255,255,0.06); }
.source-item { margin-bottom: 16px; padding-left: 16px; border-left: 2px solid rgba(232,197,71,0.25); }
.source-name a { color: rgba(232,197,71,0.7); text-decoration: none; }
.source-desc { font-size: 13px; color: rgba(255,255,255,0.38); line-height: 1.6; }
.caveats-list { list-style: none; padding: 0; }
.caveats-list li { font-size: 13.5px; color: rgba(255,255,255,0.38); line-height: 1.65; padding: 10px 0 10px 20px; border-bottom: 1px solid rgba(255,255,255,0.04); position: relative; }
.caveats-list li::before { content: '—'; position: absolute; left: 0; color: rgba(232,197,71,0.3); }
```

## Checklist Before Staging

- [ ] Headline uses specific number pair, peer comparison
- [ ] Map renders with visible color range (not all-dark)
- [ ] US or outlier renders in gold, everything else in blue
- [ ] No dead zones (fill canvas top to bottom)
- [ ] Grain overlay + near-black background
- [ ] Google Fonts: Playfair + IBM Plex Mono + Inter
- [ ] Footer: handle + source credit
- [ ] Bars fill their zone (flex:1 on rows)
- [ ] Caption follows structure, no editorializing
- [ ] Companion HTML staged alongside PNG
- [ ] Sources + caveats section present with real, specific content
