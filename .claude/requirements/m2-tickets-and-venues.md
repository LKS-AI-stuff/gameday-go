# GameDay Go — M2: Tickets and venues

| | |
|---|---|
| **Document type** | Milestone requirements |
| **Milestone** | M2 |
| **Status** | Planned (no technical design yet) |
| **Date** | 2026-10-27 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD §13 and the requirement IDs cited below), `.claude/docs/technical-design.md` (TDD sections cited below), `.claude/docs/ui-ux-design.md` |

These are the milestone's requirements: what must be built, as a checklist that cites the BRD, TDD and UI/UX sections holding the detail. `/generate-technical-design m2` turns them into a technical design at `.claude/technical-designs/m2-tickets-and-venues.md`, grounded in the current code; `/implement-technical-design m2` builds that design and ticks the items here as they're delivered.

**Users will be able to:** see tickets (with the hard maximum applied) and nearby sports bars on game detail.

## Before starting

- [ ] Ticketmaster key; Google Places key with billing enabled and a Cloud console daily quota
- [ ] T5: Ticketmaster matching parameters and team attraction IDs
- [ ] T6 and V5: Places endpoint (Text Search vs. Nearby Search), final field mask against the pricing tiers, caching and attribution rules
- [ ] V4: Ticketmaster terms (cache duration, attribution, display)

## Database

- [ ] `provider_cache` (TDD §7.6); `teams.ticketmaster_attraction_id` filled for mapped teams

## Domain rules (TDD §9, §9.1)

- [ ] `travel.py`: `travel_eligible` (Low / Medium / High, international never, unknown distance never; BR-T1–T5)
- [ ] `budget.py`: `filter_offers`, `within_budget` (true / false / unknown), `estimated_total` (BR-S4–S7)
- [ ] `suitability.py`: `rank_options` with the V/S/D formula, eligibility first, tie rule; weights and constants from config

## Providers (TDD §8.4–8.5)

- [ ] Ticketmaster adapter: `find_events`, add-on exclusion keywords, matching by date window, city and team names, price-range normalization; 4,000/day budget, 2 requests/second, 10-minute cache
- [ ] Places adapter: sports bars near a point (8 km, widened once to 16 km), field mask including `utcOffsetMinutes`, `open_at_kickoff`, distance; 30/day cap, 1-hour cache
- [ ] Kill switches; fixture mocks; contract tests; sample data labeled (FR-T6, FR-V5)

## Services and API

- [ ] `tickets.service.filter_by_budget` applied before results reach the UI or the agent (FR-T3)
- [ ] `venues` service; `recommendations` service (ranking, used by the agent in M3)
- [ ] `GET /games/{id}/tickets`, `GET /venues` (`game_id` with `zip` or `lat`/`lng`)
- [ ] Settings: Ticketmaster and Places keys, budgets, cache TTLs, radii, match window, ranking constants (TDD §13)

## Frontend (UI/UX §7.5)

- [ ] Tickets section: price range, "listed price range, fees may apply", buy link, budget-fit line; states for loading, no event, price not available, over max, provider down, outside the window, game final
- [ ] Nearby sports bars: distance, open at kickoff, call-ahead notice (FR-V3), "Search wider", provider attribution (NFR-19)
- [ ] Sections load when scrolled into view; "Outside your travel area" hint under the hero

## Tests

- [ ] Unit: travel rules (AC-5–AC-7), budget boundaries (AC-8, AC-9), ranking worked examples from TDD §9.1, ticket matching cases, opening hours across time zones
- [ ] Integration: provider down or over budget shows the right message (AC-12, FR-T9, FR-V7); venue notice always present (AC-15); budget counter is atomic

## Exit criteria

results follow the budget and travel rules, with clear unavailable states; contract tests pass.
