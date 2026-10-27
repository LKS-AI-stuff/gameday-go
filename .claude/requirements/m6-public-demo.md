# GameDay Go — M6: Public demo

| | |
|---|---|
| **Document type** | Milestone requirements |
| **Milestone** | M6 |
| **Status** | Planned (no technical design yet) |
| **Date** | 2026-10-27 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD §13 and the requirement IDs cited below), `.claude/docs/technical-design.md` (TDD sections cited below), `.claude/docs/ui-ux-design.md` |

These are the milestone's requirements: what must be built, as a checklist that cites the BRD, TDD and UI/UX sections holding the detail. `/generate-technical-design m6` turns them into a technical design at `.claude/technical-designs/m6-public-demo.md`, grounded in the current code; `/implement-technical-design m6` builds that design and ticks the items here as they're delivered.

**Users will be able to:** use the hosted web app and a test build of the mobile app, sign in with Google, and receive alerts at any address.

## Before starting

- [ ] V2 (Supabase free-tier limits and pausing), V3 (Railway pricing for two always-on services), V8 (buy a domain)
- [ ] T11: choose social providers (Google only on web and Android, or Google plus Sign in with Apple)
- [ ] Apple Developer Program and Google Play Console accounts (D8)

## Hosting (TDD §18)

- [ ] Multi-stage Dockerfile: Expo web export, then the Python image; FastAPI serves the web app with an SPA fallback at `/` and the API at `/api/v1`
- [ ] Railway services `api` and `worker` (one replica), migrations as the pre-deploy command, secrets in Railway variables
- [ ] Hosted Supabase: `bootstrap-db` for `gamedaygo_app`, Data API disabled, session-mode connection, production auth emails sent through Resend SMTP, redirect URLs
- [ ] Resend domain verified (SPF / DKIM), production `EMAIL_FROM`, webhook at `/api/v1/webhooks/resend`
- [ ] Custom domain with HSTS; `apple-app-site-association` and `assetlinks.json` for deep links
- [ ] Production guards (TDD §13); confirm the hosted JWT signing mode (TDD §6)

## Demo protections

- [ ] FR-O8: 15 agent runs per user per day
- [ ] FR-O9: daily AI spending cap ($0.65) backed by the OpenAI monthly budget
- [ ] FR-O10: daily caps per provider; NFR-22: separate API-Sports key or lower local budget
- [ ] FR-O11: email verification before the agent or Watches unlock (enforced since M0)

## Sign-in and mobile

- [ ] Google sign-in (plus Apple on iOS if chosen) with `expo-auth-session` and `expo-web-browser`; Age confirmation screen (UI/UX §7.1)
- [ ] EAS build profiles (`development`, `preview`, `production`); TestFlight and Play internal testing; universal links and app links

## Polish and launch checks

- [ ] Accessibility pass against UI/UX §9; privacy notice page (NFR-17), linked from sign-up and Settings
- [ ] `cli ops-report` (FR-O7, Could)
- [ ] `test_data_api_exposure.py` against the hosted project; Supabase Security Advisor review
- [ ] All BRD Appendix A scenarios on the hosted web app and at least one mobile build

## Exit criteria

all Appendix A scenarios pass on the hosted web app and at least one mobile build; demo protections (FR-O8–FR-O11) in place.
