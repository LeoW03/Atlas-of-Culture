#!/usr/bin/env python3
"""Inject a sources + caveats section into Atlas of Culture interactive HTML files."""

from pathlib import Path

SOURCES = {
    "teacher-pay-outcomes-interactive.html": {
        "sources": [
            ("OECD Education at a Glance 2023", "https://www.oecd.org/education/education-at-a-glance/", "Teacher salary ratios (lower secondary, salary relative to national average wage). Data year: 2021–2022."),
            ("PISA 2022 Results", "https://www.oecd.org/pisa/", "Programme for International Student Assessment composite score (reading + math + science ÷ 3). Conducted every 3 years; 2022 is the most recent."),
            ("Darling-Hammond, L. (2010). The Flat World and Education", "https://tcpress.com/", "Teacher selectivity and professional status research."),
        ],
        "caveats": [
            "The pay ratio measures salary relative to the national average wage — it captures status and competitiveness within a country, but does not reflect absolute purchasing power. A teacher in Luxembourg earning 198% of the average wage may have lower real purchasing power than one in a cheaper country earning 110%.",
            "Non-OECD salary figures (Singapore, China, India, etc.) are sourced from national statistical publications rather than direct OECD measurement. Methodology varies across countries; treat these as indicative, not precise.",
            "China's PISA data covers only four provinces (Shanghai, Beijing, Jiangsu, Zhejiang) — among the highest-performing regions in the country. It is not nationally representative.",
        ],
    },
    "insulin-price-geography-interactive.html": {
        "sources": [
            ("RAND Corporation / Health Affairs 2021", "https://www.rand.org/pubs/research_reports/RR2525.html", "Internationally comparable retail prices for a standard vial of insulin across 56 countries. Prices are unadjusted for purchasing power parity."),
            ("Health Affairs, Vol. 40, No. 1 (2021)", "https://www.healthaffairs.org/doi/10.1377/hlthaff.2020.00494", "Peer-reviewed companion analysis on insulin pricing disparities."),
        ],
        "caveats": [
            "The RAND data reflects 2018 retail prices. Since then, US insulin list prices have changed materially: in 2023, all three major manufacturers (Eli Lilly, Novo Nordisk, Sanofi) capped out-of-pocket costs at $35/month for insured patients, and biosimilar insulins entered the market at lower prices. The structural gap with other wealthy nations persists, but the most extreme figures are somewhat improved.",
            "Prices are unadjusted for purchasing power parity. A PPP-adjusted comparison would make the US gap smaller relative to wealthier countries and larger relative to lower-income ones.",
            "The '9 million Americans ration insulin' figure is from Herkert et al. (2019, Yale) and predates the 2023 cap legislation. Current rationing figures are likely lower but remain significant.",
            "Non-RAND country prices (India, Pakistan, and others beyond the study's 56 countries) are estimated from WHO and IMS Health data and carry higher uncertainty.",
        ],
    },
    "free-press-trust-interactive.html": {
        "sources": [
            ("RSF World Press Freedom Index 2024", "https://rsf.org/en/index", "Annual ranking of 180 countries on press freedom. Score 0–100 (higher = freer). Methodology covers pluralism, independence, environment, self-censorship, legislative framework, transparency, and infrastructure."),
            ("Reuters Institute Digital News Report 2024", "https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2024", "Annual survey on news consumption and trust across 47 countries. Trust question: 'I think you can trust most news most of the time.'"),
        ],
        "caveats": [
            "These two datasets measure structurally different things. RSF scores the legal and physical environment for journalists — government interference, violence, legal harassment. Reuters measures what ordinary people say when asked if they trust the news. The scatter plot shows correlation, not causation; a country can have a free press that its citizens distrust for reasons entirely unrelated to press freedom.",
            "China's reported trust figure (~80%) should be interpreted cautiously. Surveying in an authoritarian context may not capture genuine sentiment, and critical media consumption carries social and legal risk.",
        ],
    },
    "less-school-better-scores-interactive.html": {
        "sources": [
            ("OECD Education at a Glance 2023", "https://www.oecd.org/education/education-at-a-glance/", "Intended instruction time in hours per year for lower-secondary education. Data year: 2021–2022."),
            ("PISA 2022 Results (Volume I)", "https://www.oecd.org/pisa/", "PISA composite score averaged across reading, mathematics, and science. 80+ countries/economies participated."),
        ],
        "caveats": [
            "Instructional hours are 'intended' time as reported to the OECD — actual classroom time varies due to holidays, teacher absences, and school culture. Countries differ in how much instructional time is also homework, tutoring, or private supplementary education (particularly relevant for South Korea and Japan, where private tutoring hours are substantial and uncounted here).",
            "China's PISA data covers only Shanghai, Beijing, Jiangsu, and Zhejiang — four of the highest-performing provinces. It is not nationally representative.",
        ],
    },
    "democracy-satisfaction-paradox-interactive.html": {
        "sources": [
            ("IDEA Voter Turnout Database", "https://www.idea.int/data-tools/data/voter-turnout", "Voter turnout as % of registered voters in most recent national legislative election (data through 2023)."),
            ("World Values Survey Wave 7 (2017–2022)", "https://www.worldvaluessurvey.org/", "Democratic satisfaction question: 'How satisfied are you with the way democracy works in your country?' % responding satisfied or very satisfied."),
            ("Eurobarometer Autumn 2023", "https://europa.eu/eurobarometer/", "Supplementary trust-in-democracy data for EU member states."),
        ],
        "caveats": [
            "Australia, Belgium, Brazil, and Uruguay have compulsory voting laws. Their high turnout figures are legally mandated rather than expressions of civic enthusiasm — comparing them directly to voluntary-voting countries conflates two different things. They are flagged in the table.",
            "Switzerland's result is not an accident of sampling — it reflects a structurally different democratic system. Swiss citizens vote in 4–6 national referendums per year on specific policy questions, in addition to electing representatives. The satisfaction finding makes sense once you understand this; it doesn't generalise to other low-turnout contexts.",
            "Satisfaction survey data comes from different waves of the World Values Survey (2017–2022) across different countries. A country surveyed during a period of political crisis will show lower satisfaction than one surveyed during stable governance, independently of systemic quality.",
        ],
    },
}

SECTION_TEMPLATE = """
  <!-- ── SOURCES & CAVEATS ── -->
  <div class="sources-section">
    <h2>Data sources</h2>
    {sources_html}
    <h2>Caveats & methodology notes</h2>
    <ul class="caveats-list">
      {caveats_html}
    </ul>
  </div>
"""

STYLES = """
  /* ── Sources & Caveats ── */
  .sources-section {
    padding: 52px 64px 72px;
    max-width: 760px;
    margin: 0 auto;
    border-top: 1px solid rgba(255,255,255,0.06);
  }
  .sources-section h2 {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 22px;
    color: rgba(255,255,255,0.75);
    margin-bottom: 18px;
    margin-top: 36px;
  }
  .sources-section h2:first-child { margin-top: 0; }
  .source-item {
    margin-bottom: 16px;
    padding-left: 16px;
    border-left: 2px solid rgba(232,197,71,0.25);
  }
  .source-name {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 14px;
    color: rgba(255,255,255,0.7);
    margin-bottom: 3px;
  }
  .source-name a {
    color: rgba(232,197,71,0.7);
    text-decoration: none;
  }
  .source-name a:hover { color: #e8c547; text-decoration: underline; }
  .source-desc {
    font-family: 'Inter', sans-serif;
    font-weight: 300;
    font-size: 13px;
    color: rgba(255,255,255,0.38);
    line-height: 1.6;
  }
  .caveats-list {
    list-style: none;
    padding: 0;
  }
  .caveats-list li {
    font-family: 'Inter', sans-serif;
    font-weight: 300;
    font-size: 13.5px;
    color: rgba(255,255,255,0.38);
    line-height: 1.65;
    padding: 10px 0 10px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    position: relative;
  }
  .caveats-list li:last-child { border-bottom: none; }
  .caveats-list li::before {
    content: '—';
    position: absolute;
    left: 0;
    color: rgba(232,197,71,0.3);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
  }
"""


def inject(html_path: Path, filename: str):
    if filename not in SOURCES:
        print(f"  ⚠️  No source data for {filename}")
        return

    data = SOURCES[filename]
    txt = html_path.read_text()

    # Don't inject twice
    if 'sources-section' in txt:
        print(f"  ⏭  Already has sources section: {filename}")
        return

    # Build sources HTML
    sources_html = "\n    ".join([
        f'<div class="source-item"><div class="source-name"><a href="{url}" target="_blank" rel="noopener">{name}</a></div><div class="source-desc">{desc}</div></div>'
        for name, url, desc in data["sources"]
    ])

    # Build caveats HTML
    caveats_html = "\n      ".join([
        f"<li>{c}</li>" for c in data["caveats"]
    ])

    section = SECTION_TEMPLATE.format(
        sources_html=sources_html,
        caveats_html=caveats_html,
    )

    # Inject styles before </style>
    txt = txt.replace("</style>", STYLES + "\n</style>", 1)

    # Inject section before site-footer or before </body>
    if 'class="site-footer"' in txt:
        txt = txt.replace('<div class="site-footer">', section + '\n<div class="site-footer">', 1)
    elif 'site-footer' in txt:
        idx = txt.rfind('site-footer')
        insert_at = txt.rfind('<div', 0, idx)
        txt = txt[:insert_at] + section + "\n" + txt[insert_at:]
    else:
        txt = txt.replace("</body>", section + "\n</body>", 1)

    html_path.write_text(txt)
    print(f"  ✅ {filename}")


if __name__ == "__main__":
    base = Path(__file__).parent.parent / "staged"
    files = [
        base / "teacher-pay-outcomes"           / "teacher-pay-outcomes-interactive.html",
        base / "insulin-price-geography"         / "insulin-price-geography-interactive.html",
        base / "free-press-trust"                / "free-press-trust-interactive.html",
        base / "less-school-better-scores"       / "less-school-better-scores-interactive.html",
        base / "democracy-satisfaction-paradox"  / "democracy-satisfaction-paradox-interactive.html",
    ]

    print("\n📚 Adding sources + caveats sections...\n")
    for path in files:
        if path.exists():
            inject(path, path.name)
        else:
            print(f"  ❌ Not found: {path}")
    print("\nDone.\n")
