# Design System - WhichMovieItIs

## Product Context

- **What this is:** A local-first movie search app that finds films from rough plot, scene, title, object, or memory descriptions.
- **Who it's for:** People who remember a movie scene but not the title, and a developer who needs the project to look like a real product locally.
- **Space/industry:** Movie discovery, catalog browsing, and semantic search.
- **Project type:** Web app with a cinematic landing/search surface, catalog browser, and movie-detail modal.

## Aesthetic Direction

- **Direction:** Light editorial movie catalog.
- **Decoration level:** Intentional and restrained: poster imagery, orange actions, clean borders, strong typography, and very low curvature.
- **Mood:** It should feel like a product built carefully by a human developer: useful, direct, readable, and not overly glossy or generated.
- **Reference sites:** https://www.whatfilmis.com/en for product structure only; visual treatment is intentionally lighter, sharper, and orange-led.

## Typography

- **Display/Hero:** Sora - sharp, compact, strong enough for cinematic hero headings.
- **Body:** Source Sans 3 - readable for plot summaries, card text, forms, and dense movie metadata.
- **UI/Labels:** Source Sans 3 with heavier weights for buttons, chips, and nav.
- **Data/Tables:** Source Sans 3 with numeric values kept short; use tabular numbers if data tables are added later.
- **Code:** JetBrains Mono if code snippets are ever shown.
- **Loading:** Google Fonts import in `frontend/src/styles/tokens.css`.
- **Scale:** Hero 48-108px, section heading 30-48px, card title 16px, body 15-18px, metadata 13-14px.

## Color

- **Approach:** Light, warm, high-contrast palette.
- **Primary:** `#ff6600` - primary buttons, active navigation, accents, and interactive states.
- **Primary hover:** `#e65c00` - hover and pressed state.
- **Background:** `#ffffff` - the main app background.
- **Warm surface:** `#fff5e9` - subtle search/action panels without becoming beige-heavy.
- **Border:** `#fed7aa` - cards, panels, input separators, modal edges, and chips.
- **Neutrals:** `#171717`, `#5f5f5f`, `#8a6f5a`, `#ffffff`.
- **Semantic:** error `#b42318`, warning `#f59e0b`, success `#15803d`, info `#2563eb`.
- **Dark mode:** Not part of the current local MVP design; keep the product light unless explicitly redesigned later.

## Spacing

- **Base unit:** 4px.
- **Density:** Comfortable on landing sections, compact inside movie cards.
- **Scale:** 2xs 4px, xs 8px, sm 12px, md 16px, lg 24px, xl 32px, 2xl 48px, 3xl 64px, 4xl 92px.

## Layout

- **Approach:** Hybrid: editorial search hero, grid-disciplined catalog, focused modal details.
- **Grid:** Auto-fill movie cards with `minmax(168px, 1fr)`, two columns on small mobile.
- **Max content width:** 1160px.
- **Border radius:** mostly square; small 0-2px only where browser rendering needs edge softening. Avoid pill buttons and rounded cards.

## Motion

- **Approach:** Minimal-functional.
- **Easing:** `ease` for hovers and overlay transitions.
- **Duration:** Micro 120-180ms for hover lift and poster scale; avoid heavy animation because search speed should feel direct.

## Decisions Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-07-08 | Use light background, orange primary, and warm orange border | User explicitly requested `#ffffff`, `#ff6600`, and `#fed7aa`. |
| 2026-07-08 | Avoid rounded AI-style UI | User explicitly rejected over-rounded cards, buttons, and generated-looking design. |
| 2026-07-08 | Split frontend into components, data, lib, and style files | User explicitly wanted modular code instead of one large `App.jsx`. |
| 2026-07-07 | Keep header minimal with only Films navigation | User explicitly removed community, collections, sign-in, and language. |
| 2026-07-07 | Add Films grid and movie detail modal | Required to browse all local DB movies and open details using real stored fields. |
