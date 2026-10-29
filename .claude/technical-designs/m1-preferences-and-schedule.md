# GameDay Go — M1: Preferences and schedule

| | |
|---|---|
| **Document type** | Milestone technical design |
| **Requirements** | `.claude/requirements/m1-preferences-and-schedule.md` |
| **Milestone** | M1 |
| **Status** | Code complete. Exit pending: manual tests on web, iOS and Android; the Maestro flow; CI on GitHub |
| **Date** | 2026-10-29 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD), `.claude/docs/technical-design.md` (TDD), `.claude/docs/ui-ux-design.md` (UI/UX), M0 as implemented (`m0-foundation.md`) |

This milestone is implemented. The sections below describe what was built, how to run and test it, and the database queries that confirm the data.

**Users can:** onboard with the six preferences (P1–P6; time zone from the device), then browse the season by week, team or their own teams, open a game and see kickoff in their time zone, venue, distance from home, significance tags with explanations, when planning opens, and the schedule's source and freshness. They can edit preferences and notification settings, and delete their account (BRD §13; journeys J1, J2).

**Exit criteria:** J1 and J2 complete on web, iOS and Android with source and freshness labels (FR-SC4); AC-1, AC-2, AC-47 and AC-49 pass.

## Decisions

| Decision | Rationale |
|---|---|
| **API-Sports on the Pro plan** (7,500 requests/day, 300/minute). `APISPORTS_DAILY_BUDGET` defaults to 1,000, as the app's safety cap | T4 found the free plan can't read the 2026 season ("try from 2022 to 2024"). Approved 2026-10-29. BRD A4, TDD D10, V1, §8.3, §13, §21 and `CLAUDE.md` updated |
| Data files are TOML (`rivalries.toml`, `reference_overrides.toml`), read with stdlib `tomllib` | Approved 2026-10-28 instead of adding PyYAML |
| "Home opener / home finale" tag: the home team's first and last regular-season home game, international games excluded | Approved 2026-10-28; a literal "season finale" would tag all of Week 18 |
| Team IDs are API-Sports team codes (`CHI`, `KC`, `LA`…); the nickname is the name's last word | T4: `/teams` returns a `code`, so no curated mapping is needed (FR-LS10 maps by `apisports_team_id`) |
| API-Sports gives a venue's name and city only. `reference_overrides.toml` `[venue_cities]` gives each city's state (US) or country and coordinates (abroad). Teams' home venues come from where they play most US home games | T4. Unknown cities are logged (`venue_cities_unmapped`); their games have no distance and no international tag |
| A `time` of `00:00` marks a TBD kickoff; `date` is then the game day (`games.game_date`) | T4. Real kickoffs are never exactly 00:00 UTC (8:00 PM ET slots are 00:15/00:20 UTC) |
| `games.sort_at`: kickoff, or 23:59 Eastern on the game day while TBD | One indexed column for ordering and cursor pagination, with TBD games last on their day |
| ZIP place names ("Chicago, IL") are computed by `cli build-centroids`, picking the nearest Census place weighted by its land area | A plain nearest-centroid labeled ZIP 10001 "Hoboken"; weighting fixes big cities. Known gap: San Francisco's Census center is offshore, so downtown SF ZIPs read "Oakland" |
| Undecided playoff slots are stored with "TBD" placeholders and deleted when API-Sports re-lists them under new IDs | T4: playoff placeholders have team ID 0 |
| "Use my location" calls `POST /zip/nearest` with the coordinates in the body | Coordinates never reach URLs or access logs (FR-P3a); checked against the API log |
| Account deletion: app rows first, then the Auth Admin API with `SUPABASE_SECRET_KEY` (`apikey` header; checked against the local stack); `503 auth_deletion_failed` on failure, and a retry converges | No retry job before M4. After deletion, Supabase's logout returns 403 (user gone); the client still clears its session |
| Rate limits are router dependencies on slowapi's limiter: 60/min per user (authenticated routes), 60/min per IP (health, ready) | slowapi's middleware runs before authentication |
| Tests run against `<database>_test`, created automatically | Integration tests rewrite schedule data; the dev database keeps live data |
| Tag chips inside a game card are labels, not buttons | A button inside the card's button is invalid HTML (React error on web). Tags are explained on game detail |
| Onboarding keeps its answers in component state | Zustand wasn't needed for a single screen |
| Game detail is one column on desktop until M2 | The right column (tickets, bars) only has content from M2 |
| `expo-location` pinned to 58.0.18 | The repo's minimum-release-age policy rejected 58.0.20 (one day old); `expo install` had added policy exclusions, which were removed |

## Implemented

**Database** (`backend/migrations/versions/0002_preferences_schedule.py`, models in `app/db/models.py`)
- 15 tables in schema `app`, each with forced RLS through `secure_table()`: `teams`, `venues_ref`, `featured_rivalries`, `zip_centroids`, `place_centroids` (TDD §7.1); `user_preferences`, `user_favorite_teams`, `notification_settings` (§7.2); `games`, `seasons`, `game_changes`, `game_tags` (§7.3); `provider_budgets`, `sync_runs`, `app_events` (§7.6).
- User-owned tables cascade from `users` (FR-A4). Enumerations are `text` with `CHECK` constraints. `games` has the M4 score columns (null until then).

**Reference data** (`backend/data/`, `app/modules/schedule/centroids.py`, `reference.py`)
- `zip_centroids.csv` (33,780 ZCTAs with place name and state) and `place_centroids.csv` (32,130 places), built from the 2025 Census gazetteers by `cli build-centroids`.
- `rivalries.toml` (BRD Appendix B, 10 pairs) and `reference_overrides.toml` (37 venue cities; optional team overrides), validated on load.

**Domain rules** (`app/domain/`, pure, mypy strict; TDD §9)
- `geo.py`: `haversine_miles`, `is_local` (unknown venue → never local), `nearest_zip`.
- `planning.py`: `planning_status` → `Open` / `OpensOn(at)` (UTC) / `Closed`; TBD times use the game day (BR-W1, FR-SC8).
- `season.py`: `active_season` with rollover once the Super Bowl is final or a day after it (BR-W2, FR-O1c).
- `significance.py`: `schedule_tags` for playoff, division rivalry, featured rivalry (either order), primetime (Thu/Sun/Mon from `PRIMETIME_START_ET` in Eastern time), home opener / home finale, international (BRD §7.6).
- `schedule_diff.py`: `diff_games` (FR-O2).

**Provider layer**
- `core/http.py` now spends one budget unit and waits for the rate limiter on every attempt, retries included (TDD §8.2 steps 2–3), and logs budget used and remaining. `core/budgets.py`: atomic consumption in its own transaction, reserved share, warning at `PROVIDER_BUDGET_WARN_PCT` (FR-O4a). `core/rate_limit.py`: async token bucket.
- `app/providers/apisports/`: Protocol (`base.py`), live adapter (`live.py`; errors in a 200 body raise `ProviderError` without the body), mapping (`mapping.py`; T4 shapes), fixture provider for tests (`mock.py`), factory (`app/providers/factory.py`).
- Contract fixtures (recorded 2026-10-29, no secrets): `backend/tests/contract/fixtures/apisports/{games,teams,standings}_2026.json`.

**Services and API** (`/api/v1`, Bearer token, 18+ confirmation required)
- `GET /me` gains `onboarded`; `DELETE /me` (FR-A4).
- `modules/preferences`: `GET`/`PUT /me/preferences` (only P1–P6 plus `timezone` accepted, AC-1; at least one team, AC-2), `GET`/`PUT /me/notification-settings` (BR-N9), `GET /zip/{zip}`, `POST /zip/nearest`.
- `modules/schedule`: `GET /teams`, `GET /season` (active year, availability, current week, week labels, planning window, schedule source and last update), `GET /games` (`season`, `week`, `team`, `favorites`, `from`, `to`, cursor, `limit` ≤ 100), `GET /games/{id}` (tags with details, distance from home, planning status, source and freshness, Low-travel hint).
- `schedule_sync` (`modules/schedule/sync.py`): active season → fetch outside transactions → map teams (unmapped records skipped, FR-LS10) → resolve venues → upsert → `game_changes` → schedule tags → home venues → season row → rollover to the next season when the Super Bowl is over → `sync_runs`. Provider, budget and data errors fail the run and leave games as they were (NFR-11).
- `POST /app-events` (allowlisted §15.1 names, no properties yet, client time within a day; SM1).
- Rate limits (NFR-15) and `ProblemError` headers (`Retry-After`).
- CLI: `build-centroids`, `seed [--refresh-teams]`, `sync-schedule [--season]`, `budgets`.

**Shared packages**
- `packages/shared`: `format.ts` (kickoff with zone, TBD, day groups, matchup, record, distance, relative and exact times, planning-opens copy, device zone), `tags.ts`, `preferences.ts` (options, helper copy, Zod schemas, categories by level, US time zones), `COPY` strings (UI/UX §8.2).
- `packages/api-client`: typed methods for every M1 endpoint, query-string support, `ApiNetworkError`, hooks keyed by user ID.

**Screens and components** (`packages/ui`)
- Components: `AppBar`, `GameCard` (full and compact; open, opens-on, TBD, postponed/cancelled, final, sample variants; one screen-reader label), `MatchupHero`, `TagChip` / `TagRow` with explanation sheet, `PlanningWindowNotice`, `SampleDataBadge`, `FreshnessLine` (tap for the exact time), `TravelHint`, `TeamPicker` (division groups, search, single or multi), `ZipField` ("Use my location" asks permission only on tap), `PreferenceSelector`, `CardGrid` (1/2/3 columns at 600/1024 px), `Skeleton` (after 300 ms, no shimmer), `EmptyState`, `ErrorState` (request ID behind Details), `OfflineBanner`, `InfoSheet`; `Screen` gained wide, hero-band and pull-to-refresh options.
- Screens: `OnboardingScreen` (six steps + review with Edit; SM1 events), `HomeScreen` (next game per favorite team, max 5; not-released and no-more-games states), `ScheduleScreen` (week chips scrolled to the current week, team filter sheet, My teams, day groups, bye-week state with "Next game"), `GameDetailScreen`, `SettingsScreen` (each preference in a dialog with the FR-P4 note, level and categories, time zone, sign out, delete with `DELETE`), `InboxScreen`, `ComingSoonScreen`.
- Navigation (`navigation.tsx`, both apps): bottom tabs Home, Schedule, Plan, My Game Days; left rail on web at ≥ 1024 px; `(app)` routes guarded by `me.onboarded`; routes for onboarding, games, settings and inbox.

**E2E**
- Playwright (`apps/web/e2e/onboard-browse.spec.ts`, phone and desktop viewports): sign in → onboarding → Home → Schedule → game detail → delete account in Settings; fails on React errors.
- Maestro (`apps/mobile/.maestro/onboard-browse.yaml`): sign in → onboarding → Home → Schedule → game detail in Expo Go. Written, not run yet (no Maestro or simulator here).

**CI** (`.github/workflows/ci.yml`): `PROVIDER_APISPORTS_ENABLED=false` for the backend job and the API client step (no keys in CI).

## Deferred

| Item | Moves to | Note |
|---|---|---|
| Daily `schedule_sync` job | M4 | Runs from `cli sync-schedule` until the worker exists |
| Records, division rank, record-based tags | M4 | `game_tags.source = 'standings'` is empty |
| Scores, "Live now", "Recent finals" | M4 | Score columns exist; not in the API yet |
| "Plan this game" | M3 | Shown disabled with "Planning arrives soon" |
| "Set an alert", Inbox items, schedule-change alerts | M5 | `game_changes` rows are already written |
| Tickets and bars on game detail (the desktop right column) | M2 | |
| Privacy notice page | M6 | |

## First-time setup

On top of M0's setup (`m0-foundation.md`):

```bash
# .env (repo root): add the API-Sports key (Pro plan) and the local Supabase secret key
#   APISPORTS_KEY=<your key>
#   SUPABASE_SECRET_KEY=<"Secret" from `pnpm supabase status`>   (account deletion)
pnpm install
cd backend && uv sync
uv run alembic upgrade head
uv run python -m app.cli seed            # places, ZIPs, teams (2 API-Sports requests), rivalries
uv run python -m app.cli sync-schedule   # the 2026 season (1 request)
uv run python -m app.cli budgets         # today's API-Sports usage
```

- `seed` is safe to re-run; it reloads teams only with `--refresh-teams`. Re-run `sync-schedule` to pick up schedule changes.
- `alembic downgrade` drops the M1 tables and their data: run `seed` and `sync-schedule` again afterwards.
- Rebuilding the ZIP and place files (once per Census release): download the national ZCTA and Places gazetteers from census.gov, then `uv run python -m app.cli build-centroids <zcta.txt> <places.txt>`.
- Web E2E, once: `pnpm --filter @gamedaygo/web exec playwright install chromium`.

## Run it

```bash
pnpm supabase start
cd backend && uv run uvicorn app.main_api:create_app --factory --reload --host 0.0.0.0
pnpm --filter @gamedaygo/web dev        # http://localhost:8081
pnpm --filter @gamedaygo/mobile dev     # Expo Go
```

- If the web app shows type errors in your editor for new routes, start the dev server once: Expo regenerates `.expo/types/router.d.ts` for typed routes.
- The schedule is as of the last `sync-schedule`; there's no daily job until M4.

## Automated checks

```bash
pnpm turbo run lint typecheck test       # shared (20), api-client (8), ui (78), web and mobile routing (6 each)
pnpm format:check
cd backend
uv run ruff format --check . && uv run ruff check . && uv run mypy app migrations tests
uv run pytest                            # 164: domain, contract, HTTP layer, integration (own *_test database)
uv run pytest -m supabase                # Data API exposure, incl. the 15 new tables
cd .. && pnpm --filter @gamedaygo/web e2e    # Playwright, phone + desktop; needs stack, API and web app
maestro test apps/mobile/.maestro/onboard-browse.yaml -e EXPO_URL=exp://<LAN IP>:8082 -e EMAIL=… -e PASSWORD=…
```

Automated coverage of the acceptance criteria: AC-1 (`test_only_the_six_preferences_are_accepted`, onboarding screen test), AC-2 (`test_favorites_add_remove_and_keep_at_least_one`, Settings test), AC-27 (`test_isolation.py`), AC-47 (`test_planning.py`, `test_planning_window_and_closed_games`, GameCard test), AC-49 (`test_season.py`, `test_rollover_after_super_bowl_shows_next_season_not_released`). AC-49 can't happen on the calendar until February, so it's covered by tests only.

## Manual tests: web (http://localhost:8081)

Use a new account (M0 W2–W6) so onboarding starts fresh.

| # | Do | Expect |
|---|---|---|
| W1 | Sign in with a verified account that hasn't onboarded | "Who do you root for?", "Step 1 of 6"; **Next** disabled. Q7 shows `onboarding_started` |
| W2 | Search "lions", pick Lions; clear the search, pick Bears; **Next** | Tiles grouped by division with check marks; step 2 |
| W3 | Type `00000` | "We couldn't find that ZIP. Check the 5 digits."; **Next** disabled |
| W4 | Type `60601` | "Chicago, IL" |
| W5 | **Use my location** and block the browser prompt | "No problem, enter your ZIP instead." (Allowing fills the nearest ZIP and its city) |
| W6 | Steps 3–6 | Defaults selected: Medium, Medium, Flexible, Medium; the helper line follows the selection. Step 4: **Set a max ticket price**, enter 90 |
| W7 | Review: **Edit** travel → Low → **Done** → **Start planning** | Review shows Low; Home opens. Q2: the row with `timezone` = your browser's zone and `max_ticket_price_cents` 9000; Q3: Bears, Lions; Q4: four categories on; Q7: `onboarding_completed` |
| W8 | Home | "YOUR NEXT GAMES": one card per team, kickoff like `SUN, NOV 8 · 7:20 PM CT`, venue and city, up to two tags + overflow, "N mi away", and "PLAN THIS GAME · Planning arrives soon" within 30 days or "Planning opens on …" beyond |
| W9 | Make the window ≥ 1024 px wide, then narrow | Left rail ↔ bottom tabs; cards 3 / 2 / 1 per row |
| W10 | **Schedule** | Current week chip selected (selected chip has dark text on orange); games under day headers like `SUNDAY, NOV 8`; tag dots |
| W11 | **All teams** → Bears; pick a week without Bears games | "The Bears have a bye in Week N." → **Next game ›** opens the Bears' next game |
| W12 | Clear the team; **My teams** on | Only Bears and Lions games |
| W13 | Open a primetime division game (Q5 lists tags by week) | Black field-line hero: `WEEK N · SUNDAY NIGHT`, matchup, kickoff with zone, venue · city · distance, tag chips |
| W14 | Tap a tag | Sheet with a one-sentence explanation; featured rivalries show their reason |
| W15 | Open a game more than 30 days out (Week 18) | "Planning opens on <date>." in place of the plan button; the kickoff shows `TIME TBD` if not set (AC-47) |
| W16 | **About this game** | Week and stage, venue, each tag explained, `API-Sports · schedule updated N min ago`; tap it for the exact time with zone (FR-SC4). Matches Q6 `ended_at` |
| W17 | Open the Madrid or Munich game | `INTERNATIONAL GAME` (text-only chip); "Outside your travel area (Low)" |
| W18 | Settings → Favorite teams: deselect both | "Keep at least one team."; **Save** disabled. Remove only Lions → saved; Home updates (AC-2) |
| W19 | Settings → Email level Low | Reminders and Weekly digest switch off and show "Not sent at the low level"; Q4 unchanged for stored choices, Q2 `notification_level = low` |
| W20 | Settings → Time zone → Pacific | Kickoffs show PT; Q2 `timezone = America/Los_Angeles` |
| W21 | Stop the API; pull to refresh on Home | Cards stay; "You're offline. Showing saved data." Restart the API, pull again: banner gone |
| W22 | Settings → **Delete account**, type `DELETE`, confirm | Back to sign-in; Q9: no rows in `app.users` or `auth.users` for that email; signing in fails |

## Manual tests: phone (Expo Go; repeat on iOS and Android)

| # | Do | Expect |
|---|---|---|
| P1 | Sign in with a verified account that hasn't onboarded | Onboarding |
| P2 | Step 2 **Use my location**, allow | The permission prompt appears only now; the nearest ZIP and city fill in. After saving, Q2 has only the ZIP |
| P3 | Finish onboarding | Home; bottom tabs Home, Schedule, Plan, My Game Days; bell and gear top right |
| P4 | Plan, My Game Days, bell | Empty states ("Planning arrives soon", "Your saved plans and alerts will show here", "No alerts yet") |
| P5 | Schedule → swipe the week chips, open a game, Back | Same content as web; back to the same week |
| P6 | Switch the phone between light and dark mode | No change (NFR-5); kickoffs show the zone |
| P7 | System text size to the maximum | Cards grow; no clipped text |
| P8 | Airplane mode, pull to refresh | Cached games with the offline banner |
| P9 | Run the Maestro flow (Automated checks) with a fresh, verified account | Passes |

If "Use my location" never prompts in Expo Go, check the app's location permission in the phone's settings.

## API checks

With the API running, an onboarded, verified account, and `API`/`TOKEN` from M0's A4:

| # | Command | Expect |
|---|---|---|
| A1 | `curl -s $API/teams -H "Authorization: Bearer $TOKEN" \| python3 -m json.tool \| head -20` | 32 teams with conference and division |
| A2 | `curl -s $API/season -H "Authorization: Bearer $TOKEN"` | `"year":2026`, `"schedule_available":true`, a `current_week`, `schedule_updated_at` |
| A3 | `curl -s "$API/games?week=5&team=CHI" -H "Authorization: Bearer $TOKEN"` | One game (or none in a bye week) |
| A4 | `curl -s "$API/games?favorites=true&limit=2" -H "Authorization: Bearer $TOKEN"` | Two items and a `next_cursor`; passing `&cursor=<it>` returns the next two |
| A5 | `curl -s $API/games/<id> -H "Authorization: Bearer $TOKEN"` | `tags`, `distance_mi`, `planning` (`opens_at` in UTC with `Z`), `source.schedule_updated_at`, `travel_hint` |
| A6 | `curl -s $API/zip/60601 -H "Authorization: Bearer $TOKEN"` | `{"zip":"60601","place_name":"Chicago","state":"IL"}` |
| A7 | `curl -s -X POST $API/zip/nearest -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"lat":41.886,"lng":-87.62}'` | `60601`, Chicago; the API's log has no coordinates |
| A8 | `PUT /me/preferences` with `"favorite_team_ids":[]`, then with an extra `"party_size":2` | `422` both times (AC-2, AC-1) |
| A9 | `for i in $(seq 61); do curl -s -o /dev/null -w "%{http_code}\n" $API/teams -H "Authorization: Bearer $TOKEN"; done \| sort \| uniq -c` | At most 60 × `200` in a minute, then `429` with `Retry-After` |
| A10 | `cd backend && PROVIDER_APISPORTS_ENABLED=false uv run python -m app.cli sync-schedule` | "Schedule sync failed … error ProviderDisabled"; Q6 shows the failed run; browsing still works |

A1–A10 were run against the local stack on 2026-10-29 (A9 returned 429 after 43 calls because that account had already made 17 requests that minute).

## Database checks

App tables are readable only by the backend role, so connect as the role that owns them:

```bash
PW=$(grep '^DATABASE_URL=' .env | sed -E 's#.*gamedaygo_app:([^@]+)@.*#\1#')
APPSQL() { docker exec -i -e PGPASSWORD="$PW" supabase_db_gameday-go psql -h 127.0.0.1 -U gamedaygo_app -d postgres -c "$1"; }
```

**Q1. Reference data** (expect 32 teams, 33,780 ZIPs, 32,130 places, 10 rivalries, 0 teams without coordinates):
```bash
APPSQL "select (select count(*) from app.teams) teams, (select count(*) from app.zip_centroids) zips,
        (select count(*) from app.place_centroids) places, (select count(*) from app.featured_rivalries) rivalries,
        (select count(*) from app.teams where home_venue_lat is null) teams_without_coords;"
```

**Q2. Preferences**
```bash
APPSQL "select u.email, u.timezone, p.home_zip, p.travel, p.spending, p.max_ticket_price_cents, p.viewing, p.notification_level
        from app.users u join app.user_preferences p on p.user_id = u.id order by p.updated_at desc limit 5;"
```

**Q3. Favorite teams**
```bash
APPSQL "select u.email, string_agg(f.team_id, ', ' order by f.team_id) teams
        from app.user_favorite_teams f join app.users u on u.id = f.user_id group by u.email;"
```

**Q4. Notification settings**
```bash
APPSQL "select u.email, n.category, n.email_enabled from app.notification_settings n
        join app.users u on u.id = n.user_id order by u.email, n.category;"
```

**Q5. Games and tags for a week** (change the week)
```bash
APPSQL "select g.away_team_id || ' @ ' || g.home_team_id matchup, g.kickoff_at, g.kickoff_tbd, g.venue_city, g.status,
               string_agg(t.tag, ',' order by t.tag) tags
        from app.games g left join app.game_tags t on t.game_id = g.id
        where g.season = 2026 and g.week = 9 group by g.id order by g.sort_at;"
```

**Q6. Sync runs, changes, seasons**
```bash
APPSQL "select kind, season, status, records, changes, error, started_at, ended_at from app.sync_runs order by started_at desc limit 5;"
APPSQL "select g.away_team_id || ' @ ' || g.home_team_id matchup, c.field, c.old_value, c.new_value, c.detected_at
        from app.game_changes c join app.games g on g.id = c.game_id order by c.detected_at desc limit 10;"
APPSQL "select year, status, schedule_available_at, super_bowl_game_id from app.seasons order by year;"
```

**Q7. Onboarding time (SM1)**
```bash
APPSQL "with s as (select user_id, min(client_ts) started from app.app_events where name = 'onboarding_started' group by user_id),
             c as (select user_id, min(client_ts) done from app.app_events where name = 'onboarding_completed' group by user_id)
        select percentile_cont(0.5) within group (order by extract(epoch from done - started)) median_s,
               percentile_cont(0.9) within group (order by extract(epoch from done - started)) p90_s, count(*) users
        from s join c using (user_id);"
```

**Q8. API-Sports budget**
```bash
APPSQL "select provider, day, daily_limit, used, reserved, daily_limit - reserved - used remaining
        from app.provider_budgets order by day desc;"
```

**Q9. After account deletion** (replace the email; expect 0 and 0)
```bash
APPSQL "select count(*) from app.users where email = 'deleted@example.com';"
docker exec -i supabase_db_gameday-go psql -U postgres -c "select count(*) from auth.users where email = 'deleted@example.com';"
```

**Q10. Venue cities without coordinates** (expect none; otherwise add them to `reference_overrides.toml` and re-run `sync-schedule`)
```bash
APPSQL "select name, city, state, country, source from app.venues_ref where lat is null;"
```

## Exit checklist

- [x] T4 resolved: Pro plan, contract fixtures recorded, TDD markers updated
- [x] Automated checks pass locally: TypeScript (lint, typecheck, 118 tests), format, backend (ruff, mypy, 164 tests), `pytest -m supabase` (9), web export build, mobile config check
- [x] Migration round trip (up, down, up) and `alembic check` clean
- [x] `pnpm api:generate` run; client committed-ready
- [x] Live seed and sync: 32 teams, 278 games (272 regular season + 6 playoff slots), tags as expected (Q1, Q5, Q6)
- [x] API checks A1–A10 against the local stack, including live account deletion (Q9)
- [x] Playwright onboard → browse → delete flow passes (phone and desktop viewports)
- [ ] Manual web tests W1–W22
- [ ] Manual phone tests P1–P9 on iOS
- [ ] Manual phone tests P1–P9 on Android
- [ ] Maestro flow passes on a simulator or device
- [ ] AC-1, AC-2, AC-47 confirmed by hand (automated tests pass); AC-49 covered by tests only
- [ ] CI green on GitHub
