# GameDay Go — M5: Watches and notifications

| | |
|---|---|
| **Document type** | Milestone requirements |
| **Milestone** | M5 |
| **Status** | Planned (no technical design yet) |
| **Date** | 2026-10-27 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD §13 and the requirement IDs cited below), `.claude/docs/technical-design.md` (TDD sections cited below), `.claude/docs/ui-ux-design.md` |

These are the milestone's requirements: what must be built, as a checklist that cites the BRD, TDD and UI/UX sections holding the detail. `/generate-technical-design m5` turns them into a technical design at `.claude/technical-designs/m5-watches-and-notifications.md`, grounded in the current code; `/implement-technical-design m5` builds that design and ticks the items here as they're delivered.

**Users will be able to:** create and manage alerts, receive real alert emails (to the developer's own address) and phone reminders (J6, J7).

## Before starting

- [ ] Resend account and API key; `EMAIL_ALLOWLIST` set to your address
- [ ] T8 and V7: Resend idempotency-key support, free-tier limits and test-sender behavior

## Database (TDD §7.4–7.5)

- [ ] `watches` (including `last_alerted_at`), `watch_evaluations`, `notifications`, `email_outbox`, `email_unsubscribes`

## Domain rules

- [ ] `watches.py`: `evaluate_ticket_watch` (stale data never triggers, BR-N8)
- [ ] `alerts.py`: `cooldown_elapsed` (rolling 12 h, BR-N5), `dedup_key` (retry safety), `allowed_by_level`, `within_daily_cap` (in the user's time zone, BR-N11)

## Jobs and pipeline (TDD §10.2–10.3)

- [ ] `watch_check` (one Ticketmaster lookup per game; interval stretches when the budget is short, FR-W8), `watch_expiry`, `reminder_emails` (saved plans at level Medium or above), `email_dispatch` (claimed with `SKIP LOCKED`, Watch status rechecked, up to 5 retries)
- [ ] Alert policy: lock the Watch, check the cooldown, write the inbox row, outbox row and `last_alerted_at` in one transaction
- [ ] Schedule-change alerts raised by `schedule_sync` for games with a saved plan or an active Watch (FR-W2, FR-O2)
- [ ] `weekly_digest` (Could priority, FR-N11)

## Email (TDD §8.7; UI/UX §7.12)

- [ ] Resend adapter with the non-production allowlist and a log-only mode
- [ ] Jinja2 templates with a plain-text part, reason, source and time, deep link, sender identity and postal line (FR-N3)
- [ ] One-click unsubscribe: signed per-category token, GET confirmation page, POST unsubscribe, `List-Unsubscribe` headers
- [ ] Bounce and complaint webhook, verified with signed fixtures locally (a public URL comes in M6)

## API

- [ ] `POST`/`GET /watches`, `PATCH /watches/{id}` (pause / resume), `DELETE /watches/{id}`; limit of 10 active (FR-W7)
- [ ] `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all`
- [ ] `GET /reminders/upcoming` (only saved plans with a reminder, future kickoff, level Medium or above)
- [ ] `propose_watch` proposals accepted through `POST /watches`

## Frontend (UI/UX §6.8, §7.8–7.11, §7.13)

- [ ] My Game Days › Alerts: `WatchRow` grouped by status, pause / resume / delete with undo, "Having trouble checking"
- [ ] Set an alert sheet (ticket price, ticket availability, keep watching after trigger); 10-alert limit and email-off messages
- [ ] Inbox with unread badge; notification categories in Settings; email-disabled banner after a bounce
- [ ] Saved plan reminder control (1 / 3 / 6 / 24 hours or off)
- [ ] Phone reminders with `expo-notifications`: permission on first save, reconcile from the reminders feed on start, foreground and plan or level changes; tapping opens the saved plan

## Tests

- [ ] AC-20–AC-25, AC-35, AC-39, AC-40; races between pause/delete and an in-flight check (AC-21); outbox retries never duplicate (AC-23)
- [ ] Scenarios A-9 (price drop), A-10 (moved kickoff), A-12 (game-day reminder)
- [ ] E2E: onboarding → browse → plan → save → alert → notification on web and one mobile platform (AC-28)

## Exit criteria

J6–J7 complete; AC-20–AC-25, AC-35, AC-39 and AC-40 pass.
