# GameDay Go — M1: Preferences and schedule

| | |
|---|---|
| **Document type** | Milestone requirements |
| **Milestone** | M1 |
| **Status** | Code complete; exit pending manual device tests and CI: [`.claude/technical-designs/m1-preferences-and-schedule.md`](../technical-designs/m1-preferences-and-schedule.md) |
| **Date** | 2026-10-27 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD §13 and the requirement IDs cited below), `.claude/docs/technical-design.md` (TDD sections cited below), `.claude/docs/ui-ux-design.md` |

These are the milestone's requirements: what must be built, as a checklist that cites the BRD, TDD and UI/UX sections holding the detail. `/generate-technical-design m1` turns them into a technical design at `.claude/technical-designs/m1-preferences-and-schedule.md`, grounded in the current code; `/implement-technical-design m1` builds that design and ticks the items here as they're delivered.

**Users will be able to:** onboard with the six preferences, then browse the schedule and game details with significance tags (BRD §13; journeys J1, J2).

## Before starting

- [x] API-Sports key in `.env` (`APISPORTS_KEY`)
- [x] T4 (done 2026-10-29, needed the Pro plan for the 2026 season): confirm API-Sports endpoint paths, NFL league ID, status codes, team/venue fields, and that one season call returns all games (record sanitized contract fixtures)
- [x] T10: UX1, UX4 and UX5 defaults confirmed 2026-10-28 (UI/UX §11)
- [x] `expo-location` approved for "Use my location" (TDD §4.1): in onboarding it maps the device position to the nearest ZIP (`geo.nearest_zip`), asks for permission only when tapped, and never stores the coordinates (FR-P3)

## Database (each new table calls `secure_table()`)

- [x] Reference data, TDD §7.1: `teams`, `venues_ref`, `featured_rivalries`, `zip_centroids` (with `place_name`, `state`), `place_centroids`
- [x] Preferences, TDD §7.2: `user_preferences`, `user_favorite_teams`, `notification_settings`; `users.timezone` set from the device
- [x] Schedule, TDD §7.3: `games` (including the status and score columns used from M4), `seasons`, `game_changes`, `game_tags`
- [x] Operations, TDD §7.6: `provider_budgets`, `sync_runs`, `app_events`

## Data files and CLI

- [x] `backend/data/`: Census ZCTA and Places gazetteers, `rivalries.toml` (BRD Appendix B), `reference_overrides.toml` (FR-O1a); TOML read with stdlib `tomllib` (decided 2026-10-28, no YAML dependency)
- [x] `cli seed` (teams, rivalries, ZIP and place centroids) and `cli sync-schedule`. The daily schedule runs move to the worker in M4

## Domain rules (pure functions, TDD §9)

- [x] `geo.py`: `haversine_miles`, `is_local`, `nearest_zip`
- [x] `planning.py`: `planning_status` (30-day window, BR-W1, FR-SC8)
- [x] `season.py`: `active_season` (rollover after the Super Bowl, BR-W2, FR-O1c)
- [x] `significance.py`: `schedule_tags` (playoff, division rivalry, featured rivalry, primetime, home opener / home finale, international; BRD §7.6). Record-based tags come in M4
- [x] `schedule_diff.py`: `diff_games` (FR-O2; the alerts it feeds come in M5)

## Provider: API-Sports (TDD §8.3)

- [x] `core/http.py` steps 2–3: atomic daily budget in `provider_budgets` (`APISPORTS_DAILY_BUDGET`, 10% reserve; API-Sports is on the Pro plan, 7,500/day) and the 10 requests/minute limiter
- [x] Adapter `games_for_season` with status mapping and team ID mapping; unmapped records logged and skipped (FR-LS10)
- [x] Fixture mock for tests and CI; contract tests against the recorded responses
- [x] Settings: `APISPORTS_KEY`, `APISPORTS_DAILY_BUDGET`, `APISPORTS_RESERVE_PCT`, `PLANNING_WINDOW_DAYS`, `LOCAL_AREA_MILES`

## Services and API (TDD §12; data endpoints require the 18+ confirmation)

- [x] `schedule_sync`: resolve the active season, fetch, upsert, diff into `game_changes`, recompute schedule tags, record a `sync_runs` row
- [x] `GET`/`PUT /me/preferences` (P1–P6), `GET`/`PUT /me/notification-settings`, `GET /zip/{zip}`
- [x] `GET /teams`, `GET /games` (filters `team`, `week`, `from`, `to`, `favorites`; cursor pagination), `GET /games/{id}` (tags, distance from home, source and freshness), `GET /season`
- [x] `POST /app-events` (allowlisted names; `onboarding_started`, `onboarding_completed` for SM1)
- [x] Per-user and per-IP rate limits with slowapi (NFR-15)
- [x] `DELETE /me` account deletion (FR-A4; not assigned to a milestone before, so placed here with Settings)

## Frontend (UI/UX §6–7)

- [x] Navigation: bottom tabs Home, Schedule, Plan, My Game Days (Plan and My Game Days are empty states until M3); web side rail at ≥ 1024 px; inbox bell and settings in the app bar (UI/UX §2.2)
- [x] Onboarding, six steps plus review (§7.2): `TeamPicker`, `ZipField` (shows "Chicago, IL"), `PreferenceSelector`, optional max ticket price; time zone detected from the device
- [x] Home (§7.3): your next games, plus the schedule-not-released and no-more-games states. Live now and Recent finals come in M4
- [x] Schedule (§7.4): week chips, team filter, day groups, bye-week state
- [x] Game detail (§7.5): `MatchupHero`, tags with explanation sheet, planning-window notice, About section. "Plan this game" is wired in M3, "Set an alert" in M5
- [x] Components: `GameCard` variants (§6.1), `TagChip` (§6.4), `PlanningWindowNotice`, `SampleDataBadge`, data freshness line (§5.1), skeleton / empty / error / offline states (§5.3)
- [x] Settings (§7.11): edit preferences, notification level and categories, time zone, sign out, delete account (no theme setting: one dark theme, NFR-5)
- [x] `packages/shared` formatting: kickoff with time zone (NFR-4), TBD times and teams, records, distance (UI/UX §5.5)

## Tests

- [x] Unit: planning window boundaries, season rollover, every schedule tag (featured rivalry in either home/away order), schedule diff, ZIP lookup and nearest ZIP
- [x] Integration: preferences and games endpoints, user A vs. user B isolation (AC-27), `schedule_sync` against fixtures, provider budget exhaustion
- [x] Frontend: onboarding validation and flow, `GameCard` variants, formatting
- [x] E2E tooling started: Playwright (web) and Maestro (mobile) for onboarding → browse (extended each milestone toward AC-28)

## Exit criteria

J1 and J2 complete on all platforms, with source and freshness labels (FR-SC4); AC-1, AC-2, AC-47 and AC-49 pass.
