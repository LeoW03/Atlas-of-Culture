# Where Teachers Are Paid Like Professionals
**Pillar:** education | **Type:** thread (3 slides + companion) | **Slug:** teacher-pay-outcomes
**Status:** AWAITING SIGN-OFF

---

## The angle
The surprise isn't that some countries pay teachers poorly — it's the *peer comparison*. Luxembourg pays twice the national average. The US pays 64% of it. The follow-up surprise: money alone doesn't explain outcomes. Status does. Finland and Singapore have cracked it. The US hasn't.

## Slides
- **slide-1.png** — World map, terracotta (underpaid) → gold (well-paid). Luxembourg labeled on map. US in the header.
- **slide-2.png** — Scatter: teacher pay ratio (x) vs PISA composite (y). Trend line, labeled outliers. Singapore outlier high, US below trend for wealth.
- **slide-3.png** — Three facts: Finland 10:1 selectivity, Singapore 569 PISA, US 64% and what it signals.

## Companion
`teacher-pay-outcomes-interactive.html` — standalone page:
- Interactive choropleth map with hover tooltips
- Scatter plot with hover (all 47 countries with PISA data)
- Filterable table (OECD / Asia / Latin America / Africa & ME)
- Full narrative: the measurement, the correlation, the US case, the outliers

## Data sources
- OECD Education at a Glance 2023 — teacher salary ratios
- PISA 2022 — composite scores (reading + math + science / 3)
- Darling-Hammond (2010) — selectivity research

## Thread captions
See captions.txt — 4 tweets (3 with images, 1 companion link)

---

    Approve: python pipeline/approve_post.py staged/teacher-pay-outcomes
    Reject:  rm -rf staged/teacher-pay-outcomes
