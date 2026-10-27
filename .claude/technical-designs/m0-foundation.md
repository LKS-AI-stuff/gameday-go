# GameDay Go — M0: Foundation

| | |
|---|---|
| **Document type** | Milestone technical design |
| **Requirements** | BRD §13 (M0) and the M0 scope in TDD §19; M0 predates the requirements folder |
| **Milestone** | M0 |
| **Status** | Code complete. Exit pending: manual tests on iOS and Android, CI green on GitHub |
| **Date** | 2026-10-27 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD §13 and the requirement IDs cited below), `.claude/docs/technical-design.md` (TDD sections cited below), `.claude/docs/ui-ux-design.md` |

This milestone is implemented. The sections below describe what was built, how to run and test it, and the database queries that confirm the data.

**Users can:** sign up with email verification, sign in and sign out on web and mobile, against the local stack (BRD §13).

**Exit criteria:** works locally on web, iOS and Android; automated checks pass; CI green.

## Implemented

**Monorepo and tooling**
- pnpm workspace + Turborepo: `apps/mobile` (Expo Go, iOS/Android only), `apps/web` (Expo web), `packages/ui`, `packages/shared`, `packages/api-client`, `packages/config`. Expo SDK 58, pinned.
- Shared TypeScript, ESLint (9) and Prettier config; Turborepo runs `lint`, `typecheck` and `test` across packages.
- Python backend as a separate `uv` project in `backend/` (Python 3.12).

**Backend** (`backend/app/`)
- Settings from the repo-root `.env` (`core/settings.py`), validated at start-up.
- JSON logging with secret redaction, including library logs; httpx request-URL logging is silenced so API keys in query strings never reach logs (`core/logging.py`, `core/redaction.py`; FR-O6, FR-T8).
- RFC 9457 `application/problem+json` errors with stable codes, and an `X-Request-ID` on every response (`core/errors.py`, `main_api.py`).
- Supabase access-token verification: signature (ES256 via JWKS, or HS256 shared secret), expiry, issuer, audience and role; JWKS cached and refetched on key rotation (`core/auth.py`; TDD §6).
- User provisioning on the first authenticated request, safe under concurrent requests; the 18+ confirmation is copied from the sign-up form's metadata (`modules/identity/`; FR-A3, FR-A5).
- Endpoints: `GET /api/v1/health`, `GET /api/v1/ready`, `GET /api/v1/me`, `POST /api/v1/me/age-confirmation`.
- Provider HTTP layer skeleton: kill switch, timeouts, retries with backoff and `Retry-After`, redacted call metrics (`core/http.py`; TDD §8.2). Daily budgets and rate limiting arrive with the first provider.
- CLI: `bootstrap-db` (creates the backend role and schema) and `export-openapi` (`app/cli.py`).

**Database** (TDD §6.1, §7.2)
- Table `app.users`; Alembic migration `0001` (also secures `app.alembic_version`).
- Hardening: schema `app` owned by role `gamedaygo_app`; forced RLS with one policy for the backend role only; all grants and default privileges revoked from `anon`, `authenticated` and `PUBLIC`; Supabase Data API disabled and auto-exposure off (`supabase/config.toml`). Even Supabase's `postgres` admin and Studio can't read app tables.
- New tables must call `secure_table()` (`backend/migrations/hardening.py`).

**Apps and shared packages**
- `packages/ui`: design tokens (TDD §4.4) with automated WCAG AA contrast checks, React Native Paper theme (light/dark, follows the OS), Oswald/Open Sans bundled fonts, auth state (`AuthProvider`), sign-in, sign-up (18+ checkbox), verify-email (60 s resend cooldown) and a signed-in placeholder Home.
- `packages/shared`: sign-in and sign-up form schemas (Zod) and product copy.
- `packages/api-client`: types generated from the backend OpenAPI schema, a typed fetch client that maps problem responses to `ApiError`, and TanStack Query hooks keyed by user ID.
- Routing: `/` sends signed-out users to `/sign-in` and signed-in users to `/home`; auth and app route groups are guarded by session state.
- Sessions: device keychain via SecureStore on mobile (chunked for size); `localStorage` on web, where the verification link signs the user in.

**Local stack**
- Supabase CLI (repo dev dependency): Postgres 17, Auth with email confirmation required, Mailpit email catcher. Realtime, Storage, Edge Functions and Analytics disabled.
- Social sign-in is deferred to M6 (FR-A1, T11).

**CI** (`.github/workflows/ci.yml`)
- Frontend: format check, lint, typecheck, tests, API client drift check, web build, mobile config check.
- Backend: ruff, mypy, `bootstrap-db`, migration round trip (up, down, up), pytest on plain Postgres 17.

## Run it

```bash
pnpm supabase start                                   # if not running
cd backend && uv run uvicorn app.main_api:create_app --factory --reload --host 0.0.0.0
pnpm --filter @gamedaygo/web dev                      # web: http://localhost:8081
pnpm --filter @gamedaygo/mobile dev                   # phone: Expo Go, exp://<LAN IP>:8082
```

- Verification emails go to **Mailpit** at http://127.0.0.1:54324, not to real inboxes (no email provider is connected locally). Click verification links **on the Mac**: they point to `127.0.0.1`, which on a phone means the phone itself.
- Port 8082 serves the app to Expo Go only; in a browser it shows a blank page. The web app is on 8081.
- `apps/mobile/.env` must use the Mac's LAN IP (`ipconfig getifaddr en0`), and the phone must be on the same Wi-Fi.

## Automated checks

```bash
pnpm turbo run lint typecheck test       # TS packages and apps (incl. contrast and routing tests)
pnpm format:check
cd backend
uv run ruff format --check . && uv run ruff check . && uv run mypy app migrations tests
uv run pytest                            # unit, /me integration, database hardening
uv run pytest -m supabase                # Data API exposure + real token check (local stack running)
```

## Manual tests: web (http://localhost:8081)

| # | Do | Expect |
|---|---|---|
| W1 | Open the page | Sign-in screen with the "GAMEDAY GO" wordmark and the "not affiliated" note |
| W2 | **Create account**; submit empty, then a bad email, a short password, mismatched passwords | Inline error under each field |
| W3 | Valid form with **I'm 18 or older** unchecked | "You must be 18 or older to use GameDay Go"; no account created (check with Q1) |
| W4 | Check the box and create the account | "Check your inbox" screen; **Resend email** counts down from 60 s |
| W5 | **I've verified, sign in** without verifying, then sign in | Back to the verify screen; not signed in. Q1 shows `verified = f` |
| W6 | Open the email in Mailpit and click the link | Web app opens signed in on Home: your email and "Account ready". Q1 shows `verified = t`; Q2 shows a row with `age_confirmed_at` set |
| W7 | Refresh the page | Still signed in |
| W8 | **Sign out**, then open http://localhost:8081/home | Sign-in screen; `/home` isn't reachable while signed out |
| W9 | Sign in with a wrong password | "Incorrect email or password" under the password field |
| W10 | Sign in correctly | Home |

## Manual tests: phone (Expo Go; repeat on iOS and Android)

| # | Do | Expect |
|---|---|---|
| P1 | Open the project in Expo Go | Sign-in screen |
| P2 | Sign up with a new email, 18+ checked | "Check your inbox" screen |
| P3 | On the Mac, click that email's link in Mailpit | Mac browser opens signed in (expected) |
| P4 | On the phone: **I've verified, sign in**, then sign in | Home with "Account ready" (the phone reached the backend). Q2 shows the new row |
| P5 | Fully close Expo Go and reopen the project | Still signed in (session in the device keychain) |
| P6 | Sign out; sign in with the account created on web | Works: accounts are shared across platforms |
| P7 | Switch the phone to dark mode | App switches to the dark theme |

If Home shows "Can't reach GameDay Go…", the phone can't reach the API on port 8000: check the LAN IP in `apps/mobile/.env`, the Wi-Fi network and VPNs.

## Database checks

App tables are readable only by the backend role (by design), so the queries connect as the role that owns each table. Run from the repository root.

**Q1. Sign-in accounts** (Supabase Auth, as the `postgres` admin):

```bash
docker exec -it supabase_db_gameday-go psql -U postgres -c "
  select id, email,
         email_confirmed_at is not null as verified,
         raw_user_meta_data->>'age_confirmed' as age_meta,
         created_at, last_sign_in_at
  from auth.users
  order by created_at desc;"
```

**Q2. App users** (schema `app`, as the backend role):

```bash
PW=$(grep '^DATABASE_URL=' .env | sed -E 's#.*gamedaygo_app:([^@]+)@.*#\1#')
docker exec -it -e PGPASSWORD="$PW" supabase_db_gameday-go \
  psql -h 127.0.0.1 -U gamedaygo_app -d postgres -c "
  select id, email, age_confirmed_at, timezone, created_at
  from app.users
  order by created_at desc;"
```

An `app.users` row is created the first time a signed-in user calls the backend (reaching Home), so a verified account that never reached Home has no row yet. `timezone` stays empty until onboarding (M1).

**Q3. Useful checks** (open a prompt by dropping the `-c "…"` part of Q1 or Q2):

```sql
-- As postgres: accounts that signed up but never verified
select email, created_at from auth.users where email_confirmed_at is null;

-- As gamedaygo_app: users without the 18+ confirmation (expected: none from the sign-up form)
select email from app.users where age_confirmed_at is null;
```

**Q4. Hardening spot check** (expected: `permission denied for table users`):

```bash
docker exec -it supabase_db_gameday-go psql -U postgres -c "select count(*) from app.users;"
```

**Q5. Data API is off** (expected: HTTP 503):

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:54321/rest/v1/users" \
  -H "apikey: $(grep '^SUPABASE_PUBLISHABLE_KEY=' .env | cut -d= -f2)"
```

## Exit checklist

- [x] Automated checks pass locally (backend, TS packages and apps, web build)
- [x] Sign-up, verification, sign-in and `/me` verified end to end over HTTP against the local stack
- [ ] Manual web tests W1–W10
- [ ] Manual phone tests P1–P7 on iOS
- [ ] Manual phone tests P1–P7 on Android
- [ ] CI green on GitHub after the first push
