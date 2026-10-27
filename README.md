# GameDay Go

An NFL game-day planner for iOS, Android and web. An AI agent recommends going to the stadium, watching at a sports bar, or watching at home, based on your budget, travel and viewing preferences, and shows its reasoning step by step.

GameDay Go is not affiliated with the NFL or any team.

## Status

Milestone **M0 (foundation)** is code complete. Milestone requirements are in `.claude/requirements/`; each milestone's technical design, with its status and test steps (including database queries), is in `.claude/technical-designs/`. TDD §19 has the index.

## Stack

- **Apps:** Expo (React Native + React Native Web), Expo Router, React Native Paper. `apps/mobile` (iOS/Android) and `apps/web` share screens from `packages/ui`.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy + Alembic, PostgreSQL (Supabase), Supabase Auth.
- **Monorepo:** pnpm workspaces + Turborepo; the backend is a separate `uv` project.

## Local setup

Prerequisites: Node 22+, Docker, [uv](https://docs.astral.sh/uv/), and Corepack-enabled pnpm (`corepack enable pnpm`). For phones, install Expo Go.

```bash
pnpm install
pnpm supabase start                            # local Postgres + Auth + email catcher

cp .env.example .env                           # backend settings (see comments inside)
cp apps/web/.env.example apps/web/.env         # web client settings
cp apps/mobile/.env.example apps/mobile/.env   # phone client settings (use your LAN IP)

cd backend
uv sync
uv run python -m app.cli bootstrap-db          # creates the backend DB role and schema
uv run alembic upgrade head
uv run uvicorn app.main_api:create_app --factory --reload --host 0.0.0.0
```

In another terminal:

```bash
pnpm --filter @gamedaygo/web dev       # http://localhost:8081
pnpm --filter @gamedaygo/mobile dev    # scan the QR code with Expo Go
```

Verification emails land in the local email catcher (Mailpit) at http://127.0.0.1:54324.

## Checks

```bash
pnpm turbo run lint typecheck test     # TypeScript packages and apps
pnpm format:check

cd backend
uv run ruff format --check . && uv run ruff check . && uv run mypy app migrations tests
uv run pytest                          # unit, integration and database hardening tests
uv run pytest -m supabase              # Data API exposure test against the local Supabase stack
```

## Docs

- `.claude/docs/business-requirements.md`: what and why
- `.claude/docs/technical-design.md`: how it's built
- `.claude/docs/ui-ux-design.md`: screens and behavior
- `.claude/requirements/`: requirements per milestone (and later features)
- `.claude/technical-designs/`: technical designs, with status and test guide once implemented
