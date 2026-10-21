# GameDay Go

An NFL game-day planner (iOS, Android, web). An AI agent recommends going to the stadium, watching at a sports bar, or watching at home, and shows its reasoning step by step. It also offers ticket and venue lookup, alerts by email and phone reminders, and scores and standings.

## Source of truth

Read these before working on a feature. They define behavior; code follows them.

- `.claude/docs/business-requirements.md`: what and why (business rules, functional requirements, acceptance criteria)
- `.claude/docs/technical-design.md`: how (architecture, data models, agent graph, providers, jobs, config, testing, milestones in §19, technical requirements in §21)
- `.claude/docs/ui-ux-design.md`: screens, components, states, copy. The approved mockup: https://claude.ai/artifact/8URqVFmbGDbwAC3sSk8saS
- `.claude/docs/Template/`: a scraped Nicepage page used only as a visual reference. Don't reuse its assets (TDD §4.4) and don't commit it.

Requirement and decision IDs (FR-, BR-, AG-, NFR-, AC-, SM-, G-, J-, P-, A-, D-, TD-, T-, V-, UX-) are unique across all three docs. Cite them in code comments, tests and commits where helpful.

## Status

Current milestone: **M0** (TDD §19), code complete; exit pending phone testing and CI on GitHub. Build milestone by milestone (M0–M6). M0–M5 run entirely locally (TDD §17); hosting is only in M6. Update this line when a milestone closes.

## Rules for this repo

- **Docs stay current.** When a decision changes, update the relevant doc (and this file, if it's affected) in the same change.
  - The BRD stays business-only: technical detail goes to the TDD, screen detail to the UI/UX doc.
  - Docs describe the current scope plus a future-roadmap list only, with no history of dropped ideas.
- **Hard rules live in deterministic backend code** (budget, travel, authorization, alert limits, planning window), never in prompts (BRD principle 4, AG-3).
- **Authorization:** every repository method that reads user-owned data takes `user_id` and filters by it. Agent tools get `user_id` from the run context, never from model arguments (FR-A5, TDD §5.3, §6).
- **Layering:** `backend/app/domain/` is pure (no DB, provider or FastAPI imports). Every outbound provider call goes through `core/http.py` (kill switch, budget, rate limit, redaction; TDD §8.2). Never call `httpx` directly.
- **Confirmation gate:** the agent only proposes saving a plan or creating a Watch; the user's tap creates it (FR-AG8).
- **Times:** store and transfer UTC; always display with an explicit time zone (NFR-4).
- **Tunables are config variables** (intervals, limits, caps, thresholds), with defaults from TDD §13.
  - API-Sports' free tier is 100 requests/day. Backend score polling defaults to hourly; clients reload scores from the backend cache every 5 minutes (no provider cost).
- **Providers:** live keys are used locally, in a git-ignored `.env`. Mocks and fixtures are only for automated tests, CI and score replay; tests never call live providers.
- **Secrets:** never commit them, never log API keys (TDD §8.2), and never put one in an `EXPO_PUBLIC_*` variable, since those ship inside the apps (NFR-12).
- **Minimal dependencies.** Libraries named in TDD §4–5 are pre-approved. Don't add any other service, library or provider without asking.
- **Database:** app tables live in schema `app` with forced RLS and no grants to `anon`/`authenticated`; the Supabase Data API is off (TDD §6.1). Every new table (including LangGraph's checkpoint tables) is created by Alembic and must pass `test_db_hardening.py`.
- **UI:** React Native Paper plus React Native core components, with design tokens from TDD §4.4. Users see "Alerts" (internally "Watches"). No official NFL or team logos, team colors or trademarks as branding (NFR-18, UX4).
- Don't claim tests or builds pass unless they were run.

## Stack (details in TDD §4–5)

pnpm + Turborepo monorepo: `apps/mobile`, `apps/web` (Expo, Expo Router), `packages/ui`, `packages/shared`, `packages/api-client`, `packages/config` (private workspace packages, not published).

`backend/`: Python 3.12, uv, FastAPI, SQLAlchemy + Alembic, LangGraph + OpenAI, APScheduler worker, Supabase (Postgres + Auth; local via Supabase CLI), Resend.

## Commands

pnpm and uv live in `~/.local/bin`. Full setup is in `README.md` and TDD §17.

- Local stack: `pnpm supabase start` / `pnpm supabase stop` (Postgres on 54322, Auth on 54321, Mailpit on 54324)
- API: `cd backend && uv run uvicorn app.main_api:create_app --factory --reload --host 0.0.0.0`
- Apps: `pnpm --filter @gamedaygo/web dev` (:8081), `pnpm --filter @gamedaygo/mobile dev` (:8082, Expo Go)
- Migrations: `cd backend && uv run alembic upgrade head`; new DB: run `uv run python -m app.cli bootstrap-db` first. New tables call `secure_table()` (`migrations/hardening.py`).
- API client: `pnpm api:generate` after any backend API change (CI fails on drift)
- TS checks: `pnpm turbo run lint typecheck test`, `pnpm format:check`
- Backend checks: `cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy app migrations tests && uv run pytest`
- Supabase exposure test: `cd backend && uv run pytest -m supabase` (needs the local stack)
- CI: `.github/workflows/ci.yml` (frontend + backend jobs; mocks only, plain Postgres 17)
