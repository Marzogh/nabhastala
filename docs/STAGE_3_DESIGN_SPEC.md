# Stage 3 design specification: an almanac, not a data dump

Status: approved reference study; implementation not started.

This specification translates the useful editorial patterns in the supplied 2025
and 2026 astronomy almanacs and Joe Cali's 2026 SE Queensland handbook into an
original, accessible web experience. It does not copy their artwork, typography,
text, or page layouts.

## Design conclusion

Nabhastala must answer an observer's questions before exposing its datasets:

1. Is this month worth planning for?
2. Which nights and time windows are best?
3. What will the Moon and twilight do?
4. Which planets, showers, occultations, comets, or minor planets are genuinely
   useful from this location?
5. Where can I inspect or download the complete data?

The primary experience is therefore a visual annual overview and twelve curated
monthly field guides. CSV files and exhaustive tables remain first-class products,
but become supporting reference material rather than the page body.

## Reference patterns retained

The reference study covered representative covers, annual calendars, planet
visibility diagrams, monthly spreads, all-sky introductions, satellite-event
diagrams, comet pages, and compact location-specific planning tables.

Patterns to adopt:

- A visual overview first, followed by a short editorial selection, then detail.
- A month is a working unit, not merely a filter applied to every CSV.
- Moon phase, darkness, twilight, and target visibility belong in the same
  decision context.
- Dense data is acceptable when it forms a recognisable instrument with one task.
- Images and diagrams should explain or orient, not decorate empty space.
- A location-specific annual handbook should favour forward planning over a
  generic catalogue of facts.
- Light and dark editions must preserve the same hierarchy and meaning.

Patterns not to adopt:

- Print-sized text or fixed magazine spreads on narrow screens.
- Decorative astronomical imagery without provenance or informational value.
- Full-year row dumps in the main reading flow.
- Colour as the only expression of quality.
- Tables of failed, unavailable, or irrelevant targets in the primary experience.

## Identity hierarchy

The header must read as two semantic groups in this exact order:

```text
नभस्तल
त्रिषु दिगन्तेष्वेकं नभः (Triṣu diganteṣv ekaṃ nabhaḥ)

Nabhastala
One sky at three horizons.
```

The Devanagari name and Sanskrit motto are the primary identity. The English name
and translation are a smaller explanatory gloss; they must not compete in size,
weight, colour, or position. The compact header may place the English gloss beside
the primary block at wide widths, but it remains visually subordinate and follows
it in document order.

## Publication structure and routes

The Stage 3 route contract is:

```text
site/
  index.html
  sites/
    se-qld/<year>/index.html
    southern-tasmania/<year>/index.html
    malabar-coast/<year>/index.html
    <site-slug>/<year>/months/01.html ... 12.html
    <site-slug>/<year>/data/index.html
```

During Stage 3 development, the same templates may continue to render under
`output/<site-id>/<year>/`; final `site/` assembly and Pages base-path handling
remain Stage 6 work.

Navigation order:

- identity link to the Nabhastala landing page when published;
- location and year context;
- Overview;
- Months;
- Data & downloads;
- Chips'nCode;
- theme control.

All links remain ordinary links and all content remains available without
JavaScript.

## Landing page

Purpose: choose one of the three horizons and an available year with no prior
knowledge of site IDs.

Required content:

- the exact four-line identity with the prescribed hierarchy;
- one-sentence purpose: a local, reproducible observing and nightscape planner;
- three location cards using public names, local time zones, and stable slugs;
- available year links per location, with 2027 presented as the initial reviewed
  edition;
- a short explanation of reviewed data, downloads, and field PDF availability.

No astronomical data table belongs on this page.

## Annual overview

Purpose: decide which months deserve attention, then enter a monthly guide.

Reading order:

1. Compact location/year masthead.
2. **Year at a glance**: a twelve-month grid with moon-state markers, strongest
   opportunity category, and an explicit quality word for each month.
3. **Best of the year**: at most six ranked opportunities drawn only from valid,
   observable records. Each item states date/window, target, reason, and month link.
4. **Seasonal sky**: the existing Milky Way annual chart and planet summary placed
   beside short explanations of what decisions they support.
5. **Month index**: twelve editorial cards with a one-line verdict, best dark-sky
   window, Moon state, and up to two highlights.
6. **Reference and downloads**: links to the dataset library, validation/provenance,
   CSV bundle, and later the field PDF.

The annual overview must not render any complete dataset or a sequence of generic
dataset sections. Empty and failed source records never become annual highlights.

## Monthly field guide

Purpose: make an observing decision in under a minute, then support detailed
planning.

Desktop uses an asymmetric editorial grid; mobile follows the same document order
in one column:

```text
Month title + verdict              Location / year controls
------------------------------------------------------------
Night-planning overview            3-5 highlights
(static Stage 3 summary)           Moon and darkness
------------------------------------------------------------
Milky Way / deep-sky sessions      Planet visibility
------------------------------------------------------------
Meteor / occultation / transient opportunities, when present
------------------------------------------------------------
Data notes                         Downloads and full tables
```

Required sections:

- **Monthly verdict**: one plain-language sentence grounded in valid source data.
- **Night-planning overview**: new/full moon dates, representative astronomical
  dusk and dawn, and the best moon-free windows. Stage 3 uses semantic HTML and
  restrained CSS; the richer continuous timeline belongs to Stage 4.
- **Highlights**: three to five ranked events or sessions, never filler.
- **Moon and darkness**: phase progression, best dark period, and moonlight caveat.
- **Milky Way and deep sky**: only recommended sessions, with start/end, duration,
  maximum core altitude, and a short verdict.
- **Planets**: one compact row or card per useful planet, grouped into evening,
  overnight, and predawn. Do not show daily records here.
- **Other opportunities**: meteor showers, occultations, viable comets, and viable
  minor planets appear only when the month contains trustworthy results.
- **Data notes**: disclose missing calculations or query failures without allowing
  them to dominate the page.
- **Downloads**: direct monthly/full CSV links and an optional accessible full-table
  disclosure.

The sticky desktop section navigation and horizontally scrollable mobile month
navigation must never trap vertical page scrolling.

## Dataset presentation rules

| Source | Primary almanac treatment | Complete-data treatment |
| --- | --- | --- |
| Sun/twilight | monthly darkness summary | CSV and optional full table |
| Moon phase + rise/set | phase markers and concise Moon panel | CSV and optional full table |
| Moon-free windows | best ranked sessions | CSV and optional full table |
| Milky Way windows | recommended sessions + existing chart | CSV and optional full table |
| Daily planets | useful planets grouped by observing period | CSV only by default |
| Planet monthly summary | compact planet cards | CSV and optional full table |
| Jupiter/Saturn moons | link to specialised instrument | CSV; Stage 4 visual tool |
| Minor planets | valid, chaseable opportunities only | complete CSV |
| Comets | valid, chaseable opportunities only | complete CSV; failures in data note |
| Occultations | event cards when present | CSV and explicit empty state |
| Meteor showers | peak card with Moon interference and verdict | CSV and optional full table |

Primary cards show local date/time first. UTC, raw precision, internal identifiers,
calculation status, and provenance columns belong in detail or downloads.

## Selection and failure rules

- A card must be derived deterministically from existing values; renderer code does
  not alter scientific scores.
- Prefer `excellent`, then `good`, then `fair`; include `poor` only when explaining
  a well-known event whose local conditions are poor.
- `query_failed`, missing time/altitude, and non-chaseable records are excluded from
  highlights.
- Preserve a count and explanation of excluded records in Data notes.
- Never claim “best” without displaying the deciding value or reason.
- Ties use date/time and then stable source order so fixture output is repeatable.
- Editorial summaries use controlled templates, not invented astronomical claims.

## Visual and interaction direction

- Retain the Chips'nCode warm paper/charcoal, terracotta, cream, fine-rule, modest
  radius system, but introduce stronger editorial rhythm through varied column
  widths, compact diagrams, bordered calendar cells, and purposeful empty space.
- Use one atmospheric celestial visual only where it carries context and can be
  locally licensed or generated; do not make a generic hero image a dependency.
- Prefer diagrams, phase symbols, timing bands, and small multiples over decorative
  icons.
- Provide text labels beside every colour state and patterns/borders that remain
  distinct in monochrome.
- Remembered theme and optional filters are enhancements. Navigation, disclosures,
  tables, and downloads work without scripts.
- At 200% text zoom, content reflows without clipped cards or two-dimensional page
  scrolling. Wide tables may scroll inside clearly labelled regions.

## Stage boundary

Stage 3 builds the landing page, stable information architecture, editorial
selection helpers, annual overview, monthly guides, dataset library, and accessible
navigation. It may reuse current charts.

Stage 4 builds astronomy-specific continuous timelines, moon/planet diagrams,
satellite offset instruments, richer filtering, and other progressive visual tools.
Stage 5 owns the curated field PDF. Stage 6 owns reviewed release assembly and
GitHub Pages deployment.

## Restart-safe implementation slices

Each slice updates `docs/IMPLEMENTATION_STATUS.md`, runs its focused tests, and is
committed before the next begins.

1. **3A — Contracts and selection helpers**
   - Stable public slugs and route helpers.
   - Typed annual/monthly view models and deterministic ranking.
   - Tests for missing, failed, tied, and poor records.
2. **3B — Identity and landing page**
   - Correct identity hierarchy.
   - Location/year selector and dataset-library route.
   - Semantic, no-JavaScript, and link tests.
3. **3C — Annual overview**
   - Year-at-a-glance, best-of-year, seasonal context, and month cards.
   - Removal of raw annual tables from the primary page.
4. **3D — Monthly guide**
   - Decision-led monthly composition and contextual download links.
   - Mobile/desktop navigation and empty/failure states.
5. **3E — Dataset library and visual QA**
   - Full-data access, captions, table disclosures, provenance links.
   - Keyboard, no-JavaScript, light/dark, 200% zoom, narrow/wide QA.

Suggested slice checkpoint tags are `stage-3a-contracts`, `stage-3b-landing`,
`stage-3c-annual`, `stage-3d-monthly`, and `stage-3-information-architecture`.

## Stage 3 acceptance checks

- The four-line identity is exact and correctly subordinated.
- A visitor can select a location/year and reach any month through stable links.
- Annual and monthly pages contain no exhaustive table in their initial reading
  flow.
- A visitor can identify a promising month and useful session without interpreting
  internal column names.
- Complete CSV data remains directly reachable, including unavailable/failed rows.
- All three locations coexist without path collision or cross-linking.
- Core information and navigation work without JavaScript.
- Keyboard focus, contrast, reduced motion, 200% zoom, and phone/tablet/desktop
  layouts pass focused checks in both themes.
- Existing scientific and CLI tests remain green.

## Resume instruction

Do not implement Stage 3 until the user authorises it. After authorisation, begin
only slice 3A from the repository root:

```bash
git status --short
git describe --tags --exact-match
PYTHONPATH=src .venv/bin/pytest -q
```

Then record slice 3A's affected files and focused test command in
`docs/IMPLEMENTATION_STATUS.md` before editing code.
