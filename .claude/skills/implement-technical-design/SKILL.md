---
name: implement-technical-design
description: Implement a GameDay Go technical design from .claude/technical-designs/ (generated from a requirements file in .claude/requirements/). Writes the code, runs the repo's checks with fix-and-retry, has a separate agent on a different model review the change, then rewrites the design document as implemented (what was built, run steps, manual tests and database queries) and ticks the delivered requirements. Use when the user asks to implement or build a milestone or a design, or invokes /implement-technical-design. Takes the design filename (or a milestone shorthand such as "m1") as an argument; if none is given, ask which one.
---

# Implement a technical design

This skill builds one design (usually a milestone) end to end: code across the backend, shared packages and both apps,
validated with the repo's own checks (fixing failures automatically), self-reviewed against the
design, independently reviewed by a separate agent on a different model, and finally recorded in
the design document the way `m0-foundation.md` is, with the delivered items ticked in its requirements file.

Everything runs inline in this skill run. Completion is surfaced with the native `PushNotification`
tool (step 7).

## 1. Resolve the design document

- Accept a design filename with or without `.md` and with or without the `.claude/technical-designs/`
  prefix. A milestone shorthand (`m1`, `M1`, `1`) resolves to `.claude/technical-designs/m1-*.md`.
- If nothing was given, list the files there with their **Status** row and ask which one
  (`AskUserQuestion`).
- If there's no design yet but a matching requirements file exists in `.claude/requirements/`, say so
  and offer to run `/generate-technical-design` on it first. Don't implement straight from a
  requirements checklist.
- If nothing matches at all, say so, list what's there, and ask again rather than guessing.
- Check the design's **Milestone** / **Prerequisites**: if a milestone it depends on isn't implemented
  yet, say so and ask before starting. Note the **Requirements** file it was generated from.

## 2. Read for context, and check prerequisites

Read, in order:

1. The design document (design, implementation phases, test plan, exit checklist) and the
   requirements file it was generated from (the scope every item must meet).
2. `CLAUDE.md`: repo rules and commands. Every change must respect them (hard rules in deterministic
   backend code; `user_id`-scoped repositories; pure `domain/`; outbound calls only via `core/http.py`;
   `secure_table()` on new tables; tunables as config; no secrets in committed files or
   `EXPO_PUBLIC_*`; React Native Paper + tokens; "Alerts" in user-facing copy; no team logos).
3. The BRD, TDD and UI/UX sections the document cites.
4. Earlier milestones' "Implemented" sections, and the actual code the design touches. Don't trust the
   design's "Current state" blindly: confirm with `Explore` or targeted `Grep`/`Read`. If the code has
   moved on, follow the code and note the discrepancy in the report.

Then check the document's **Prerequisites** / "Before starting" items:
- Provider keys: check only that the variable is present and non-empty in `.env` (e.g.
  `grep -c '^APISPORTS_KEY=.' .env`). Never print or log a key's value.
- Open items and decisions: if one blocks a phase, stop before that phase and ask
  (`AskUserQuestion`), rather than guessing.
- A library, service or provider not approved in TDD §4–5: ask before adding it.

## 3. Implement in phases

Work through the design's "Implementation phases" in order. If there are none, use:

```
database (Alembic migration + secure_table) → domain → providers → services/API
→ pnpm api:generate → jobs → shared packages and screens (packages/ui) → app routes (apps/*)
```

Finish each phase as a coherent, working change before the next. Follow the patterns M0 and later
milestones established (module layout `router.py` / `service.py` / `schemas.py`, repositories keyed by
`user_id`, screens in `packages/ui` with thin route files in each app). Write the tests for each phase
as you go. Use mocks and fixtures only in tests; local runs use live keys.

## 4. Validate: fix and retry automatically

Run what applies to the change (commands in `CLAUDE.md`):

- **Backend:** `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy app migrations tests`,
  `uv run pytest`. On a new migration: `alembic upgrade head`, `downgrade -1`, `upgrade head`.
  If Supabase config, auth or tables changed and the stack is running: `uv run pytest -m supabase`.
- **API changed:** `pnpm api:generate`, and confirm the generated client is committed-ready.
- **TypeScript:** `pnpm turbo run lint typecheck test`, `pnpm format:check`, and the web build
  (`pnpm --filter @gamedaygo/web build:web`).
- **Behavior:** where practical, start the API locally, exercise the changed endpoints with `curl`
  using a real local Supabase token, and check the data with the design's database queries. Stop
  anything you started. You can't tap through the phone app; say so in the report rather than
  claiming it was tested on a device.

**On any failure:** read the actual output, fix the root cause, and re-run that step. Up to **3
attempts** per failing step; if it still fails, stop further phases, report the exact failure and what
was tried, and ask before continuing.

Never weaken a check to make it pass (skipping tests, loosening lint or hardening rules).

## 5. Review: self-review, then an independent agent

### 5a. Self-review against the design

Read back the **full** change (`git status`, `git diff`, and the contents of untracked files; don't rely
on memory) against the design's test plan, exit checklist, security section and the `CLAUDE.md` rules.
Fix clear oversights; flag (don't silently decide) judgment calls or scope questions.

### 5b. Independent review by a separate agent

A review by the session that wrote the code shares its blind spots, so also hand the change to a fresh
agent. This step is part of the skill and needs no separate approval.

1. Spawn one agent with `Agent`, `subagent_type: "general-purpose"`, and a **model different from the
   implementer's** (e.g. `"fable"` if implementing on Opus, otherwise `"opus"`). Not a `fork`: a fork
   inherits this context and wouldn't be independent. Run it in the foreground.
2. Give it a self-contained prompt: the design document and requirements file paths; read `CLAUDE.md`, the design and the
   BRD/TDD/UI sections it cites; inspect the change with `git status` / `git diff` and read untracked
   files; it is **read-only** (no edits, commits or servers); report findings most severe first, each
   with `file:line`, what is wrong and a concrete failure scenario. Ask it to check:
   - **Correctness**: logic errors, races, async mistakes, resource leaks, boundaries, time zones and
     UTC handling.
   - **Design conformance**: requirements, API contract, config names and defaults, exit checklist
     items missed or done differently.
   - **Repo rules**: hard rules enforced in code, not prompts; every user-owned query filtered by
     `user_id`; `domain/` pure; outbound calls only via `core/http.py` (budget, kill switch, redaction);
     new tables secured (`secure_table()`, passes `test_db_hardening.py`); tunables in config; no
     secrets in committed files, logs or `EXPO_PUBLIC_*`.
   - **Security**: injection (including prompt injection via provider text), authorization gaps, input
     limits, rate limits, data leaked in errors or traces.
   - **Tests**: behavior the design requires that is untested or only trivially tested.
   - **Frontend**: typing holes, stale state or effects, Paper and token usage, accessibility,
     loading / empty / error states, user-facing "Alerts" wording.
   Tell it to skip style nitpicks and anything lint already enforces, and to say plainly when it finds
   nothing.
3. Triage each finding yourself: verify it against the code, then **fix** it (and re-run the affected
   step-4 checks, same attempt limit), **skip** it with a one-line reason, or **flag** it for the user.
4. One review round only. If fixes were substantial, say so and suggest `/code-review ultra`.
5. If the agent fails or can't run, say so. Never claim a review happened when it didn't.

## 6. Record the result

Rewrite the design document the way `m0-foundation.md` is written:

- Header: **Status** `Code complete` (or `Code complete. Exit pending: …` for anything not yet
  verified, such as device tests or CI), **Date** updated.
- **Implemented**: what was built, by area, with file paths and requirement IDs.
- **Run it**: commands, new settings in `.env`, and any gotchas found along the way.
- **Automated checks**: the commands, including any new test markers.
- **Manual tests**: numbered steps per platform with expected results, each pointing to the database
  query that confirms its data.
- **Database checks**: copy-paste queries (Supabase `auth.*` as `postgres`; schema `app` only as
  `gamedaygo_app`, with the password read from `.env`).
- **Exit checklist**: tick only what was actually verified in this run; leave manual device tests and
  CI unticked for the user.

In the requirements file, tick each item that was delivered and set its **Status** (e.g. `Implemented`,
linking the design); leave undelivered items unticked and list them in the report. Also update
the TDD §19 index, the "Current milestone" line in `CLAUDE.md` and the README
status. If implementation changed a decision, update the BRD, TDD or UI/UX doc in the same change.

## 7. Notify, then report. Don't commit

Call `PushNotification` (`status: "proactive"`) with one line under 200 characters, e.g.
`"M1 implemented: all checks pass, review fixes applied"` or
`"M1 stopped at phase 3: API-Sports key missing, needs your input"`. Skip it if the run stopped at
step 1 or nothing changed.

Then report: what changed by area (briefly), validation results (passed, retried and why, not
verifiable here), the reviewer's findings with what was done about each, doc updates, and what's left
for the user (device tests, CI, commit). Don't create a commit unless the user asks. Suggest
`/code-review ultra` in one line as an option for a deeper review.
