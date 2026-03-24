# Brand Guidelines — [@atlasofculture] (handle TBC)

*Internal document. Living, updated as we learn.*

---

## The Idea

A view from nowhere, looking at everywhere. Data as a lens on the strangeness of human civilization — not to explain it, but to make you feel it. Every post should make someone pause mid-scroll and think *I didn't know that* or *why is it like that?*

Not an infographics account. Not an activism account. Not a politics account, though politics will appear in the data. The stance is **curious, not activist**. The tone is **precise, not sterile**.

The account has no author. It exists. It observes.

---

## How We Make Things

**This is the order. It is not negotiable.**

**1. Find a question worth answering.**
Not a headline. Not a "this would make a good post." A genuine research question: *Why do teachers get paid so differently across wealthy nations? What does a passport actually buy you? Where did insulin pricing go wrong?* The question has to be one we actually want to explore.

**2. Build something explorable.**
The interactive HTML is the real product. A map you can hover. A scatter you can interrogate. A table you can filter. It exists because the data is interesting, not because we need content. If building it doesn't reveal anything surprising, the question wasn't right.

**3. Tell the story you discovered.**
The thread is a trailer. Screenshots of the moments that made us go "wait, really?" Captions that say "I found this" — because we did. The post points at the interactive. The interactive rewards curiosity.

**What this means in practice:**
- Never start with "what would make a good slide"
- Never design slides before building the interactive
- Never write captions before exploring the data
- The story is always something we discovered, not something we planned

*If you're designing slides first, you're doing it backwards.*

---

## Audience

People who:
- Would read *The Economist* but find it too dry
- Follow @informationisbeautiful or @flowingdata but want more cultural texture
- Send links to friends with "wait, look at this"
- Are globally literate and casually curious about everywhere

Age skew: 25-40. Global, English-speaking. Educated without being academic.

---

## Visual Identity

### Color Palette

**Primary palette — restrained, cartographic:**
- Background: `#0F0F0F` (near-black) — default for dark-mode-first
- Alternate background: `#F5F0E8` (aged paper/parchment) — for geographic/historical pieces
- Data ink (primary): `#E8C547` (warm gold) — main data color, used sparingly
- Data ink (secondary): `#4A9EBF` (steel blue)
- Data ink (tertiary): `#C45C3A` (terracotta)
- Data ink (quaternary): `#7DB87D` (muted green)
- Text: `#FFFFFF` on dark / `#1A1A1A` on parchment
- Annotation/secondary text: `#888888`

**Rule:** Never use more than 3 data colors in a single viz. Restraint = sophistication.

### Typography

- **Headlines/Labels:** Space Grotesk (free, Google Fonts) — geometric but warm
- **Data annotations:** IBM Plex Mono — technical precision
- **Body/captions (in-image):** Inter — neutral, universal

All weights used: Regular + Bold only. No italics in data labels.

### Layout Grid

Every post: **1080×1080px** (square, for feed + stories crop flexibility).
- Margin: 60px on all sides
- Title block: top-left always
- Source credit: bottom-right, 11px, muted gray, always present
- Account watermark: bottom-left, small — the handle only, no logo

Carousels: up to 8 slides. First slide is the hook (most dramatic data moment). Last slide is always a contextual "why this matters" or a provocative question.

Reels: 15-30 seconds. Animated versions of static charts — reveals, not full animations. The data builds on screen.

### Visual Personality

- **Clean but not clinical.** Lots of white/dark space. Data shouldn't fight the page.
- **Never chartjunk.** No 3D pie charts. No unnecessary gridlines. No decorative elements that don't encode data.
- **One striking thing per post.** The visual hierarchy leads you to one wow moment, then lets you explore.
- **Maps lean cartographic.** Not Google Maps. Think National Geographic meets Brutalism.

---

## Voice & Tone

### The register

Third-person observation. Never first person. Never "we think" or "this shows us." The data shows. The account points.

**Not:** "This shocking map reveals the TRUTH about pharmaceutical prices 😱"
**Yes:** "The same vial of insulin. Twelve countries. The price difference would buy you a flight."

**Not:** "In this post, we explore..."
**Yes:** Start with the fact. Let it land.

### Caption structure

```
[One-line hook — the most arresting fact or question]

[2-4 lines of context — no jargon, no hedging]

[One closing line — either a question, a tension, or a small provocation]

[Source line: Data: [source] | #tags]
```

**Length:** 100-200 words max. Most people won't read it. The ones who do should feel rewarded, not lectured.

### What we never do

- Editorialize about what *should* be done
- Take political sides (the data can be political; we are not)
- Use the word "fascinating" (lazy)
- Use exclamation points in serious posts
- Explain what the visualization is ("This choropleth shows...") — trust the viewer
- Clickbait ("You won't believe...") — the data is enough

### What we lean into

- Counterintuitive findings
- Geographic surprise (the thing that's different where you don't expect)
- Scale contrast (the thing that's 100x bigger than you thought)
- Historical depth (this was different 50 years ago, here's the delta)
- Human stakes (not abstract — insulin, trees, food, movement, speech)

---

## Content Pillars

**1. Mobility & Access** (20%)
Who can go where. Passports, visas, immigration, movement. The geography of freedom of movement.

**2. Economics at Human Scale** (20%)
What things cost. What people earn. What a dollar buys. The PPP-adjusted reality of daily life.

**3. Language & Culture Flow** (15%)
How languages spread, borrow, die. How culture moves — music, film, food, words.

**4. Environment & Urban Life** (15%)
Cities, trees, concrete, air, water. How humans have shaped the physical world.

**5. Information & Power** (15%)
Censorship, surveillance, press freedom, AI governance. Who controls what you know.

**6. Health & Bodies** (10%)
Drug prices, life expectancy, disease, healthcare access. The body as political terrain.

**7. Time & Democracy** (5%)
Elections, governance, institutional trust. How power is organized and transferred.

---

## Posting Cadence

**Target: 10-12 posts/week** (1-2/day)

| Day | Content Type |
|-----|-------------|
| Mon | Main viz — complex, ambitious |
| Tue | Quick hit — single stat, micro-map |
| Wed | Main viz — carousel (3-6 slides) |
| Thu | Quick hit or Reel (animated) |
| Fri | Main viz — the week's best |
| Sat | Aesthetic-first — beautiful before data-dense |
| Sun | Provocation — question in caption, simpler visual |

**Surge posting:** When a news event makes our existing data relevant, post immediately. This is how you grow — being the account that had the chart *before* everyone needed it.

**Queue rule:** Always maintain 7+ posts in queue. Never scramble.

---

## What the $25/Month Buys

| Tool | Cost | Purpose |
|------|------|---------|
| Google Imagen 3 API | ~$15-20 | Illustrative posts only ($1 Meal type — ~10-15% of content) |
| Proxied data APIs (if needed) | ~$5 | Some datasets behind soft paywalls |
| **Total** | **~$20-25** | |

**Claude** handles everything else: data research, visualization code generation (Python), caption writing, scheduling, comment responses. Already running through OpenClaw.

Free data sources cover ~80% of content: World Bank, WHO, UNESCO, Our World in Data, Freedom House, SIPRI, OpenStreetMap, US Census, Eurostat, UN FAO.

---

## What "Not Obviously AI" Means

- Occasional minor imperfections are fine (a slightly unusual phrasing, a non-standard choice)
- Captions should read like a thoughtful human who cares about data, not like a generated summary
- No emojis in main caption text (one is fine in comments, never in the post itself)
- Source citations are clean and minimal — not over-cited like an AI covering its bases
- If a post gets a comment calling it AI-generated, the response is always a mild, confident non-denial: "Just someone who likes maps." No protest.

---

## Growth Strategy

**Phase 1 (0-1k followers):** Post quality, establish visual identity, find the 2-3 formats that get saves/shares.

**Phase 2 (1k-10k):** Double down on what works. Engage with adjacent accounts (reply genuinely in comments). Repost-bait: posts that make people want to share to their story.

**Phase 3 (10k+):** Collaborations, cross-posting to Twitter/X, possible newsletter.

**The metric that matters most:** Saves. Saves signal "I want to return to this." The algorithm weights them heavily and they indicate genuine value, not just algorithmic virality.

---

*Last updated: 2026-03-21. Review monthly.*
