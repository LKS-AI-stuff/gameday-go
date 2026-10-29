# GameDay Go — Technical Design Document

| | |
|---|---|
| **Product** | GameDay Go |
| **Document type** | Technical Design Document (TDD) |
| **Version** | 0.8 (draft) |
| **Date** | 2026-10-27 |
| **Implements** | `.claude/docs/business-requirements.md` v0.16 (the BRD) |
| **Audience** | Engineers, AI coding agents, reviewers |

This document describes **how** GameDay Go is built. Requirement IDs (FR-, BR-, AG-, NFR-, AC-) refer to the BRD, which stays the source of truth for behavior. Items marked **[verify]** are details that must be confirmed against provider documentation or real responses during the milestone that integrates them. Do not hard-code them before then.

---

## 1. Design Goals

1. **Runs fully locally through M5** (NFR-20). Docker, the Supabase CLI and live provider keys are all that's needed.
2. **Hard rules in deterministic code** (AG-3). The LLM explains and chooses tools; it never decides budget, travel, authorization or alert eligibility.
3. **Few moving parts.** Two backend processes (API and worker), one database, no cache server or queue broker.
4. **Quota-aware by construction.** Every external call goes through one budgeted, rate-limited, redacting HTTP layer.
5. **Testable.** Business rules are pure functions. Providers sit behind interfaces with fixture mocks. The agent has a scenario evaluation suite.
6. **Shared client code.** Two thin Expo app shells over shared packages.

## 2. System Overview

### 2.1 Context

```mermaid
flowchart LR
  subgraph Clients
    M[apps/mobile<br/>Expo iOS/Android]
    W[apps/web<br/>Expo Web]
  end
  subgraph Backend["Backend (Python)"]
    API[API process<br/>FastAPI + LangGraph agent]
    WK[Worker process<br/>APScheduler jobs]
  end
  DB[(PostgreSQL<br/>Supabase)]
  AUTH[Supabase Auth]
  subgraph External
    AS[API-Sports]
    TM[Ticketmaster Discovery]
    GP[Google Places]
    OAI[OpenAI]
    RS[Resend]
  end
  M -- HTTPS JSON / SSE --> API
  W -- HTTPS JSON / SSE --> API
  M -- sign-in --> AUTH
  W -- sign-in --> AUTH
  API --> DB
  WK --> DB
  API -- verify JWT (JWKS) --> AUTH
  API --> TM & GP & OAI
  WK --> AS & TM & RS
```

- **Clients** talk to Supabase Auth only to sign in and refresh sessions. All application data goes through the FastAPI backend.
- The **API process** serves REST endpoints, runs agent sessions (streamed over SSE) and, in M6, serves the Expo web static build.
- The **worker process** runs scheduled jobs: schedule and standings sync, score polling, Watch checks, reminder emails, the email outbox and cleanup.
- **PostgreSQL** is the only stateful store. It holds app data, LangGraph checkpoints, provider cache, request budgets and job history.

### 2.2 Process responsibilities

| Concern | API process | Worker process |
|---|---|---|
| REST + SSE endpoints | ✅ | |
| Agent runs (bounded at 45 s) | ✅ | |
| Ticket/venue lookups for the agent | ✅ | |
| Schedule, standings sync | manual trigger via CLI only | ✅ daily |
| Score polling / replay | | ✅ |
| Watch checks, expiry | | ✅ |
| Email dispatch (outbox) | | ✅ |
| Retention cleanup | | ✅ |

Both processes share one codebase (`backend/app`) and differ only in entry point.

## 3. Repository Structure

```text
gameday-go/
├── apps/
│   ├── mobile/                 # Expo app (iOS/Android); Expo Router routes + native config
│   │   ├── app/                # Route files: thin wrappers that render screens from packages/ui
│   │   ├── app.config.ts
│   │   └── eas.json            # EAS build profiles (used from M6)
│   └── web/                    # Expo app (web target); Expo Router routes + web config
│       ├── app/
│       └── app.config.ts
├── packages/
│   ├── shared/                 # Zod form schemas, constants, formatting (time zones, money), tag labels
│   ├── api-client/             # Generated OpenAPI types + typed fetch client + SSE helper + TanStack Query hooks
│   ├── ui/                     # Shared screens, components, design tokens, theme
│   └── config/                 # Shared tsconfig / eslint / prettier presets
├── backend/
│   ├── app/
│   │   ├── main_api.py         # FastAPI app factory (API entry point)
│   │   ├── main_worker.py      # Worker entry point (APScheduler)
│   │   ├── cli.py              # Operator commands (sync, record game, seed, budgets report)
│   │   ├── core/               # settings, logging, auth, errors, http client, budgets, redaction
│   │   ├── db/                 # SQLAlchemy models, session, repositories
│   │   ├── domain/             # Pure business rules (no I/O)
│   │   ├── providers/          # Adapters: apisports, ticketmaster, places, openai, resend (+ mocks)
│   │   ├── modules/            # Feature modules: router + service per area (see §5.2)
│   │   ├── agent/              # LangGraph graph, state, tools, prompts, grounding validator
│   │   ├── jobs/               # Worker job functions
│   │   └── email/              # Templates (Jinja2) and rendering
│   ├── migrations/             # Alembic
│   ├── data/                   # reference_overrides.toml, rivalries.toml (stdlib tomllib), zip_centroids.csv, place_centroids.csv, replays/*.json
│   ├── tests/                  # unit/, integration/, contract/, agent_eval/
│   ├── pyproject.toml
│   └── Dockerfile
├── supabase/                   # Supabase CLI project (config.toml) for the local stack
├── .claude/
│   ├── docs/                   # BRD, this TDD, UI/UX design
│   ├── requirements/           # Requirements per milestone (m<N>-*.md) and later features
│   ├── technical-designs/      # Designs generated from requirements; implemented ones hold test guides
│   ├── skills/                 # generate-technical-design, implement-technical-design
│   ├── hooks/                  # Secret-write guard (PreToolUse), stale-backend killer (Stop)
│   └── settings.json           # Registers the hooks
├── .github/workflows/ci.yml
├── turbo.json
├── pnpm-workspace.yaml
├── .env.example
└── README.md
```

**`packages/ui` (decided, T1).** Created in M0 for shared screens, components and design tokens, because two Expo app shells would otherwise duplicate nearly every screen. The app shells contain only routes, configuration and platform-specific code.

### 3.1 Workspace packages (not published to npm)

The folders under `packages/` are **internal pnpm workspace packages**. They are never published to the npm registry.

- Each has a `package.json` with a scoped name (`@gamedaygo/ui`, `@gamedaygo/shared`, `@gamedaygo/api-client`, `@gamedaygo/config`) and `"private": true`, which also blocks accidental publishing.
- Apps depend on them with the workspace protocol, e.g. `"@gamedaygo/ui": "workspace:*"`. pnpm links them locally, and they're imported like normal packages (`import { GameCard } from "@gamedaygo/ui"`).
- They're consumed **as TypeScript source**, with no separate build or versioning step. Metro (Expo's bundler) and TypeScript resolve them directly, so a change in `packages/ui` hot-reloads in both apps immediately.
- Turborepo uses the dependency graph between packages to run `lint`, `typecheck` and `test` in the right order and cache results.
- The Python backend is not part of the pnpm workspace. It's a separate `uv` project in `backend/`. The only link is the OpenAPI schema it exports, which generates `packages/api-client`.

## 4. Frontend Design

### 4.1 Technology

| Concern | Choice |
|---|---|
| Framework | Expo SDK 58 (pinned in both apps) with React Native and React Native Web |
| Routing | Expo Router (file-based) in each app; route files render screens from `packages/ui` |
| Server state | TanStack Query (all backend data); query keys and hooks live in `packages/api-client` |
| Client state | Zustand only for cross-screen UI state (e.g. active agent session draft, onboarding progress) |
| Forms | React Hook Form + Zod resolvers (schemas in `packages/shared`) |
| UI components | **React Native Paper** (Material Design 3) themed with GameDay Go tokens, plus React Native's built-in core components (`View`, `Text`, `Pressable`, `ScrollView`, `Image`) for custom components. No additional headless/primitive UI library. Icons: `@expo/vector-icons` (MaterialCommunityIcons, Paper's default) |
| Styling | `StyleSheet` + design tokens (colors, spacing, typography, radii) feeding both custom components and the Paper theme; one dark theme on every platform (NFR-5); apps set `userInterfaceStyle: "dark"`. Details in §4.4 |
| Motion | `react-native-reanimated` (entering/layout animations), honoring the OS reduce-motion setting |
| Fonts | Oswald (headings) and Open Sans (body) bundled via `@expo-google-fonts/*` and `expo-font` (SIL Open Font License; no runtime call to Google Fonts) |
| Auth | `@supabase/supabase-js` for auth only. Session storage: `expo-secure-store` on native, `localStorage` on web. From M6, social sign-in on native uses `expo-auth-session` + `expo-web-browser` (OAuth redirect) |
| API types | Generated from the backend OpenAPI schema with `openapi-typescript`; thin typed fetch wrapper |
| Streaming | SSE over `fetch` streaming: `expo/fetch` on native **[verify streaming support in the pinned SDK]**, standard `fetch` on web |
| Local reminders | `expo-notifications` (local scheduling only, no push) |
| Device location | `expo-location`: one-off foreground position for "Use my location" (onboarding ZIP in M1, nearby bars in M2, the planner's location toggle in M3). Permission is requested only when the user taps it; coordinates are used for that request only and never stored (FR-P3, FR-P3a) |
| Date/time | Store and transfer UTC ISO-8601; display with the user's IANA time zone via `Intl` / `date-fns-tz` (NFR-4) |
| Testing | Jest + React Native Testing Library; Playwright (web E2E); Maestro (mobile E2E) |

### 4.2 Screens and navigation

| Route | Screen | Key BRD refs |
|---|---|---|
| `/(auth)/sign-in`, `/(auth)/sign-up` | Email sign-in (social sign-in added in M6); 18+ confirmation | FR-A1–A3 |
| `/onboarding` | Six-step preferences (P1–P6) | FR-P1, AC-1 |
| `/(tabs)/home` | Next games for favorite teams, "Live now", recent finals | FR-SC1, FR-LS4 |
| `/(tabs)/schedule` | Season by week, team filter | FR-SC2 |
| `/games/[id]` | Game detail: kickoff, venue, tags, records, score, "Plan this game", "Watch" | FR-SC3–7, FR-ST4 |
| `/(tabs)/plan` | Agent chat (new or resumed session) | FR-AG1–12 |
| `/plan/[sessionId]/trace/[runId]` | Agent Trace timeline | FR-TR1–6 |
| `/(tabs)/my-game-days` | Saved plans and Alerts (segmented: Plans \| Alerts) | FR-SP1–3, FR-W5–6 |
| `/plans/[id]` | Saved plan detail | FR-SP2–3 |
| `/inbox` | Notification inbox | FR-N1 |
| `/settings` | Preferences, notification level, email categories, account deletion | FR-P2, BR-N9, FR-A4 |

Web gets a wider layout with a side navigation rail. Mobile uses bottom tabs (NFR-2).

### 4.3 Key client behaviors

- **Auth flow.** The client signs in with Supabase and sends `Authorization: Bearer <access_token>` on every API call. On first authenticated call the backend creates the `users` row. If preferences are missing, the client routes to onboarding.
- **Score refresh.** Home and game detail refetch scores from the backend on a configurable interval while focused (`EXPO_PUBLIC_SCORE_REFRESH_SEC`, default 300; TanStack `refetchInterval`), plus on screen focus and app foreground, and support pull-to-refresh (FR-LS11). These requests hit only the backend cache, never API-Sports, so they don't use the provider quota (NFR-8b). A short client interval keeps the score on screen within a few minutes of the backend's latest poll, so it is never more than about an hour old (NFR-8a).
- **Agent streaming.** `POST /agent/sessions/{id}/messages` returns an SSE stream of the events listed in §12 (`run_started`, `trace_step`, `token`, `plan_card`, `proposal`, `clarification`, `limit`, `error`, `done`). The client renders trace steps live and the Plan Card when it arrives.
- **Proposals.** "Save plan" and "Create Watch" from the agent are rendered as buttons. Tapping calls the normal REST endpoint (`POST /plans`, `POST /watches`) with the proposal ID. The agent itself never creates them (FR-AG8).
- **Local reminders (mobile only).** On app start, foreground and after saving, editing or deleting a plan or changing the notification level, the app calls `GET /reminders/upcoming`, which returns reminders only for saved plans with a reminder set, a future kickoff, and a user notification level of Medium or High (BR-N3), so at Low or Off the list is empty and reconciliation cancels everything. It then reconciles scheduled notifications: cancel every GameDay Go-scheduled notification and reschedule from the list, keyed by reminder ID. Each notification's text includes the kickoff time it was scheduled for (FR-N7–N9). Permission is requested on the first save (FR-N8).
- **Sample data.** Any API object with `is_sample: true` renders a "Sample data" badge (AC-13, FR-LS16).
- **Deep links.** Email links point to `https://<web-domain>/games/{id}` etc. The web app handles them directly. In M6, universal links / app links open the mobile app when installed.

### 4.4 Visual design foundation (from the reference template)

The reference in `.claude/docs/Template/` is a Nicepage preview of a "Modern Football Team" template; the page itself loads from nicepage.io. Its look: dark near-black sections, white content cards, an orange-red accent, condensed uppercase headings, full-bleed photos under a dark overlay, a three-card "upcoming matches" row, a standings table, and content that fades and rises in on scroll. GameDay Go adopts the **direction**, not the assets: template images (Freepik/Nicepage) and its logo are not reused, and no team logos are used (A12).

**Color tokens** (one dark theme, NFR-5; template values mapped to roles):

| Token | Value | Template source / use |
|---|---|---|
| `color.primary` | `#F0502A` | Template accent (palette 2). Buttons, active tab, key highlights |
| `color.onPrimary` | `#111111` | Text and icons on primary fills (passes AA at all sizes; white, about 3.3:1, is not used) |
| `color.primaryText` | `#FF7A57` | Primary-colored small text and links |
| `color.hero` | `#000000` | Hero bands, under the field-line pattern |
| `color.background` | `#111111` | Template `#111111` sections; every screen |
| `color.surface` | `#1A1A1A` | Cards and panels (template grey-90 sections) |
| `color.surfaceRaised` | `#262626` | Sheets and raised elements |
| `color.chrome` | `#0B0B0B` | Bottom tabs and app chrome |
| `color.outline` | `#333333` | Decorative borders and dividers only (template grey-80) |
| `color.outlineStrong` | `#767676` | Form-field borders (at least 3:1 on every surface, WCAG 1.4.11) |
| `color.fieldLine` | `#FFFFFF` at 16% | Field-line pattern (yard lines every 40 px, sidelines, hash marks) |
| `color.text` / `color.textMuted` / `color.textSubtle` | `#FFFFFF` / `#B9C1CC` / `#8E96A3` | Body, secondary text, captions (sources, timestamps) |
| `color.info` | `#6690F4` | Template palette 1 (blue), lightened for AA on raised cards: links, info banners |
| `color.live` | `#F1C50E` | Template palette 3 (yellow): "Live now", warnings; dark text on it |
| `color.success` | `#2CCCC4` | Template palette 4 (teal): positive states (alert active, within budget) |
| `color.danger` | `#F26360` | Errors, destructive actions |
| `color.overlay` | `rgba(0,0,0,0.6)` | Sheet and dialog backdrop |
| `color.scrim` | `rgba(0,0,0,0.35)` | Over the background photo (`AppBackground`) |
| `color.panelGlass` | `rgba(17,17,17,0.9)` | Panels over the photo; text on them passes AA even with pure white behind |

**Typography:** Oswald for display and headings (uppercase, like the template), Open Sans for body and UI text. The template's web sizes (3.75–6 rem headings) are scaled for phones:

| Token | Font | Size / line height | Use |
|---|---|---|---|
| `type.display` | Oswald 700, uppercase | 36 / 42 (web 48 / 56) | Hero matchup ("BEARS @ PACKERS") |
| `type.h1` | Oswald 600, uppercase | 28 / 34 | Screen titles |
| `type.h2` | Oswald 500, uppercase | 22 / 28 | Section titles ("UPCOMING GAMES", "LIVE NOW") |
| `type.h3` | Oswald 500 | 18 / 24 | Card titles |
| `type.body` | Open Sans 400 | 16 / 24 | Body |
| `type.label` | Oswald 500, uppercase, +0.5 letter spacing | 14 / 20 | Buttons, chips, date labels (template button style) |
| `type.caption` | Open Sans 400 | 13 / 18 | "Updated 4 min ago", sources |
| `type.score` | Oswald 700, tabular numbers | 32 / 36 | Scores |

All text tokens are checked against WCAG AA on every surface (including a glass panel over pure white), and form-field borders against 3:1, by `packages/ui/src/theme/tokens.test.ts`.

**Background photo:** `AppBackground` (core `ImageBackground`, no extra library) renders, fixed behind every `Screen`, `packages/ui/assets/stadium-night.jpg` (852 × 1846, about 140 KB) when the window is taller than wide and `stadium-night-wide.jpg` (1672 × 941, about 160 KB) otherwise, chosen with `useWindowDimensions` so it switches on resize or rotation, with `color.scrim` over it. Text that isn't in the dark top area goes on a `Panel` with `variant="glass"` (UI/UX §4).

**Shape and spacing:** the template uses square corners, so Paper `roundness` is set to 2 (near-square cards and buttons). Spacing scale: 4, 8, 12, 16, 24, 32, 48. Cards use 16 px padding on mobile, 24 px on web.

**Motion** (template: content fades and rises in over 2 s on scroll; too slow for an app):
- Entering content: fade in + rise 12 px, 300 ms, ease-out; list items staggered by 50 ms; only on first mount, never on refetch.
- Score change: a 600 ms highlight pulse on the changed number.
- Agent trace steps: each new step slides in (200 ms) as it streams.
- Reduce motion: when the OS setting is on, all of the above are disabled (Reanimated `useReducedMotion`).

**Template sections mapped to GameDay Go components:**

| Template element | GameDay Go component | Built with |
|---|---|---|
| Hero (full-bleed photo, dark overlay, huge uppercase title) | `Hero` band (black with the `FieldLines` pattern) on game detail as `MatchupHero`, and as the header of the auth screens; matchup in `type.display`, kickoff, venue, tags | Core primitives + tokens |
| "Upcoming matches" cards (date / Team vs Team / venue / Kickoff time) | `GameCard` in Home and Schedule: date label, matchup with records, venue, kickoff in user time zone, tags, planning status | Paper `Card` + primitives |
| Orange-red highlighted block | `PlanCard` recommended option, primary call to action | Paper `Card`, `Button` |
| Standings table (pos, team, W, L, T, PCT, PF, PA…) | `RecordBadge` (W–L–T) and division rank on game detail; no full standings screen (BRD future roadmap) | Paper `Chip` / primitives |
| Social/contact strip, player cards | Not used | — |

**Paper components used:** `Appbar`, `Card`, `Button`, `IconButton`, `Chip` (tags, filters), `SegmentedButtons` (Low/Medium/High, Less/Medium/More in onboarding), `TextInput`, `List.Item`, `Banner` ("Sample data", "Scores paused"), `Snackbar`, `Dialog` (confirmations, account deletion), `ActivityIndicator`, `ProgressBar`, `Divider`, `Badge` (inbox count). Tab bars use Expo Router tabs styled with the tokens.

**Custom components** (core primitives + tokens): `AppBackground`, `Hero`, `FieldLines`, `Panel`, `GameCard`, `MatchupHero`, `ScoreStrip`, `RecordBadge`, `TagChip`, `PlanCard`, `TraceTimeline`, `ChatComposer` (with turns-remaining hint), `PlanningWindowNotice`, `SampleDataBadge`.

Screen-by-screen layouts, component specs and all loading, empty and error states are in `.claude/docs/ui-ux-design.md`.

## 5. Backend Design

### 5.1 Technology

| Concern | Choice |
|---|---|
| Runtime | Python 3.12, dependencies managed with `uv` |
| Web | FastAPI, Pydantic v2, `pydantic-settings` |
| DB access | SQLAlchemy 2.0 (async) + `asyncpg`; Alembic migrations |
| HTTP client | `httpx` (async) wrapped by `core/http.py` (timeouts, retries via `tenacity`, budget, rate limit, redaction) |
| Token verification | `PyJWT` (with `cryptography`) for Supabase access tokens, JWKS or shared secret (§6) |
| Agent | `langgraph`, `langchain-openai`, `langgraph-checkpoint-postgres` (`AsyncPostgresSaver`; uses `psycopg` 3, a second driver alongside `asyncpg`, on its own small pool with `search_path=app`) |
| Scheduler | APScheduler 3.x `AsyncIOScheduler`, jobs defined in code, in-memory job store; run history in Postgres |
| Logging | `structlog` JSON logs with request/run/job IDs and a redaction processor |
| Email | Resend Python SDK or plain HTTPS **[verify idempotency-key support]**; Jinja2 templates |
| API rate limiting | `slowapi` with in-memory storage (single API instance in MVP) |
| Lint/type | `ruff`, `mypy` (strict on `domain/` and `agent/`) |
| Tests | `pytest`, `pytest-asyncio`, Postgres service container, `respx` for HTTP fixtures |

### 5.2 Modules

Each module has `router.py` (HTTP), `service.py` (use cases), `schemas.py` (Pydantic I/O) and uses repositories from `db/`. Modules call each other only through services.

| Module | Responsibility | BRD |
|---|---|---|
| `identity` | Current user, account deletion, age confirmation | 8.1 |
| `preferences` | P1–P6, time zone, notification settings, ZIP lookup | 7.1, 8.2 |
| `schedule` | Teams, games, schedule sync, change detection | 8.3, FR-O1–O2 |
| `scores` | Live state, hourly polling, replay, final confirmation | 8.4 |
| `standings` | Snapshots, record lookups | 8.4.1 |
| `significance` | Tag computation (schedule + record-based) | 7.6 |
| `tickets` | Event matching, price filtering | 8.5 |
| `venues` | Nearby sports bars | 8.6 |
| `recommendations` | Option building and suitability ranking (used by agent tools) | 7.2–7.4 |
| `agent` (router/service) | Sessions, runs, SSE, traces, proposals | 8.7, 8.8, 9 |
| `plans` | Saved plans and refresh | 8.9 |
| `watches` | Watch CRUD and evaluation | 8.10 |
| `notifications` | Inbox, policy, outbox, email, unsubscribe, reminders feed | 7.5, 8.11 |
| `ops` | Health, budgets report, kill switches | 8.12 |

### 5.3 Layering rules

```text
router (HTTP, auth dependency) → service (use case, transactions) → domain (pure rules)
                                         ↘ repositories (SQL)   ↘ providers (external I/O)
```

- `domain/` imports nothing from `db/`, `providers/` or FastAPI. It's pure functions and dataclasses, 100% unit-tested.
- **Every repository method that reads user-owned data takes `user_id` and filters by it** (FR-A5). There are no "get by ID" methods for user-owned rows without `user_id`.
- Services own transactions. One request is one transaction, unless a step calls an external provider; external calls happen outside open transactions.

## 6. Authentication and Authorization

- **Sign-in.** Clients use Supabase Auth with email/password (FR-A1); social sign-in is added in M6 (T11). "Confirm email" is enabled in Supabase, so unverified users never get a session (FR-O11). Locally, verification emails land in the Supabase CLI email catcher.
- **Token verification.** A FastAPI dependency `current_user` verifies the access token's signature, expiry, issuer and audience. Supabase projects can sign with asymmetric keys (verify against the project's JWKS endpoint) or with a legacy shared secret. The verifier supports both, chosen by `SUPABASE_JWT_MODE`. The local CLI stack signs with an asymmetric ES256 key published at its JWKS endpoint, so the default is `jwks` **[verify the hosted project in M6]**. JWKS responses are cached in-process and refetched when an unknown key ID appears (key rotation).
- **User provisioning.** `users.id` is the Supabase `sub` (UUID). The row is created on first authenticated request. The 18+ confirmation (FR-A3) is stored in `users.age_confirmed_at`, and the API rejects data endpoints until it's set. Unverified users have no session, so the email sign-up form can't call the API: it passes `age_confirmed: true` in Supabase `signUp` user metadata, and provisioning copies it from the token's `user_metadata` into `age_confirmed_at`. From M6, social sign-in users (no sign-up form) are routed to the Age confirmation screen, which calls `POST /me/age-confirmation`. The confirmation is a self-attestation either way.
- **Authorization.** Every user-owned query filters by `user_id` (§5.3). Agent tools receive the user ID from the run context, never from model arguments.
- **Database exposure.** Supabase runs PostgREST (the "Data API"), which automatically serves REST endpoints for tables in exposed schemas (by default `public`). Requests carrying the publishable (anon) key run as the `anon` role; requests with a user token run as `authenticated`. The anon key ships inside the apps and is public by design, and we never use the Data API, since all data goes through FastAPI. So the direct path is closed with four layers (see §6.1).

### 6.1 Database exposure hardening

| Layer | Measure | Where |
|---|---|---|
| 1. Non-exposed schema | All app tables live in schema **`app`**, which is not in the Data API's exposed schemas. Nothing is created in `public` | Base Alembic migration |
| 2. RLS deny-all | Every table in `app` has row-level security **enabled and forced** with no policies, so roles other than the table owner see zero rows even if the schema were exposed | Each migration that creates a table |
| 3. No grants | `REVOKE ALL ON SCHEMA app FROM anon, authenticated, public;` `REVOKE ALL ON ALL TABLES/SEQUENCES/FUNCTIONS IN SCHEMA app FROM anon, authenticated, public;` and `ALTER DEFAULT PRIVILEGES IN SCHEMA app REVOKE ALL ON TABLES, SEQUENCES, FUNCTIONS FROM anon, authenticated, public;` so future tables are never granted either | Base Alembic migration (and re-asserted in a final "hardening" step of each migration run) |
| 4. Data API off | The Data API is disabled: locally in `supabase/config.toml` (`[api] enabled = false`, plus `auto_expose_new_tables = false`; the Data API then answers 503), and in the hosted project's API settings (M6) **[verify the hosted setting name]**. Supabase Auth is a separate service and is unaffected | Supabase config / project settings |

The backend connects as a dedicated role (`gamedaygo_app`) that owns schema `app`. It is not `anon`, `authenticated` or `service_role`. `cli bootstrap-db` creates the role (password from `DATABASE_URL`) and the schema through an admin connection (`DATABASE_ADMIN_URL`), then removes the role's database-level `CREATE`; Alembic then runs as the role, so it owns every table. Supabase's own `postgres` role is not the owner, so it can't read app tables either. Because the backend role owns the tables, the forced RLS in layer 2 would also apply to it, so each table gets one policy for `gamedaygo_app` only (`USING (true)`); no policy exists for any other role.

**Exposure tests:**

| Test | Runs where | Asserts |
|---|---|---|
| `test_db_hardening.py` (migration-level) | CI (plain Postgres; the test fixture creates `anon`/`authenticated` roles if missing) and locally | After `alembic upgrade head`: no tables exist in `public` created by us; every table in `app` has `relrowsecurity` and `relforcerowsecurity` true; `anon` and `authenticated` have no `USAGE` on schema `app` and no privileges on any table in it (`has_schema_privilege`, `has_table_privilege`); every policy in `app` targets only `gamedaygo_app`. A new table without RLS fails CI |
| `test_data_api_exposure.py` (HTTP, marker `supabase`) | Locally against `supabase start`, and as an M6 smoke test against the hosted project | `GET {SUPABASE_URL}/rest/v1/<table>` for several `app` tables, with (a) the anon key and (b) a signed-in test user's token, never returns data: Data API disabled (expected 404/unavailable) or a permission/unknown-relation error. Also asserts the `Accept-Profile: app` header can't select the schema |

The M6 deployment checklist also includes reviewing Supabase's Security Advisor for the hosted project.
- **Account deletion (FR-A4).** `DELETE /me` deletes all user rows in one transaction (cascades) and, from M3, the LangGraph checkpoints for the user's sessions, then calls the Supabase Auth Admin API with the server-side `SUPABASE_SECRET_KEY` to delete the auth user (a 404 counts as done). If that call fails, the request returns `503 auth_deletion_failed` and the client offers Try again: the retry re-provisions an empty user row, deletes it and repeats the auth call, so it converges without a retry job. Personal data is gone after the first call.

## 7. Data Model

All tables are in schema `app`. Every table has `created_at` / `updated_at` (`timestamptz`). Primary keys are UUIDs unless noted. All timestamps are UTC.

### 7.1 Reference data (seeded from `backend/data/`)

| Table | Key columns | Notes |
|---|---|---|
| `teams` | `id` (API-Sports team `code`, e.g. `KC`), `name` (`Kansas City Chiefs`), `nickname` (`Chiefs`, the name's last word), `city`, `state`, `conference`, `division`, `home_venue_name`, `home_venue_lat`, `home_venue_lng`, `apisports_team_id` (unique), `ticketmaster_attraction_id` (nullable) | Built by `cli seed` from API-Sports `teams` and `standings` (conference, division). The home venue, its coordinates and the state are set by the schedule sync from where each team plays most US home games. `reference_overrides.toml` `[teams.<code>]` can override any field (FR-O1a) |
| `venues_ref` | `id`, `name`, `city`, `state`, `country`, `lat`, `lng`, `source` (`place_centroids` / `override` / `none`); unique (`name`, `city`). API-Sports reports a venue's name and city only, so `reference_overrides.toml` `[venue_cities]` gives each city's state (US) or country and coordinates (abroad) | Every venue seen in the schedule (home, neutral, international). If coordinates can't be resolved, distance is unknown, which means not travel-eligible |
| `featured_rivalries` | `team_a`, `team_b`, `reason` | From `rivalries.toml` (Appendix B). Unique unordered pair (`team_a < team_b`) |
| `zip_centroids` | `zip` (PK, text), `lat`, `lng`, `place_name`, `state` | Census ZCTA gazetteer, about 33k rows (FR-P3). `place_name`/`state` are computed by `cli build-centroids` from the nearest Census place, weighted by the place's land area (the ZCTA file has no city names) and shown as the ZIP confirmation, e.g. "Chicago, IL". "Use my location" in onboarding maps device coordinates to the nearest ZIP centroid (`geo.nearest_zip`) |
| `place_centroids` | `name`, `state`, `lat`, `lng` (composite key name+state) | Census Places gazetteer (public domain), used to place venue cities. City-level accuracy (a few miles) is enough for the 75-mile local-area rule |

### 7.2 Users and preferences

| Table | Key columns |
|---|---|
| `users` | `id` (Supabase sub), `email`, `age_confirmed_at`, `timezone`, `email_disabled_reason` (bounce/complaint) |
| `user_preferences` | `user_id` (PK/FK), `home_zip`, `travel` (`low`/`medium`/`high`), `spending` (`less`/`medium`/`more`), `max_ticket_price_cents` (nullable), `viewing` (`stadium`/`bar`/`home`/`flexible`), `notification_level` (`off`/`low`/`medium`/`high`) |
| `user_favorite_teams` | `user_id`, `team_id` (composite PK) |
| `notification_settings` | `user_id`, `category` (`watch_hit`/`schedule_change`/`reminder`/`digest`), `email_enabled` (composite PK) |

Device coordinates from "use my location" are used per request and never stored (FR-P3, FR-P3a). Only the home ZIP is stored.

### 7.3 Schedule, scores, standings

| Table | Key columns | Notes |
|---|---|---|
| `games` | `id`, `apisports_game_id` (unique), `season`, `week` (1–18 regular; 19–22 Wild Card, Divisional, Conference, Super Bowl), `stage` (`regular`/`playoff`), `home_team_id` (nullable), `away_team_id` (nullable), `home_placeholder`, `away_placeholder` (e.g. "AFC Wild Card winner" while playoff teams are TBD), `game_date` (the provider's calendar date, kept when the time is TBD), `kickoff_at` (nullable when TBD), `kickoff_tbd` (bool), `sort_at` (kickoff, or 23:59 Eastern on the game day while TBD; ordering and cursors), `venue_id` (FK `venues_ref`, for coordinates), `venue_name`, `venue_city`, `venue_state`, `venue_country` (as reported; diffed), `status`, `home_score`, `away_score`, `quarter`, `clock`, `score_updated_at`, `is_sample`, `last_synced_at` | Live state stored on the game row. Replay games have `is_sample = true` |
| `seasons` | `year` (PK), `status` (`upcoming`/`active`/`completed`), `schedule_available_at`, `super_bowl_game_id` (nullable) | Season rollover (FR-O1c) |
| `game_changes` | `id`, `game_id`, `field`, `old_value`, `new_value`, `detected_at`, `sync_run_id` | Audit of sync diffs; drives schedule-change alerts (FR-O2) |
| `game_tags` | `game_id`, `tag`, `weight` (`high`/`medium`/`info`), `source` (`schedule`/`standings`), `detail` (nullable; e.g. the featured-rivalry reason), `computed_at` | Recomputed after schedule sync and standings sync |
| `standings_snapshots` | `id`, `season`, `retrieved_at`, `is_sample` | |
| `standings_entries` | `snapshot_id`, `team_id`, `wins`, `losses`, `ties`, `win_rate`, `division_rank`, `games_behind`, `points_for`, `points_against` (nullable; shown only if the provider supplies them) | |
| `score_recordings` | `id`, `apisports_game_id`, `captured_at`, `payload` (jsonb) | Raw polled payloads when recording (FR-LS15) |

### 7.4 Agent, plans, watches

| Table | Key columns | Notes |
|---|---|---|
| `agent_sessions` | `id`, `user_id`, `title`, `game_id` (nullable), `user_turns` (int), `last_active_at` | LangGraph `thread_id` = session ID |
| `agent_runs` | `id`, `session_id`, `user_id`, `status` (`running`/`completed`/`limited`/`failed`/`cancelled`), `started_at`, `ended_at`, `tool_calls`, `replans`, `input_tokens`, `output_tokens`, `cost_usd_micros`, `limit_hit`, `model`, `prompt_version`, `config_snapshot` (jsonb: ranking weights and constants used) | Totals for FR-TR6, cost caps, reproducible evaluations (§9.1, §11.5) |
| `agent_messages` | `id`, `session_id`, `run_id`, `role` (`user`/`assistant`), `content`, `plan_card` (jsonb, nullable) | User-visible history (FR-AG11) |
| `agent_trace_steps` | `id`, `run_id`, `seq`, `kind` (`plan`/`tool_call`/`tool_result`/`constraint_check`/`replan`/`answer`/`limit`), `label`, `status` (`success`/`empty`/`failed`/`filtered`), `duration_ms`, `detail` (jsonb, redacted) | FR-TR1–5 |
| `agent_proposals` | `id`, `run_id`, `user_id`, `kind` (`save_plan`/`create_watch`), `payload` (jsonb), `status` (`pending`/`accepted`/`declined`/`expired`) | Confirmation gate (FR-AG8) |
| `saved_plans` | `id`, `user_id`, `game_id`, `plan_card` (jsonb snapshot), `source_run_id`, `reminder_hours` (1/3/6/24, default 3; null = reminder off) | FR-SP1–4. Reminders live here only; they are not Watches |
| `watches` | `id`, `user_id`, `game_id`, `type` (`ticket_price`/`ticket_availability`), `threshold_cents`, `keep_active_after_trigger`, `last_alerted_at` (cooldown, BR-N5), `status` (`active`/`paused`/`triggered`/`expired`/`deleted`), `last_checked_at`, `last_result` (jsonb), `consecutive_failures`, `expires_at` (= kickoff) | Partial index on `status='active'` |
| `watch_evaluations` | `id`, `watch_id`, `evaluated_at`, `outcome`, `detail` | Kept 30 days after expiry (NFR-16) |

### 7.5 Notifications and email

| Table | Key columns | Notes |
|---|---|---|
| `notifications` | `id`, `user_id`, `category`, `title`, `body`, `link_path`, `source`, `data_updated_at`, `dedup_key` (unique), `read_at` | Inbox (FR-N1). `dedup_key` enforces BR-N5 |
| `email_outbox` | `id`, `notification_id`, `user_id`, `to_email`, `template`, `payload` (jsonb), `idempotency_key` (unique), `status` (`queued`/`sent`/`failed`/`skipped`), `attempts`, `next_attempt_at`, `provider_message_id`, `skip_reason` | Transactional outbox (FR-N5–N6) |
| `email_unsubscribes` | `user_id`, `category`, `at` | One-click unsubscribe (FR-N3) |

### 7.6 Operations

| Table | Key columns | Notes |
|---|---|---|
| `provider_budgets` | `provider`, `day` (UTC date), `daily_limit`, `used`, `reserved` (composite PK) | Atomic consumption (§8.2) |
| `provider_cache` | `key` (PK), `provider`, `payload` (jsonb), `expires_at` | Within provider terms (FR-T5, FR-V4) |
| `job_runs` | `id`, `job`, `scheduled_for`, `started_at`, `ended_at`, `status`, `detail` | Unique (`job`, `scheduled_for`) for idempotency |
| `sync_runs` | `id`, `kind` (`schedule`/`standings`), `started_at`, `ended_at`, `status`, `records`, `changes`, `error` | |
| `audit_events` | `id`, `user_id`, `action`, `resource`, `outcome`, `at` | Account deletion, Watch creation, plan saves, preference changes |
| `app_events` | `id`, `user_id` (nullable), `name`, `props` (jsonb), `platform` (`ios`/`android`/`web`), `client_ts`, `received_at` | Product metrics for SM1, SM4, SM7 (§15.1). Allowlisted event names only; no third-party analytics; kept 90 days |
| LangGraph tables | checkpoint tables of `langgraph-checkpoint-postgres` | Created by an Alembic migration in schema `app` (copied from the library's setup SQL for the pinned version), never by the library's `setup()`, which would create them in `public` without RLS. They get the same RLS and grants as every other table and must pass `test_db_hardening.py`. Cleanup by session ID |

### 7.7 Retention (NFR-16)

A daily `retention_cleanup` job deletes: agent sessions, messages, runs, traces and checkpoints older than 90 days; notifications, `email_outbox` rows and `audit_events` older than 90 days; Watches and evaluations 30 days after they leave the active/paused states (expired, triggered or deleted); expired `provider_cache` rows; `app_events` older than 90 days; score recordings older than the season (except files committed to the repo). Retention periods are configuration (§13). Account deletion removes all of the user's rows immediately (§6).

## 8. External Provider Layer

### 8.1 Adapter pattern

Each provider has a `Protocol` interface in `providers/<name>/base.py`, a live implementation and a fixture-based mock. A factory picks the implementation from settings. Live is the default locally and in production; mocks are for automated tests and CI only (NFR-21), except score replay (§10.4).

```python
class ScoresProvider(Protocol):
    async def games_for_season(self, season: int) -> list[ProviderGame]: ...
    async def games_on_date(self, day: date) -> list[ProviderGame]: ...
    async def standings(self, season: int) -> list[ProviderStanding]: ...

class TicketsProvider(Protocol):
    async def find_events(self, game: GameRef, window: TimeWindow) -> list[TicketEvent]: ...

class PlacesProvider(Protocol):
    async def sports_bars_near(self, point: LatLng, radius_m: int) -> list[Venue]: ...

class EmailSender(Protocol):
    async def send(self, msg: EmailMessage, idempotency_key: str) -> SendResult: ...
```

Adapters return **normalized domain types** (e.g. `TicketEvent` with `min_price_cents | None`, `currency`, `url`, `retrieved_at`, `provider`). Raw payloads never leave the adapter, except to the score recorder.

### 8.2 Shared HTTP layer (`core/http.py`)

Every outbound call goes through `ProviderClient.request(provider, ...)`, which handles:

1. **Kill switch.** If `PROVIDER_<X>_ENABLED=false`, it raises `ProviderDisabled` immediately (FR-O5).
2. **Daily budget.** In its own short transaction (never inside a service transaction), it creates today's row if missing, then runs `UPDATE app.provider_budgets SET used = used + 1 WHERE provider=$1 AND day=$2 AND used < daily_limit - reserved RETURNING used`. No row returned raises `BudgetExhausted`. Reserved capacity (scores final confirmation) is consumed with a separate `allow_reserved=True` path. Budgets reset by UTC day, which matches API-Sports' 00:00 UTC reset.
3. **Rate limit.** An in-process async token bucket that waits rather than fails. Ticketmaster: 1 request/s per process (two processes give ≤ 2 req/s, FR-T7). API-Sports: `APISPORTS_RATE_PER_MIN` (10) total (CLI in M1, worker from M4). Google Places: per settings.
4. **Timeouts and retries.** 5 s connect / 10 s read timeouts. `tenacity` retries on network errors, 5xx and 429 with exponential backoff (max 3 attempts; 429 honors `Retry-After`). Retries also consume budget.
5. **Redaction.** URLs are logged with query parameters `apikey`, `key` and `api_key` replaced by `***`. Auth headers (`x-apisports-key`, `X-Goog-Api-Key`, `Authorization`) are never logged (FR-T8, FR-O6). A `structlog` processor scrubs the same patterns from any log event as a backstop.
6. **Metrics.** Each call logs provider, endpoint name (not full URL), status, latency, budget used/remaining (FR-O4, FR-O4a).

### 8.3 API-Sports (schedule, scores, standings)

| Item | Design |
|---|---|
| Auth | `x-apisports-key` header; base URL `https://v1.american-football.api-sports.io`; NFL league ID 1 (confirmed T4) |
| Endpoints | Season games (`/games?league=1&season=<YYYY>`: one call, all games, no pagination), teams (`/teams?league=1&season=<YYYY>`), standings (`/standings?league=1&season=<YYYY>`), games by date (`/games?league=1&date=<YYYY-MM-DD>`, M4). Plan and parameter errors come back as HTTP 200 with a non-empty `errors` object |
| Plan and budget | Pro plan: 7,500 requests/day, 300/minute. App budget `APISPORTS_DAILY_BUDGET` 1,000 (a safety cap), 10% reserve. Typical use: schedule 1–2, standings 1, seeding teams 2 (once), hourly score polling (A15). Local budget from M6: 30 (NFR-22) |
| Mapping | `apisports_team_id` → `teams.id`; unmapped teams or games are logged and skipped (FR-LS10, FR-ST2) |
| Mapping | Times come as a UTC `timestamp`; a `time` of `00:00` marks a TBD kickoff and `date` is then the game day. Stages: `Pre Season` (dropped, BR-W3), `Regular Season` (`Week N`), `Post Season` (`Wild Card`, `Divisional Round`, `Conference Championships`, `Super Bowl` → weeks 19–22; `Pro Bowl` dropped). Undecided playoff teams have ID 0. Status codes `NS`, `Q1`–`Q4`, `OT`, `HT`, `FT`, `AOT`, `PST`, `CANC` map to `scheduled`/`in_progress`/`halftime`/`final`/`final_ot`/`postponed`/`cancelled` (`NS`, `FT`, `AOT` seen in T4; the live codes are confirmed in M4) |
| Contract tests | Recorded real responses (sanitized) in `tests/contract/fixtures/apisports/` |

### 8.4 Ticketmaster Discovery (tickets)

| Item | Design |
|---|---|
| Endpoint | `GET https://app.ticketmaster.com/discovery/v2/events.json` with `apikey`, `attractionId` (home and away team IDs where known) or `keyword`, `classificationName=Football`, `startDateTime`/`endDateTime` = kickoff ± 12 h, `countryCode=US`, `size ≤ 50` (page depth ≪ 1,000) **[verify parameters]** |
| Matching | An event matches a game when the date is within the window, the venue city equals the game's city and both team names appear in the event name or attractions. Events whose name or classification marks them as add-ons (parking, hospitality, suites, tailgate; configurable keyword list `TICKET_EXCLUDE_KEYWORDS`) are dropped first, since they share the game's time and teams. Zero matches give `no_event`; more than one match picks the closest kickoff and logs the ambiguity |
| Normalization | `priceRanges` (if present): min/max and currency go to `min_price_cents`/`max_price_cents`. Missing gives `price_available=false` (BR-S5). Labeled "listed price range" (BR-S6) |
| Budget | 4,000/day shared by API lookups and Watch checks (FR-T7). Cache TTL 10 min (configurable, within terms **[verify V4]**) |
| Budget filter | `tickets.service.filter_by_budget()` drops events with `min_price_cents > max_ticket_price_cents` **before** results reach the agent or UI (FR-T3, AC-8) |

### 8.5 Google Places (venues)

| Item | Design |
|---|---|
| Endpoint | Places API (New) Text Search (`POST https://places.googleapis.com/v1/places:searchText`) with `textQuery: "sports bar"` and a circle `locationRestriction` (default radius 8 km, widened once to 16 km by the agent, FR-AG5) **[verify; compare with Nearby Search using `includedTypes`]** |
| Field mask | `places.id,places.displayName,places.formattedAddress,places.location,places.regularOpeningHours,places.rating,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.utcOffsetMinutes` (`utcOffsetMinutes` is needed to compare local opening hours with kickoff). Hours, rating, phone and website are Enterprise-tier fields, which have the smallest free allowance (about 1,000 calls/month), so the final mask is chosen in M2 against the cost table (FR-V6) **[verify V5]** |
| Derived fields | Distance (haversine from search point); `open_at_kickoff` = true/false/unknown computed from `regularOpeningHours` in the venue's local time |
| Caching | Place IDs may be stored; other content is cached only as long as terms allow (default 1 h TTL in `provider_cache`) **[verify V5]**. Attribution shown in UI (NFR-19) |
| Caps | App daily cap (default 30 requests, about 900/month, inside the Enterprise free allowance) plus a Google Cloud console quota |

### 8.6 OpenAI (agent)

- `langchain-openai` `ChatOpenAI` with model name from `OPENAI_MODEL`. The model is chosen in M3 by running the evaluation suite on two or three candidate models: it must support tool calling and structured output, with the lowest cost that passes the suite (V6).
- Token usage from responses is converted to cost with a configurable price table (`OPENAI_PRICE_INPUT_PER_MTOK`, `..._OUTPUT_...`) and recorded in `agent_runs`.
- A project-level monthly budget is set in the OpenAI dashboard (A16). The app enforces per-run and, from M6, per-day caps (FR-O9).

### 8.7 Resend (email)

- **Sending.** `EmailSender.send()` with `from = EMAIL_FROM`, an HTML and a text part, and an idempotency key = `email_outbox.idempotency_key` (provider idempotency header if supported **[verify]**; the outbox's unique key and status check prevent duplicates regardless).
- **Non-production allowlist (NFR-23).** If `APP_ENV != production` and the recipient isn't in `EMAIL_ALLOWLIST`, the message is marked `skipped` with reason `not_allowlisted` and logged.
- **Modes.** `EMAIL_MODE=resend` (default, including locally) or `log` (render and log only).
- **Test sender (M5).** Until the domain is verified, `EMAIL_FROM` uses Resend's shared test sender, which only delivers to the Resend account owner's address **[verify V7]**.
- **Bounces and complaints (FR-N6).** `POST /webhooks/resend` verifies the webhook signature and sets `users.email_disabled_reason`. This needs a public URL, so it's exercised in M6. Locally, it's tested with signed fixture payloads.

## 9. Domain Rules (`backend/app/domain/`)

All functions are pure, typed and unit-tested with boundary cases (AC-26).

| Module | Functions | BRD |
|---|---|---|
| `geo.py` | `haversine_miles(a, b)`; `is_local(home, venue, local_miles=75)` (unknown venue → `None`, never local); `nearest_zip(point, candidates)` (nearest ZIP for "Use my location"; generic over the key, so seed also uses it to give each ZIP its nearest place) | A5, FR-P3 |
| `travel.py` | `travel_eligible(pref, game, distance_mi, tags) -> Eligibility(allowed, reason)`: Low means local only; Medium means local, or any High-weight tag; High means any US game; international is never eligible; unknown distance is never eligible | BR-T1–T5 |
| `budget.py` | `filter_offers(offers, max_cents) -> (kept, excluded)`; `within_budget(offer, max_cents) -> True/False/Unknown`; `estimated_total(offer, party_size)` | BR-S4–S7 |
| `significance.py` | `schedule_tags(games, teams, rivalries, primetime_start_et)` over a whole season (home opener / home finale depend on schedule position; primetime = Thu, Sun or Mon kickoff at or after `PRIMETIME_START_ET` in Eastern time); `record_tags(game, standings, week, cfg)` with the Week ≥ 4 gate, staleness gate and thresholds; `win_rate(w, l, t)`; `has_high_tag(tags)` | 7.6, BR-G1–G6 |
| `suitability.py` | `rank_options(options, prefs, cfg) -> list[RankedOption]`; formula and examples below. Ineligible options are excluded, not just down-ranked | 7.2–7.4, BR-V5 |
| `watches.py` | `evaluate_ticket_watch(watch, event_result, now) -> Outcome(triggered, reason)`; stale data never triggers | FR-W1, BR-N8 |
| `alerts.py` | `cooldown_elapsed(last_alerted_at, now, cooldown) -> bool`; `dedup_key(source, source_id)`; `allowed_by_level(level, category)`; `within_daily_cap(count, cap)` | BR-N1–N11 |
| `polling.py` | `game_windows(games, cfg)` (merging overlaps); `should_poll(now, windows, last_poll_at, interval)`; `resolve_scores_mode(setting, now, windows, interval)` | FR-LS5–LS6, LS13 |
| `season.py` | `active_season(now, seasons, games)`: switches to the next season once the Super Bowl is final or one day after its scheduled date | FR-O1c |
| `planning.py` | `planning_status(kickoff_at, game_date, status, now, window_days=30) -> Open / OpensOn(at) / Closed` (TBD time uses `game_date`; past, final or cancelled games are `Closed`) | FR-SC8 |
| `schedule_diff.py` | `diff_games(stored, incoming) -> list[Change]` | FR-O2 |

**Polling rule.** During a game window, poll when no poll has happened in this window yet or when `now − last_poll_at ≥ SCORES_POLL_INTERVAL_MIN` (default 60). One "games by date" call covers every game in progress. A final confirmation poll runs once after each window ends. Budgets are counted per UTC day because that's when API-Sports resets; a window that crosses midnight UTC (e.g. Sunday Night Football) simply draws its later polls from the next day's budget. At hourly polling a full Sunday uses about 12–15 requests, so the budget is a safety guard rather than a constraint.

### 9.1 Option ranking formula (`suitability.py`)

Priority (decided): **spending = viewing preference > travel distance**. For each eligible option (stadium, best bar, home):

```text
score = 0.4 × V (viewing fit) + 0.4 × S (spending fit) + 0.2 × D (distance fit)      each term in [0, 1]
```

**Eligibility first (excluded options are never ranked):** stadium is excluded when travel rules fail (BR-T1–T4), the event is unavailable, or every listing is above the hard maximum (BR-S4). A bar is excluded when it's known to be closed at kickoff. Home is always eligible.

**V: viewing fit**

| Preference | Stadium | Bar | Home |
|---|---|---|---|
| Stadium | 1.0 | 0.5 | 0.4 |
| Sports bar | 0.4 | 1.0 | 0.6 |
| Home | 0.3 | 0.5 | 1.0 |
| Flexible | 0.8 | 0.8 | 0.8 |

**S: spending fit**
- Stadium: comfort price `C` = $75 (Less), $150 (Medium), $300 (More), capped at the hard maximum if one is set. With `p` = listed minimum price: `S = 1` if `p ≤ C`; `S = 1 − (p − C) / C` if `C < p < 2C`; `S = 0` if `p ≥ 2C`. Price unknown: `S = 0.5` (and labeled, BR-S5).
- Bar: 0.9 (Less), 0.9 (Medium), 0.7 (More).
- Home: 1.0 (Less), 0.75 (Medium), 0.5 (More).

**D: distance fit**
- Stadium: `1 − min(d / R, 1)` with `R` = 75 mi (Low), 400 mi (Medium), 1,200 mi (High).
- Bar: `1 − min(d / 10 mi, 1)`, multiplied by 0.8 when hours at kickoff are unknown.
- Home: 1.0.

**Ties** (scores, rounded to 2 decimals, less than `RANK_TIE_THRESHOLD` = 0.02 apart): prefer the user's viewing preference, then the lower-cost option, then the shorter distance. All weights and constants are configuration, unit-tested, and recorded on each run so evaluation results are reproducible.

**Worked examples** (Appendix A personas):

| Persona and game | Stadium | Bar | Home | Result |
|---|---|---|---|---|
| **Budget Ben** (Low, Less, Bar). Bears home game, stadium 2 mi, tickets from $120; bar 0.8 mi, open | V 0.4, S 0.4 (C=$75), D 0.97 → **0.52** | V 1.0, S 0.9, D 0.92 → **0.94** | V 0.6, S 1.0, D 1.0 → **0.84** | Bar; home as alternative; stadium mentioned as a trade-off |
| **Road-trip Rosa** (High, More, max $250, Stadium). Chiefs at Arrowhead, 185 mi, tickets from $180; bar 1.5 mi | V 1.0, S 1.0 (C=$250), D 0.85 → **0.97** | V 0.5, S 0.7, D 0.85 → **0.65** | V 0.4, S 0.5, D 1.0 → **0.56** | Stadium; offer a ticket Watch |
| **Flexible Fran** (Medium, Medium, Flexible). Cowboys vs Eagles in Arlington, 190 mi (division rivalry → travel eligible), tickets from $210; bar 2 mi, open | V 0.8, S 0.6 (C=$150), D 0.53 → **0.67** | V 0.8, S 0.9, D 0.8 → **0.84** | V 0.8, S 0.75, D 1.0 → **0.82** | Bar narrowly; home and stadium as alternatives with trade-offs |

## 10. Background Jobs (worker)

### 10.1 Scheduler setup

- `main_worker.py` connects to Postgres and takes `pg_try_advisory_lock(<gamedaygo-scheduler>)` on a dedicated connection held for the process lifetime (a session-level lock is released if its connection goes back to a pool). If the lock isn't acquired, it logs and exits (single scheduler guarantee). It then starts `AsyncIOScheduler` with the jobs below.
- Each job execution inserts a `job_runs` row with a unique (`job`, `scheduled_for`). A duplicate insert means "already ran", so the job is skipped (idempotent retries, NFR-10).
- Jobs are short and resumable. Long work is chunked per tick.

### 10.2 Jobs

| Job | Trigger | What it does | BRD |
|---|---|---|---|
| `schedule_sync` | Daily 09:00 UTC + CLI | Resolve the active season (`season.py`; after the Super Bowl, request the next season until it's available), fetch season games, upsert, diff into `game_changes`, recompute schedule tags, raise schedule-change alerts for games in saved plans or active Watches | FR-O1–O2, FR-W2 |
| `standings_sync` | Daily 10:00 UTC + CLI | Fetch standings, store snapshot, recompute record tags | FR-ST1–ST6 |
| `score_tick` | Every 1 min | Resolve scores mode (§10.4). In live mode, poll `games_on_date` when `should_poll` says so (hourly by default), update `games`, do final confirmation after windows end using reserved budget, optionally record payloads | FR-LS5–LS9, LS15 |
| `watch_check` | Every 5 min | Select active ticket Watches whose `last_checked_at` is older than their interval, group by game, one Ticketmaster lookup per game, evaluate each Watch, raise alerts. If the budget is short, stretch the interval (FR-W8) | FR-W8–W11 |
| `watch_expiry` | Every 5 min | Set `expired` for Watches past kickoff | FR-W4 |
| `reminder_emails` | Every 5 min | For saved plans with a reminder due (kickoff − `reminder_hours`) and level ≥ Medium, raise reminder alerts (email + inbox). Dedup key: plan ID + kickoff time, so a moved kickoff gets a new reminder | BR-N3, FR-SP4 |
| `email_dispatch` | Every 30 s | Claim queued outbox rows (`FOR UPDATE SKIP LOCKED`), recheck Watch status and user settings, send, update status; retry with backoff (max 5) | FR-N5–N6, FR-W10 |
| `retention_cleanup` | Daily 08:00 UTC | §7.7 | NFR-16 |
| `weekly_digest` *(C)* | Tue 14:00 UTC | Digest for High-level users | FR-N11 |

### 10.3 Alert pipeline

```mermaid
sequenceDiagram
  participant J as Job (watch_check / schedule_sync / reminder_emails)
  participant P as notifications.policy
  participant DB as Postgres
  participant D as email_dispatch
  participant R as Resend
  J->>P: raise_alert(user, category, subject, dedup_key, data_updated_at)
  P->>DB: Watch hits: SELECT watch FOR UPDATE; skip if cooldown not elapsed (BR-N5)
  P->>P: level allows? category email on? not unsubscribed? daily cap? data fresh?
  P->>DB: INSERT notifications (dedup_key UNIQUE) + INSERT email_outbox + SET watch.last_alerted_at (same tx)
  Note over DB: Duplicate dedup_key means no-op (retry safety, FR-N5)
  D->>DB: claim queued rows (SKIP LOCKED)
  D->>DB: recheck watch status / settings (FR-W10)
  D->>R: send(idempotency_key)
  D->>DB: status = sent / failed / skipped
```

- Inbox rows are always written, even at level Off (BR-N1). Only the outbox row depends on the level, category, unsubscribe and cap checks (BR-N6).
- **Cooldown (BR-N5)** is a rolling window, not a time bucket: a Watch hit is raised only if `now − watches.last_alerted_at ≥ ALERT_COOLDOWN_H`. The check and the `last_alerted_at` update happen in one transaction with the Watch row locked, so concurrent checks can't both alert.
- **`dedup_key`** only makes retries idempotent: the Watch evaluation ID for Watch hits, the change ID for schedule changes, plan ID + kickoff time for reminders.
- The optional LLM-written alert explanation (FR-W9) is off by default. When enabled, it runs in `email_dispatch` with a 5 s timeout and falls back to the template text.

### 10.4 Scores mode and replay

- `SCORES_MODE ∈ {live, replay, auto}`. Settings validation refuses to start the worker or API in production unless the mode is `live` (FR-LS13, AC-46).
- **auto:** at each tick, `live` if a game window is in progress or starts within the next polling interval, otherwise `replay`. This avoids any "which calendar day" time-zone question.
- **Replay (FR-LS14).** Loads `backend/data/replays/<REPLAY_GAME>.json` (an ordered list of `{offset_seconds, status, home_score, away_score, quarter, clock}` plus the teams). It creates or refreshes one `games` row with `is_sample=true`, kickoff = replay start, and advances its state by `elapsed × REPLAY_SPEED` (default 10). It makes no API-Sports score calls (NFR-24). The replay game is excluded from schedule-change alerts, Watches and plans.
- **Recording (FR-LS15).** With `SCORES_RECORD=true`, each live poll stores raw payloads in `score_recordings`. `cli.py export-replay <apisports_game_id>` converts them to a replay file.
- The mode is logged at start-up and on every tick. API responses for sample games include `is_sample: true`, which triggers the UI banner (FR-LS16).

## 11. Agent Design

### 11.1 Execution model

- An agent run executes **in the API process** as an asyncio task, bounded by AG-1 (45 s wall clock, 8 tool calls, 4 replans, per-run cost cap). Results stream to the client over SSE. If the client disconnects, the run continues to completion and the result is persisted, so it can be fetched later.
- **Cancellation (FR-AG12).** `POST /agent/runs/{id}/cancel` sets a flag checked between graph steps. The run ends with status `cancelled` and partial output.
- **Follow-ups (FR-AG7).** LangGraph `AsyncPostgresSaver` checkpoints keyed by `thread_id = session_id` keep conversation state between turns.
- **Session cap (FR-AG13).** `agent_sessions.user_turns` is incremented atomically when a message is accepted. The 21st message is rejected with `409 session_turn_limit`, and the client shows "Start a new plan." Sessions report `turns_remaining` so the composer can warn near the limit.
- **Context policy.** The model sees: the system prompt, the minimal user context, compacted history (earlier user messages and earlier final answers / Plan Card summaries, but **not** earlier raw tool results) and the current turn's tool results. With at most 20 turns this keeps prompts small, and the per-run cost cap (AG-1) still applies to every run.
- **Planning window (FR-SC8).** Planning tools refuse games outside the 30-day window with `outside_planning_window`, which becomes a constraint check in the trace; the agent then explains when planning opens.

### 11.2 State

```python
class PlanState(TypedDict):
    session_id: str
    run_id: str
    user_ctx: UserContext          # teams, travel, spending, max price, viewing, home ZIP (no email, no coordinates)
    messages: Annotated[list[AnyMessage], add_messages]
    goal: Goal | None              # parsed intent: target game(s), party size, overrides
    evidence: Evidence             # normalized tool results keyed by evidence ID
    candidates: list[RankedOption] # from deterministic ranking
    checks: list[ConstraintCheck]  # travel/budget/hours checks for the trace
    counters: RunCounters          # tool_calls, replans, tokens, cost, started_at
    plan_card: PlanCard | None
    proposals: list[ProposalDraft]
    clarification: str | None
```

### 11.3 Graph

```mermaid
flowchart TD
  S([start]) --> L[load_context<br/>deterministic]
  L --> U[understand<br/>LLM: parse goal, need clarification?]
  U -- ambiguous --> Q[ask_clarification] --> E([end turn])
  U -- clear --> PL[plan_and_act<br/>LLM with tools]
  PL -- tool calls --> T[tools<br/>guarded ToolNode]
  T --> PL
  PL -- done gathering --> EV[evaluate<br/>deterministic: rank + checks]
  EV -- insufficient & replans left --> RP[replan hint] --> PL
  EV -- sufficient or out of budget --> C[compose<br/>LLM structured output: PlanCard]
  C --> G[ground_check<br/>deterministic]
  G -- invalid, first time --> C
  G -- ok / stripped --> F[finalize<br/>persist, proposals, stream]
  F --> E
```

- **Guards on every edge.** Before each LLM or tool step, `counters` are checked against limits. A hit routes to `compose` with `limit_hit` set, so the answer is partial with a limitation note (AC-16).
- **`evaluate`** calls `domain.suitability.rank_options` and records `ConstraintCheck`s (e.g. "Travel rule: Low → excluded away game at Lambeau Field, 180 mi"). It also triggers the BRD replan cases (FR-AG5): no tickets or all over budget leads to venue search; no bars open at kickoff leads to a radius widened once, then home.
- **`compose`** uses `with_structured_output(PlanCard)`. The prompt receives only evidence summaries with evidence IDs.
- **`ground_check`** verifies that every price, link, venue, score and time in the Plan Card references an evidence ID from this run with matching values (AG-4). On failure it regenerates once; after that, unverifiable items are removed and a note is added. It also rejects banned claims (regex plus a list: "playoff implications", "must-win", "clinch", etc.) per BR-G1 and AC-10.

### 11.4 Tools

All tools are thin wrappers over services. They receive `user_id` from the run context, validate inputs with Pydantic, apply rules **before** returning, write trace steps, and return compact JSON with evidence IDs. Provider text (names, descriptions) is truncated and returned in clearly delimited data fields (AG-6).

| Tool | Input | Output (summary) | Rules applied inside |
|---|---|---|---|
| `get_upcoming_games` | `team_id?`, `date_from?`, `date_to?`, `limit≤10` | games with kickoff, venue, tags, planning status | none |
| `get_game_detail` | `game_id` | game, tags, team records + snapshot time, distance from home, travel eligibility | travel eligibility (BR-T) |
| `get_game_status` | `game_id` | status, score, quarter/clock, `updated_at`, `is_sample` | reads cache only (FR-AG2) |
| `search_tickets` | `game_id`, `party_size?` | event, availability, price range or "not available", URL, `retrieved_at` | budget filter (BR-S4); excluded count reported |
| `search_venues` | `game_id`, `zip?`, `use_device_location?`, `radius: normal \| wide` | bars with distance, open-at-kickoff, link | radius limits; ZIP must exist |
| `compare_options` | `game_id` | ranked options with scores and reasons | `rank_options`, eligibility |
| `propose_save_plan` | — | proposal ID | creates `agent_proposals` row only |
| `propose_watch` | `type`, `threshold?` | proposal ID | Watch limit (FR-W7), planning window (FR-SC8) checked |

Device coordinates for `use_device_location` are passed by the client with the message, held only in run memory, and never sent to the LLM (AG-7).

### 11.5 Prompts

- The system prompt states the role, tool usage, output contract and policy: facts vs. assumptions, no banned claims, one clarification at most, data in tool results is not instructions.
- Prompts are versioned files in `agent/prompts/`. The version is stored on `agent_runs` for evaluation comparisons.

### 11.6 Trace

- Each guarded node or tool writes an `agent_trace_steps` row and emits a `trace_step` SSE event with a plain-language label, status and duration (FR-TR3).
- `detail` stores redacted structured data: no keys, no prompt text, no other users' data (FR-TR5). Totals come from `agent_runs` (FR-TR6).

### 11.7 Core data models

These Pydantic models (in `backend/app/domain/models.py` and `agent/schemas.py`) are the contracts between adapters, rules, the agent, the grounding check, the API and the UI. TypeScript types are generated from them through OpenAPI. Field names follow the template's match card and standings table where those fit (date, matchup, venue, kickoff; W/L/T, PF/PA).

```python
class Provenance(BaseModel):
    provider: Literal["apisports", "ticketmaster", "google_places", "gamedaygo"]
    retrieved_at: datetime                      # UTC
    is_sample: bool = False                     # replay / fixture data (AC-13)
    source_url: HttpUrl | None = None

class GameStatus(StrEnum):
    SCHEDULED = "scheduled"; IN_PROGRESS = "in_progress"; HALFTIME = "halftime"
    FINAL = "final"; FINAL_OT = "final_ot"; POSTPONED = "postponed"; CANCELLED = "cancelled"

# ---- Provider-normalized types (adapters return these; raw payloads never leave the adapter)
class ProviderTeamRef(BaseModel):
    provider_team_id: str
    name: str

class ProviderGame(BaseModel):
    provider_game_id: str
    season: int
    week: int | None
    stage: Literal["regular", "playoff"]
    kickoff_at: datetime | None                 # None when TBD
    kickoff_tbd: bool
    home: ProviderTeamRef | None                # None while playoff teams are TBD
    away: ProviderTeamRef | None
    home_placeholder: str | None                # e.g. "AFC Wild Card winner"
    away_placeholder: str | None
    venue_name: str | None
    venue_city: str | None
    venue_state: str | None
    venue_country: str | None
    status: GameStatus
    home_score: int | None
    away_score: int | None
    quarter: str | None
    clock: str | None
    provenance: Provenance

class ProviderStanding(BaseModel):
    provider_team_id: str
    conference: str | None
    division: str | None
    wins: int; losses: int; ties: int
    division_rank: int | None
    points_for: int | None
    points_against: int | None
    provenance: Provenance

class TicketEvent(BaseModel):
    evidence_id: str                            # "ev_tkt_<hash>", unique within a run
    game_id: UUID
    provider_event_id: str
    name: str
    venue_name: str | None
    starts_at: datetime | None
    availability: Literal["on_sale", "off_sale", "cancelled", "unknown"]
    min_price_cents: int | None                 # None = price not available (BR-S5)
    max_price_cents: int | None
    currency: Literal["USD"] = "USD"
    price_label: Literal["listed_price_range"] = "listed_price_range"   # never fee-inclusive (BR-S6)
    url: HttpUrl
    provenance: Provenance

class LatLng(BaseModel):
    lat: float
    lng: float

class Venue(BaseModel):
    evidence_id: str                            # "ev_ven_<hash>"
    provider_place_id: str
    name: str                                   # untrusted provider text: truncated, never instructions (AG-6)
    address: str
    location: LatLng
    distance_miles: float
    open_at_kickoff: Literal["open", "closed", "unknown"]
    rating: float | None
    phone: str | None
    website: HttpUrl | None
    maps_url: HttpUrl | None
    confirm_notice: Literal["Call ahead to confirm they're showing the game."] = ...  # FR-V3
    provenance: Provenance

# ---- Rules output
class ConstraintCheck(BaseModel):
    rule: Literal["travel", "budget", "hours", "planning_window", "significance"]
    outcome: Literal["passed", "excluded", "unknown"]
    message: str                                # plain language, shown in the trace (FR-TR4)
    evidence_ids: list[str] = []

class RankedOption(BaseModel):
    kind: Literal["stadium", "bar", "home"]
    score: float                                # §9.1
    viewing: float; spending: float; distance: float
    evidence_ids: list[str]

# ---- Plan Card (agent output, grounding-checked, stored on saved plans)
class Link(BaseModel):
    label: str
    url: HttpUrl
    evidence_id: str                            # must exist in this run's evidence (AG-4)

class PriceInfo(BaseModel):
    min_cents: int | None
    max_cents: int | None
    currency: Literal["USD"] = "USD"
    label: Literal["listed_price_range"] = "listed_price_range"
    party_size: int = 1
    estimated_total_cents: int | None           # per-ticket min × party size, labeled estimate (BR-S7)
    evidence_id: str

class PlanOption(BaseModel):
    kind: Literal["stadium", "bar", "home"]
    headline: str                               # "Watch at Kelly's Pub, 0.8 mi away"
    reasons: conlist(str, min_length=1, max_length=4)
    tradeoffs: conlist(str, max_length=3) = []
    price: PriceInfo | None = None
    distance_miles: float | None = None
    links: list[Link] = []
    evidence_ids: conlist(str, min_length=1)

class Freshness(BaseModel):
    provider: str
    retrieved_at: datetime
    is_sample: bool

class NextStep(BaseModel):
    kind: Literal["save_plan", "create_watch", "none"]
    label: str
    proposal_id: UUID | None = None

class PlanCard(BaseModel):
    schema_version: Literal[1] = 1
    game_id: UUID
    game_summary: str                           # "Bears @ Packers · Sun, Nov 8 · 12:00 PM CT"
    recommended: PlanOption
    alternatives: conlist(PlanOption, max_length=2) = []
    significance_tags: list[str] = []
    team_records: list[str] = []                # "Chiefs 7–1 (as of Tue 6:00 AM)"
    assumptions: list[str] = []
    limitations: list[str] = []                 # "Ticket prices not available", "Run limit reached"
    facts_as_of: list[Freshness]
    next_step: NextStep

# ---- Trace and proposals
class TraceStep(BaseModel):
    seq: int
    kind: Literal["plan", "tool_call", "tool_result", "constraint_check", "replan", "answer", "limit"]
    label: str                                  # "Searched tickets for Bears @ Packers: 0 under $90"
    status: Literal["success", "empty", "failed", "filtered"]
    duration_ms: int
    detail: dict                                # redacted (FR-TR5)

class Proposal(BaseModel):
    id: UUID
    kind: Literal["save_plan", "create_watch"]
    summary: str
    payload: dict
    status: Literal["pending", "accepted", "declined", "expired"]
```

**Grounding check rules (AG-4):** every `Link.url`, `PriceInfo` value and `distance_miles` must match the evidence item it references (distance within 0.1 mi); every `evidence_id` must exist in the run's evidence; `facts_as_of` must list every provider referenced; `team_records` must match the standings snapshot; the kickoff time in `game_summary` must match the game row; banned claims are rejected (BR-G1).

**API view models** (e.g. `GameCardData`: id, kickoff, kickoff_tbd, home/away name, placeholder and record, venue, status, score, tags, `planning.status`/`planning.opens_at`, `is_sample`) are defined per endpoint in `modules/*/schemas.py`.

### 11.8 Evaluation suite (AC-29)

- `tests/agent_eval/` holds at least 20 scenarios: the Appendix A personas plus variants, each with fixed provider fixtures and a persona.
- Deterministic assertions run on the Plan Card and trace: travel and budget compliance, no banned phrases, grounding valid, a clarification asked when expected, an injection fixture ignored (AC-18).
- In CI, a **scripted fake LLM** checks graph wiring and guards without network access. With the real OpenAI model, the suite runs on demand (`pytest -m eval`) and before model or prompt changes. The report shows the violation count (SM3).

## 12. API Design

- Base path `/api/v1`. JSON. Auth is a Bearer token on all routes except health, unsubscribe and webhooks.
- **Errors** use RFC 9457 `application/problem+json` with a stable `code` (e.g. `budget_exhausted`, `provider_disabled`, `watch_limit_reached`, `outside_planning_window`, `session_turn_limit`, `not_found`).
- **Pagination** is cursor-based (`?cursor=&limit=`) for lists.
- **Rate limits (NFR-15):** per user 60 req/min general and 10/min for agent messages; per IP for unauthenticated routes.
- **Client drift.** The OpenAPI schema is exported in CI. `packages/api-client` is regenerated and CI fails on drift.

| Method & path | Purpose | BRD |
|---|---|---|
| `GET /health`, `GET /ready` | Liveness / DB readiness | NFR |
| `GET /me` · `DELETE /me` | Profile (with `onboarded`); account deletion (`503 auth_deletion_failed` if the auth user couldn't be deleted; retry) | FR-A4 |
| `POST /me/age-confirmation` | Record 18+ confirmation | FR-A3 |
| `GET /me/preferences` · `PUT /me/preferences` | P1–P6 | FR-P1–P4 |
| `GET /me/notification-settings` · `PUT ...` | Level + per-category email | BR-N9 |
| `GET /zip/{zip}` · `POST /zip/nearest` | Validate ZIP; nearest ZIP for "Use my location" (coordinates in the body so they never reach URLs or access logs) | FR-P3, FR-P3a |
| `GET /teams` | Teams | FR-SC |
| `GET /games` | Filters: `season`, `team`, `week`, `from`, `to`, `favorites=true`; cursor pagination | FR-SC1–2 |
| `GET /games/live` | In-progress + recent finals for favorites | FR-LS4 |
| `GET /games/{id}` | Detail incl. tags, records, score, distance | FR-SC3–7, FR-ST4 |
| `GET /games/{id}/tickets` | Ticket lookup (budget-filtered) | FR-T1–T4 |
| `GET /venues` | `game_id`, `zip` or `lat`/`lng` | FR-V1–V3 |
| `POST /agent/sessions` · `GET /agent/sessions` · `GET /agent/sessions/{id}` | Sessions and history; responses include `turns_used` / `turns_remaining` | FR-AG1, FR-AG11, FR-AG13 |
| `POST /agent/sessions/{id}/messages` | Send message; **SSE** response | FR-AG3–AG10 |
| `GET /agent/runs/{id}` | Run status and result (Plan Card, proposals); used after a dropped stream and as the SSE fallback | FR-AG10 |
| `POST /agent/runs/{id}/cancel` | Cancel run | FR-AG12 |
| `GET /agent/runs/{id}/trace` | Trace steps + totals | FR-TR |
| `POST /agent/proposals/{id}/decline` | Decline a proposal | FR-AG8 |
| `POST /plans` (`proposal_id` or `game_id` + card) · `GET /plans` · `GET /plans/{id}` · `DELETE /plans/{id}` · `PATCH /plans/{id}` (`reminder_hours`) · `POST /plans/{id}/refresh` | Saved plans | FR-SP |
| `POST /watches` · `GET /watches` · `PATCH /watches/{id}` (pause/resume) · `DELETE /watches/{id}` | Watches | FR-W |
| `GET /notifications` · `POST /notifications/{id}/read` · `POST /notifications/read-all` | Inbox | FR-N1 |
| `GET /reminders/upcoming` | Reminder feed for local scheduling | FR-N7–N9 |
| `GET /season` | Active season, whether its schedule is available, current week, week labels, planning window length, schedule source and last update | FR-O1c, FR-SC8, FR-SC4 |
| `POST /app-events` | Batch of up to 20 allowlisted client events (§15.1) | SM1, SM4 |
| `GET /email/unsubscribe?token=` · `POST /email/unsubscribe?token=` | Public; signed per-category token. GET shows a confirmation page (mail scanners prefetch links, so GET never unsubscribes); POST unsubscribes and is the RFC 8058 one-click target named in the `List-Unsubscribe` / `List-Unsubscribe-Post` headers | FR-N3 |
| `POST /webhooks/resend` | Public; signature-verified | FR-N6 |

**SSE event types** for agent messages: `run_started {run_id}`, `trace_step {...}`, `token {text}`, `plan_card {...}`, `proposal {id, kind, summary}`, `clarification {text}`, `limit {reason}`, `error {code}`, `done {status}`.

## 13. Configuration

Settings are loaded by `pydantic-settings` from environment variables (`.env` locally) and validated at start-up with clear, non-secret error messages. Optional providers are cleanly disabled when their key is missing **only if** their kill switch is off; otherwise start-up fails.

| Variable | Example / default | Notes |
|---|---|---|
| `APP_ENV` | `local` \| `ci` \| `production` | Production guards (below) |
| `PUBLIC_WEB_URL` | `http://localhost:8081` | Email deep links |
| `DATABASE_URL` | `postgresql+asyncpg://gamedaygo_app:<password>@127.0.0.1:54322/postgres` | Backend role; Supabase CLI local port 54322 |
| `DATABASE_ADMIN_URL` | `postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres` | Only for `cli bootstrap-db` (§6.1) |
| `SUPABASE_URL` | `http://localhost:54321` | |
| `SUPABASE_JWT_MODE` | `jwks` \| `secret` | §6 |
| `SUPABASE_JWT_SECRET` | — | Only for `secret` mode |
| `SUPABASE_SECRET_KEY` | — | Server only; account deletion (Auth Admin API) and the Data API exposure test |
| `SUPABASE_PUBLISHABLE_KEY` | — | Only for the Data API exposure test (`pytest -m supabase`) |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | — | |
| `OPENAI_PRICE_INPUT_PER_MTOK`, `OPENAI_PRICE_OUTPUT_PER_MTOK` | — | Cost estimation |
| `AGENT_MAX_TOOL_CALLS` / `AGENT_MAX_REPLANS` / `AGENT_TIMEOUT_S` / `AGENT_MAX_COST_USD` | 8 / 4 / 45 / 0.05 | AG-1, A16 |
| `AGENT_DAILY_RUNS_PER_USER`, `LLM_DAILY_SPEND_CAP_USD` | 15 / 0.65 | FR-O8–O9 (enforced from M6); daily cap × 31 stays within the $20 monthly budget (A16) |
| `APISPORTS_KEY`, `APISPORTS_DAILY_BUDGET`, `APISPORTS_RESERVE_PCT` | — / 1000 / 10 | Pro plan quota is 7,500/day; the budget is the app's safety cap |
| `APISPORTS_BASE_URL`, `APISPORTS_LEAGUE_ID`, `APISPORTS_RATE_PER_MIN` | `https://v1.american-football.api-sports.io` / 1 / 10 | §8.2–8.3 (the plan allows 300/min) |
| `PROVIDER_BUDGET_WARN_PCT` | 80 | FR-O4a |
| `SCORES_MODE`, `SCORES_POLL_INTERVAL_MIN`, `REPLAY_GAME`, `REPLAY_SPEED`, `SCORES_RECORD` | `auto` / 60 / `sample-1` / 10 / false | §9, §10.4 |
| `GAME_WINDOW_LEAD_MIN`, `GAME_WINDOW_MAX_H` | 15 / 4.5 | FR-LS5, A14 |
| `SCHEDULE_SYNC_UTC`, `STANDINGS_SYNC_UTC`, `RETENTION_CLEANUP_UTC` | `09:00` / `10:00` / `08:00` | §10.2 |
| `PLANNING_WINDOW_DAYS`, `AGENT_MAX_TURNS_PER_SESSION` | 30 / 20 | FR-SC8, FR-AG13 |
| `RANK_WEIGHTS`, `COMFORT_PRICE_{LESS,MEDIUM,MORE}`, `TRAVEL_RADIUS_{LOW,MEDIUM,HIGH}_MI`, `BAR_DISTANCE_NORM_MI`, `RANK_TIE_THRESHOLD` | 0.4,0.4,0.2 / 75,150,300 / 75,400,1200 / 10 / 0.02 | §9.1 (the viewing-fit matrix and bar/home spending constants live in a versioned config file) |
| `TICKETMASTER_API_KEY`, `TICKETMASTER_DAILY_BUDGET`, `TICKETMASTER_CACHE_TTL_S` | — / 4000 / 600 | |
| `GOOGLE_PLACES_API_KEY`, `GOOGLE_PLACES_DAILY_CAP` | — / 30 | §8.5 |
| `PLACES_RADIUS_NORMAL_M`, `PLACES_RADIUS_WIDE_M`, `PLACES_CACHE_TTL_S` | 8000 / 16000 / 3600 | §8.5, FR-AG5 |
| `TICKET_MATCH_WINDOW_H`, `TICKET_EXCLUDE_KEYWORDS` | 12 / `parking,hospitality,suite,tailgate` | §8.4 |
| `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_MODE`, `EMAIL_ALLOWLIST`, `RESEND_WEBHOOK_SECRET` | — / test sender / `resend` / your address | |
| `UNSUBSCRIBE_SIGNING_KEY` | — | HMAC for unsubscribe tokens |
| `PROVIDER_{APISPORTS,TICKETMASTER,PLACES,OPENAI,RESEND}_ENABLED` | `true` | Kill switches (FR-O5) |
| `STANDINGS_ENABLED` | `true` | FR-ST8 |
| `LOCAL_AREA_MILES`, `RECORD_TAGS_FROM_WEEK`, `STANDINGS_MAX_AGE_DAYS` | 75 / 4 / 8 | A5, BR-G4–G5 |
| `PRIMETIME_START_ET` | `19:00` | BRD §7.6 primetime tag |
| `WATCH_INTERVAL_MIN`, `ALERT_COOLDOWN_H`, `DAILY_EMAIL_CAP`, `MAX_ACTIVE_WATCHES`, `WATCH_TROUBLE_AFTER_FAILURES` | 30 / 12 / 5 / 10 / 3 | A11, FR-W11 |
| `EMAIL_MAX_ATTEMPTS` | 5 | §10.2 `email_dispatch` |
| `RETENTION_SESSIONS_DAYS`, `RETENTION_NOTIFICATIONS_DAYS`, `RETENTION_WATCHES_DAYS` | 90 / 90 / 30 | NFR-16, §7.7 |
| `RATE_LIMIT_PER_MIN`, `RATE_LIMIT_IP_PER_MIN`, `RATE_LIMIT_AGENT_PER_MIN` | 60 / 60 / 10 | NFR-15, §12; per user, per IP (unauthenticated routes), agent messages |
| `CORS_ORIGINS` | `http://localhost:8081` | Expo web dev origin |

**Client (public by design)**, in `apps/mobile/.env` and `apps/web/.env` (each app has a `.env.example`; Expo reads `.env` from the app folder): `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_ANON_KEY`, `EXPO_PUBLIC_SCORE_REFRESH_SEC` (default 300; how often open score screens reload from the backend cache). These values ship inside the apps: never put a secret in an `EXPO_PUBLIC_*` variable (NFR-12).

**Production guards:** `SCORES_MODE` must be `live`; `EMAIL_ALLOWLIST` is ignored; `EMAIL_FROM` must not be the test sender; debug and docs UI are disabled; all kill-switched-on providers must have keys.

## 14. Security

| Area | Measure | BRD |
|---|---|---|
| Secrets | Server-side only; local `.env` git-ignored; production secrets in Railway variables | NFR-12 |
| Transport | TLS everywhere in M6 (Railway / Supabase); HSTS on the web origin | NFR-13 |
| AuthN/AuthZ | JWT verification on every request; user-scoped repositories | FR-A5, §6 |
| Database exposure | `app` schema, forced RLS, revoked grants and default privileges, Data API disabled; enforced by `test_db_hardening.py` (CI) and `test_data_api_exposure.py` (local + M6 smoke) | §6.1 |
| Input validation | Pydantic on every request; Zod on client forms | NFR-14 |
| Rate limiting | slowapi per user/IP; provider budgets; agent per-user caps | NFR-15, FR-O8–O10 |
| Prompt injection | Rules in code before the model; tool output as delimited data; grounding validator; banned-claim filter; no arbitrary URLs or code tools | AG-2–AG-6, AC-18 |
| Logging | structlog redaction of keys, tokens, emails (hashed) and coordinates | FR-O6 |
| Email | Signed unsubscribe tokens; webhook signature verification; allowlist outside production | FR-N3, NFR-23 |
| CORS | Locally: explicit origins. In M6 the web app is same-origin (served by the API), so CORS stays closed | — |
| Dependencies | `uv lock` / `pnpm-lock.yaml` committed; Dependabot or Renovate in CI | — |

## 15. Observability

- **Logs.** JSON to stdout (Railway captures them in M6). Every log line carries `request_id`, `user_id_hash`, `run_id` or `job` where relevant.
- **Operational data in Postgres:** `provider_budgets`, `job_runs`, `sync_runs`, `agent_runs` (tokens, cost) and `email_outbox` statuses.
- **CLI report.** `cli.py ops-report` prints today's budgets, last sync results, failing Watches, agent cost and email failures (stands in for the FR-O7 dashboard).
- **Warnings** are logged at 80% of any provider budget (FR-O4a) and on any job failure.
- No external error-tracking service in the MVP, to keep dependencies minimal.

### 15.1 Product metrics (`app_events`)

| Metric | Events / source | Calculation |
|---|---|---|
| SM1 onboarding time | Client: `onboarding_started`, `onboarding_completed` | Median and p90 of completed − started per user |
| SM4 plan response time | Server: `agent_runs.started_at/ended_at`; client: `plan_first_step_rendered`, `plan_card_rendered` | p95 run duration; p95 time to first trace step |
| SM7 cost per plan | Server: `agent_runs.cost_usd_micros` | Average per completed run, per day |
| Funnel (informational) | Client: `plan_requested`, `plan_saved`, `watch_created` | Counts per day |

Allowlisted names only, no free-text properties, no device identifiers, no email tracking pixels. `cli.py ops-report` includes these metrics.

## 16. Testing Strategy

| Layer | Tooling | Scope |
|---|---|---|
| Domain unit | pytest | All rules in §9, boundary values (AC-26, AC-42) |
| Database hardening | pytest (CI Postgres) + HTTP test against the Supabase stack (local, M6) | §6.1 exposure tests |
| Service/integration | pytest + Postgres service container + respx fixtures | Repositories, authorization (user A vs. user B, AC-27), budgets, outbox idempotency (AC-23, AC-40), Watch lifecycle races (AC-21) |
| Contract | Recorded, sanitized real responses per provider | Adapter mapping for API-Sports, Ticketmaster, Places, Resend |
| Jobs | pytest with frozen time (`time-machine`) | Polling rule, UTC-midnight window, season rollover, planning window, scores mode switching (AC-46), replay, expiry, reminders |
| Agent | Scripted fake LLM in CI; real model on demand | Graph guards, eval suite (AC-29) |
| Frontend unit | Jest + RNTL | Components, forms, formatting, reminder reconciliation |
| E2E web | Playwright against the local stack | Onboarding → browse → plan → save → Watch → inbox (AC-28) |
| E2E mobile | Maestro on simulator/emulator | Same flow, plus a local reminder fired in a fast-forwarded test configuration |

**CI (GitHub Actions)** runs on every PR:
1. `pnpm install`, Prettier format check, then `turbo lint typecheck test` for all TS packages and apps.
2. `uv sync`, `ruff`, `mypy`, `pytest` (unit, integration, contract, agent with fake LLM) against a Postgres service container.
3. `alembic upgrade head` → `downgrade -1` → `upgrade head` on an empty DB.
4. OpenAPI export plus api-client regeneration with a diff check.
5. `expo export --platform web` build check for `apps/web`, and an Expo config check for `apps/mobile`.

CI uses mocks only: no provider secrets, no quota use (NFR-21).

## 17. Local Development (M0–M5)

**Prerequisites:** Node 22+ with pnpm (via Corepack), uv (installs Python 3.12), Docker, and Expo Go on a phone or Xcode / Android Studio for simulators. The Supabase CLI is a dev dependency of the repo (`pnpm supabase ...`).

```bash
pnpm install
pnpm supabase start                  # local Postgres + Auth + email catcher (prints URLs/keys)
cp .env.example .env                 # backend: pick a DATABASE_URL password, add local Supabase keys
cp apps/web/.env.example apps/web/.env         # client settings (EXPO_PUBLIC_* only)
cp apps/mobile/.env.example apps/mobile/.env   # use the Mac's LAN IP for phones
cd backend && uv sync
uv run python -m app.cli bootstrap-db  # backend role + schema app (once per database)
uv run alembic upgrade head
uv run python -m app.cli seed        # places, ZIP centroids, rivalries, teams (M1; 2 API-Sports requests)
uv run python -m app.cli sync-schedule   # M1 (sync-standings arrives in M4)
uv run uvicorn app.main_api:create_app --factory --reload --host 0.0.0.0   # API on :8000
uv run python -m app.main_worker                            # worker, scores mode auto (M4)
pnpm --filter @gamedaygo/web dev     # Expo web on :8081
pnpm --filter @gamedaygo/mobile dev  # Expo for phones/simulators on :8082
```

- **Phone testing:** in `apps/mobile/.env`, point `EXPO_PUBLIC_API_URL` and `EXPO_PUBLIC_SUPABASE_URL` at the Mac's LAN IP, keep the phone on the same Wi-Fi, and run the API with `--host 0.0.0.0`. Allow incoming connections if macOS asks.
- **Exposure check:** `uv run pytest -m supabase` runs the Data API exposure test against the local stack (§6.1). Run it after changing Supabase config or adding tables.
- **Sign-up emails:** open the Supabase CLI email catcher (Mailpit, URL printed by `pnpm supabase start`). The verification link opens the web app on :8081.
- **API client:** `pnpm api:generate` regenerates `packages/api-client` after backend schema changes (CI fails on drift).
- **Alert emails:** real emails through Resend to the allowlisted address (§8.7).
- **Non-game days:** `SCORES_MODE=auto` switches to replay automatically.
- `turbo dev` can run all TypeScript dev servers together. A `Procfile.dev` / `honcho` can run API + worker together.

## 18. Deployment (M6)

| Component | Target | Details |
|---|---|---|
| API + web | Railway service `api` | Multi-stage Dockerfile: build the Expo web export, then the Python image. FastAPI mounts static files at `/` with SPA fallback and the API under `/api/v1`. Health check `/ready` |
| Worker | Railway service `worker` | Same image, command `python -m app.main_worker`. One replica (advisory lock enforces it anyway) |
| Migrations | Railway pre-deploy command | `alembic upgrade head` on the `api` service |
| Database + Auth | Hosted Supabase project | Production auth email settings, redirect URLs, social provider credentials; `gamedaygo_app` role owning schema `app`; **Data API disabled**; connect through a direct or session-mode connection, not the transaction-mode pooler (the worker's advisory lock and `asyncpg` prepared statements need a session) **[verify IPv4 reachability from Railway]**; run `test_data_api_exposure.py` against the hosted URL and review the Security Advisor before going public |
| Email | Resend | Domain verified (SPF/DKIM), production `EMAIL_FROM`, webhook to `/api/v1/webhooks/resend` |
| Domain | Custom domain on Railway | Also serves `apple-app-site-association` / `assetlinks.json` for deep links into the mobile app |
| Mobile | EAS Build profiles `development`, `preview`, `production`; EAS Submit to TestFlight / Play internal testing | `EXPO_PUBLIC_*` per profile |
| Demo protections | FR-O8–O11 enabled via settings | Per-user agent cap, LLM daily spend cap, provider daily caps |

## 19. Implementation Plan by Milestone

Each milestone's requirements (what must be built, as a checklist citing this document, the BRD and the UI/UX doc) are in `.claude/requirements/`. `/generate-technical-design` turns a requirements file into a technical design in `.claude/technical-designs/`, grounded in the current code; `/implement-technical-design` builds it and records what was implemented and how to test it, including database queries. Feature requirements beyond the milestones follow the same path.

| Milestone | Requirements | Technical design | Status |
|---|---|---|---|
| M0: Foundation | (BRD §13) | `m0-foundation.md` | Code complete; CI green; exit pending manual tests on web, iOS and Android |
| M1: Preferences and schedule | `m1-preferences-and-schedule.md` | `m1-preferences-and-schedule.md` | Code complete; exit pending manual tests on web, iOS and Android, the Maestro flow, and CI |
| M2: Tickets and venues | `m2-tickets-and-venues.md` | not yet | Planned |
| M3: Agent and trace | `m3-agent-and-trace.md` | not yet | Planned |
| M4: Scores and standings | `m4-scores-and-standings.md` | not yet | Planned |
| M5: Watches and notifications | `m5-watches-and-notifications.md` | not yet | Planned |
| M6: Public demo | `m6-public-demo.md` | not yet | Planned |

M0–M5 run entirely on a developer's machine (§17); hosting is only in M6.

## 20. Technical Decisions and Open Items

### 20.1 Decisions made in this document

| ID | Decision | Rationale |
|---|---|---|
| TD1 | Agent runs in the API process (not the worker) | Needs to stream to the client; bounded at 45 s; avoids a job queue |
| TD2 | Live scores stored on the `games` row, not a separate live table | One read path for clients; the history that matters (final scores) stays on the row |
| TD3 | Jobs defined in code with an in-memory APScheduler store, plus `job_runs` for idempotency | No dynamic jobs needed; simpler than a persistent job store |
| TD4 | App tables in a non-exposed `app` schema with forced RLS, revoked grants/default privileges, and the Data API disabled; enforced by tests | Supabase's Data API plus the public anon key would otherwise expose tables; four independent layers so one misconfiguration isn't enough |
| TD5 | Transactional outbox for email | Exactly-once-ish delivery with retries (FR-N5) without a queue |
| TD6 | Grounding validator after composition | Enforces AG-4 deterministically instead of relying on prompts |
| TD7 | OpenAPI-generated TS client | Single source of truth for API types; drift caught in CI |
| TD8 | Web app served by the API in production | Same origin (no CORS), one fewer service (D2) |
| TD9 | `packages/ui` created in M0; all `packages/*` are private pnpm workspace packages consumed as source | Avoids screen duplication across two app shells; no npm publishing or build step |
| TD10 | React Native Paper (themed) + React Native core components (`View`, `Text`, `Pressable`, `ScrollView`, `Image`), no extra primitives library; visual direction from the reference template | Mature cross-platform component set that works on web; template supplies colors, type and motion |
| TD11 | Fixed hourly score polling instead of a budget-driven interval | Simpler; uses about 15% of the free quota on the busiest day; removes the UTC-midnight edge case |
| TD12 | Ranking weights V 0.4 / S 0.4 / D 0.2 | Decided priority: spending = viewing > distance |
| TD13 | Team and venue data from API-Sports + Census Places coordinates, with a small overrides file | Minimizes hand-curated data |

### 20.1.1 Platform and provider decisions

| ID | Decision | Outcome |
|---|---|---|
| D1 | Identity provider | **Supabase Auth**: free tier, Expo-compatible, issues JWTs that FastAPI verifies. Same vendor as the database. |
| D2 | Hosting | **Railway** for FastAPI (also serving the web static build) and the APScheduler worker; **Supabase** for Postgres and Auth; **EAS** for mobile builds and store submission. No Redis, Celery or separate web host. |
| D3 | App structure | Two Expo app shells (`apps/mobile`, `apps/web`) plus `packages/ui`, `packages/shared` and `packages/api-client` (private workspace packages). |
| D4 | Ticket provider | **Ticketmaster Discovery API** (free tier: 5,000 calls/day; plan for 2 req/s; pagination < 1,000). |
| D5 | Places provider | **Google Places (New)**. No geocoding API (see D11). |
| D6 | LLM provider | **OpenAI** via LangChain; model chosen with the eval suite (V6); caps per BRD A16. |
| D8 | Developer accounts | Apple Developer Program and Google Play Console accounts are set up in M6, only for TestFlight / store distribution. Before that, the mobile app runs on simulators, Expo Go or a development build. |
| D10 | Score provider | **API-Sports (American Football), Pro plan** (the free plan only covers past seasons), also used for the schedule and standings. |
| D11 | Geocoding | Not used. ZIP entry backed by a bundled public-domain ZIP coordinates dataset; venue cities by the Census Places dataset. |
| D12a | Email provider | **Resend**, sending from the backend only. Phone reminders are scheduled on the device with Expo Notifications (no server push service). |

### 20.2 Open items

| ID | Item | Needed by |
|---|---|---|
| T2 | Confirm `expo/fetch` streaming for SSE on native with the pinned Expo SDK (58) | M3 |
| T11 | Social sign-in (M6): offering Google sign-in on iOS generally requires Sign in with Apple for App Store and external TestFlight review. Decide the providers (Google only on web/Android, or Google + Apple) and configure them in the hosted Supabase project | M6 |
| T5 | Ticketmaster matching parameters and team attraction IDs | M2 |
| T6 | Google Places endpoint choice and field mask vs. pricing tier | M2 |
| T7 | OpenAI model selection via the eval suite (V6) | M3 |
| T8 | Resend idempotency-key support and test-sender behavior (V7) | M5 |

### 20.2.1 Provider verification (before each integration)

| ID | Item | Needed by |
|---|---|---|
| V1 | Current-season schedule, scores and standings on the API-Sports Pro plan: **confirmed 2026-10-29** (contract fixtures recorded in M1). Still to check: observed score update latency (first live game window) and attribution / portfolio-use terms. | M4 |
| V2 | Hosted Supabase free-tier limits, and whether inactive free projects are paused (affects an idle public demo). | M6 |
| V3 | Railway plan pricing for two always-on services (API, scheduler worker). | M6 |
| V4 | Ticketmaster terms of use: caching duration, attribution and display requirements. | M2 |
| V5 | Google Maps Platform free usage per SKU, caching rules, attribution; budget alerts configured. | M2 |
| V6 | OpenAI model choice (tool calling + structured output at low cost) and project budget limit configured. | M3 |
| V7 | Resend account created and free-tier limits confirmed (reported around 3,000 emails/month, 100/day); behavior of the shared test sender confirmed. | M5 |
| V8 | Project domain purchased and verified in Resend (SPF/DKIM) for sending to any user. | M6 |

### 20.3 Risks

| Risk | Mitigation |
|---|---|
| API-Sports score latency is worse than expected | The UI always shows "updated X min ago"; scores support planning rather than drive it |
| Ticketmaster price ranges often missing for NFL events | "Price not available" handling (BR-S5); availability Watches still work |
| Google Places costs exceed free usage | Field masks, app caps, console quotas, cache within terms |
| LLM output violates rules | Rules applied before the model, grounding validator, banned-claim filter, eval suite in the loop |
| SSE streaming quirks on native | `expo/fetch` streaming (T2); fallback to polling `GET /agent/runs/{id}` |
| Single API/worker instance | Acceptable for the MVP; the design (advisory lock, outbox, budgets in Postgres) supports scaling later |

## 21. Technical Requirements

These requirements are defined here rather than in the BRD because they describe implementation. IDs are unique across the BRD, this document and the UI/UX document.

### 21.1 Provider summary

| Dependency | Source | Data used | Limits and status | Fallback |
|---|---|---|---|---|
| Schedule, game status, scores, standings | API-Sports (American Football), Pro plan | Season schedule, status, scores, quarter/clock if available; daily standings | 7,500 requests/day (resets 00:00 UTC), 300 requests/minute, all endpoints. Current season confirmed (V1) | Curated schedule file (FR-O1b); last known score with "Scores paused" |
| Team and venue reference data | API-Sports + Census Places coordinates + curated overrides and rivalries files | Teams, divisions, venues and coordinates, featured rivalries | Internal (FR-O1a) | n/a |
| Tickets | Ticketmaster Discovery API, free public tier | Event match, availability, price range, purchase URL | 5,000 calls/day; 5 req/s (2 req/s on some endpoints, so plan for 2); pagination depth < 1,000; API key as `apikey` query parameter (V4) | "Ticket data unavailable" limitation |
| Venues | Google Places (New) | Bars near a location, hours, contact, rating | Billing account required even within free usage (V5) | "Venue search unavailable" limitation |
| LLM | OpenAI | Agent reasoning, tool calling, structured output | Pay-as-you-go; prepaid credits plus monthly project budget (V6) | "Planning unavailable"; browsing still works |
| Email | Resend | Alert, reminder and digest emails | M5: shared test sender; M6: verified domain (V7, V8) | In-app inbox only |
| Phone reminders | Device OS via Expo Notifications | Game-day reminders on iOS/Android | On-device scheduling, no external service | Email and inbox |
| Authentication | Supabase Auth | Sign-in, email verification, JWT sessions | Free tier (V2) | n/a |
| ZIP coordinates | Census ZCTA gazetteer (bundled, public domain) | ZIP → approximate coordinates | Refresh yearly | n/a |
| Hosting | Railway, Supabase, EAS | API + web, worker, database, mobile builds | V2, V3 | n/a |

### 21.2 Requirements

**Scores and standings**

| ID | Requirement | Pri |
|---|---|---|
| FR-LS5 | Score polling runs only during **game windows**, from shortly before kickoff (default 15 min) until the game is final or a maximum duration passes (default 4.5 hours). No polling outside game windows. | M |
| FR-LS6 | During game windows, scores are polled on a **fixed interval** (default every 60 minutes) with one shared "games by date" request per cycle. A daily request budget below the plan's limit acts as a hard guard (budgets reset at 00:00 UTC; a window crossing midnight UTC draws from the next day's budget). A share (default 10%) is reserved for final-score confirmation and recovery. | M |
| FR-LS7 | Polling fetches shared data once per cycle for all games in the window, no matter how many users are watching. User actions never trigger provider calls; clients read cached scores from the backend. | M |
| FR-LS10 | Schedule and scores come from the same provider, so games are linked by the provider's game ID. Provider team IDs are mapped to canonical team data; unmappable records are logged and skipped, never attached to the wrong game. | M |
| FR-LS11 | Open score views (Home "Live now", game detail) reload from the backend cache on a short interval (default every 5 minutes), on screen open and app foreground, and on pull-to-refresh. These reloads never call the score provider. | M |
| FR-LS12 | A mock score provider can replay a recorded game for automated tests, CI and local testing (FR-LS13). Replayed data is labeled "Sample data" everywhere it appears. | M |
| FR-LS13 | **Scores mode setting (non-production only):** `live` (API-Sports polling), `replay` (mock replay, no API-Sports score requests) or `auto` (default locally: `live` when a game window is in progress or starts within the next polling interval, otherwise `replay`). Production always uses `live` and refuses to start otherwise. | M |
| FR-LS14 | In `replay` mode, a chosen recorded game is shifted to start now (or at a configured offset) and plays back at a configurable speed (default 10×). It appears in "Live now" as a sample game alongside the real schedule; schedule, standings, tickets and venues stay live. | M |
| FR-LS15 | A record option saves score snapshots polled during a real game to a replay file. A small set of recorded games ships with the repo for tests. | S |
| FR-LS16 | The active scores mode is visible to testers: a "Sample data, replay" banner on score views and a log line at worker start-up and each polling cycle. | M |
| FR-ST1a | The daily standings job runs after Monday Night Football (default 10:00 UTC), uses one API-Sports request, stores a snapshot with its retrieval time, and counts against the shared budget (A15). | M |
| FR-ST2a | Provider team IDs in standings are mapped to canonical team data; unmapped teams are logged and skipped. | M |
| FR-ST6 | If the standings fetch fails, the previous snapshot is kept and the failure logged; staleness follows BRD BR-G5. | M |
| FR-ST7 | Standings fixtures (early-, mid- and late-season) are available for automated tests and CI. Live standings are used locally and in production. | M |
| FR-ST8 | Standings features have a kill switch; every other feature works unchanged when it's off. | S |

**Tickets and venues**

| ID | Requirement | Pri |
|---|---|---|
| FR-T5 | Ticket results are cached only as long as the provider's terms allow; cache length is configurable. | M |
| FR-T6 | Automated tests and CI use a fixture-based mock ticket provider (no secrets, no quota). Local testing and production use the live API. Mock data shown in the UI is labeled "Sample data." | M |
| FR-T7 | Ticketmaster usage stays within free-tier limits: a daily budget below the 5,000-call quota (default 4,000, shared by agent lookups and Watch checks), a 2 requests/second rate limiter, and pagination below the 1,000-item depth limit. Budget exhaustion produces the BRD FR-T9 message. | M |
| FR-T8 | The Ticketmaster API key travels as a query parameter, so request URLs are treated as secrets: never sent to clients, redacted from all logs, traces and error reports. | M |
| FR-V4 | Venue data is shown and cached only within the provider's terms (including attribution). | M |
| FR-V5 | Automated tests and CI use a fixture-based mock places provider. Local testing and production use live Google Places. Mock data shown in the UI is labeled "Sample data." | M |
| FR-V6 | Google Places requests ask only for displayed fields (field masks) to stay in the lowest pricing tier. Daily caps are set in the Google Cloud console and in the app; over the cap, the BRD FR-V7 message is shown. | M |
| FR-P3a | ZIP validation uses a bundled ZIP-coordinates dataset (no geocoding API); device coordinates are used directly and held only in request memory. | M |

**Notifications**

| ID | Requirement | Pri |
|---|---|---|
| FR-N2a | Alert emails are sent through Resend. | M |
| FR-N4 | Emails are sent from a verified project domain (SPF/DKIM) in production. | M |
| FR-N5a | Each alert has an idempotency key; delivery records are checked before sending (transactional outbox, §10.3). | M |
| FR-N6a | Delivery states are tracked (queued, sent, failed, skipped). Resend bounce/complaint webhooks set the user's email-disabled flag. | M |
| FR-N9a | The mobile app reconciles scheduled local notifications from `GET /reminders/upcoming` on start, foreground and after plan changes (§4.3). | M |

**Data maintenance and operations**

| ID | Requirement | Pri |
|---|---|---|
| FR-O1d | The schedule is synced from API-Sports by a daily job (one season-wide request when supported) and on manual CLI trigger; requests count against the shared budget. | M |
| FR-O1a | Team and venue reference data (conference, division, home venue and coordinates) comes from API-Sports where available, with coordinates from the bundled Census Places dataset; a curated overrides file fills gaps (API-Sports gives venue cities without state or country) and a curated file holds featured rivalries. | M |
| FR-O1b | Contingency: if API-Sports is unavailable for an extended period, a curated schedule file can be loaded through the same import path and change detection. | C |
| FR-O3 | Structured logs for agent runs, tool calls, provider calls, Watch checks and notification delivery. | M |
| FR-O4 | Provider errors, rate-limit responses, latency, LLM token usage and estimated cost are tracked. | M |
| FR-O4a | Score-provider usage is tracked against the daily budget (used, remaining, reserved) and logged every polling cycle; a warning is logged at 80%. | M |
| FR-O6 | Logs never include credentials, API keys (including keys in query strings), tokens or unnecessary personal data. Locations are stored no more precisely than needed. | M |
| FR-O7 | A simple internal report shows provider health, score budget usage, Watch check runs and agent cost (`cli.py ops-report`). | C |

**Non-functional (technical)**

- NFR-8b: Score reads are served from the backend cache; client traffic never affects provider request usage.
- NFR-9: External provider calls use timeouts, bounded retries with backoff, and graceful fallback (§8.2).
- NFR-10: Background jobs are idempotent and safe to retry (§10.1).
- NFR-14: All inputs are validated with typed schemas on the server, even if already validated on the client.
- NFR-20: The whole product (web, mobile, backend, worker, database, auth, email) runs locally with Docker and the Supabase CLI, without any hosting account, domain or app-store account (§17).
- NFR-21: Local testing uses **live provider keys** from a local `.env` that is never committed. Mock/fixture adapters are used only by automated tests and CI, and for score replay.
- NFR-22: Quota protection: until M6 local testing has the full API-Sports quota. From M6, local testing uses a separate API-Sports key if the provider's terms allow it; otherwise the local daily budget is lower (default 30) and live score polling is off locally unless explicitly enabled. Other providers use separate keys or projects per environment where available.
- NFR-23: Real alert emails can be sent during local testing through Resend (test sender until M6). A non-production recipient allowlist sends only to approved addresses; others are logged and skipped. A log-only email adapter is also available.
- NFR-24: In `replay` mode no API-Sports score requests are made; schedule and standings syncs still run live.

**Technical assumptions**

| ID | Assumption |
|---|---|
| A14 | Game-window defaults: start 15 min before kickoff, max 4.5 hours, poll every 60 minutes, 10% of the daily budget reserved. All configurable. |
| A15 | API-Sports budget (app cap 1,000 requests/day on the 7,500/day Pro plan): about 2 for the schedule sync, 1 for standings, 10% reserve, the rest for score polling. With hourly polling a full Sunday (about 11–12 hours of windows) uses roughly 12–15 requests. |

### 21.3 Technical acceptance criteria

- AC-26: Unit tests cover travel, budget, significance, ranking, Watch evaluation, polling rule, deduplication and idempotency.
- AC-27: Integration tests cover authorization (user A cannot access user B's data), persistence, provider adapters (with fixtures) and workers.
- AC-28: End-to-end tests cover onboarding → browse → plan → save → Watch → notification on web and at least one mobile platform.
- AC-31: Score polling makes no provider requests outside game windows, and daily requests never exceed the configured budget (checked against provider-usage logs).
- AC-33: Many users viewing the same game don't increase provider request usage (load test: 100 simulated viewers, same request count as 1).
- AC-36: A provider record that can't be matched to exactly one scheduled game is logged and never shown on the wrong game.
- AC-38: The mock score provider replays a full game (kickoff → final) for automated tests and non-game-day testing, labeled "Sample data."
- AC-41: Standings are fetched at most once per day, and the request is counted in the API-Sports budget.
- AC-42: Given fixed standings fixtures, each record-based tag applies exactly when its rule is met (unit-tested for every tag, including ties and boundary values).
- AC-46: With scores mode `auto`, the worker polls live on a day with a game window and replays on a day without one. With `replay`, no API-Sports score requests are logged. In production, a non-`live` scores mode prevents start-up.

## Appendix A — BRD Traceability (summary)

| BRD area | Where it's implemented |
|---|---|
| Accounts (8.1) | §6, `identity` module |
| Preferences (7.1, 8.2) | `preferences`, `zip_centroids`, §7.2 |
| Travel / spending / viewing rules (7.2–7.4) | `domain/travel.py`, `budget.py`, `suitability.py` |
| Notification rules (7.5) | `domain/alerts.py`, §10.3 |
| Significance + standings (7.6, 8.4.1) | `domain/significance.py`, `standings_sync`, `game_tags` |
| Schedule (8.3) | `schedule` module, `schedule_sync` |
| Scores (8.4) | `scores` module, `score_tick`, §10.4 |
| Tickets (8.5) | §8.4, `tickets` module |
| Venues (8.6) | §8.5, `venues` module |
| Agent + trace (8.7–8.8, 9) | §11 |
| Saved plans (8.9) | `plans` module |
| Watches (8.10) | `watches` module, `watch_check` / `watch_expiry` |
| Notifications (8.11) | §8.7, §10.3, client §4.3 |
| Operations + demo protections (8.12) | §8.2, §13, §15, §18 |
| Local development (TDD §21.2, NFR-20–24) | §17 |
