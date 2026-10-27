---
name: generate-technical-design
description: Generate a GameDay Go technical design (in .claude/technical-designs/) from a requirements file in .claude/requirements/, grounded in the BRD, TDD, UI/UX doc and the current code. Use when the user asks to create/generate/write a technical design from a requirements doc or for a milestone, or invokes /generate-technical-design. Takes the requirements filename (or a milestone shorthand such as "m1") as an argument; if none is given, ask which file to use.
---

# Generate a technical design from a requirements file

Requirements live in `.claude/requirements/`: one file per milestone (`m1-preferences-and-schedule.md`,
…, each a checklist of what must be built) plus any feature requirements added later. This skill
turns one of them into a technical design in `.claude/technical-designs/` that an implementer can
build from: grounded in the high-level docs in `.claude/docs/` and in the code as it is today, not the
requirements reworded.

## 1. Resolve the input file

- Accept a filename with or without `.md` and with or without the `.claude/requirements/` prefix.
  A milestone shorthand (`m1`, `M1`, `1`) resolves to `.claude/requirements/m1-*.md`.
- If nothing was given, list the files in `.claude/requirements/` with their **Status** row and ask
  which one (`AskUserQuestion`, one option per file).
- If the file doesn't exist, say so, list what's there, and ask again rather than guessing.

## 2. Read for context before writing anything

Read, in order:

1. The requirements file: it defines the scope. Every item in it must end up designed, or explicitly
   deferred with a reason and the milestone it moves to. For a feature requirements file, map each
   requirement to existing BRD IDs where they already cover it, and note what is new scope.
2. `CLAUDE.md`: the repo rules. Every design must respect them: hard rules in deterministic backend
   code, never in prompts; `user_id`-scoped repositories; `domain/` pure; outbound calls only through
   `core/http.py`; new tables call `secure_table()`; tunables as config with TDD §13 defaults;
   no secrets in `EXPO_PUBLIC_*`; Paper + tokens UI; users see "Alerts"; minimal dependencies.
3. The high-level docs in `.claude/docs/`, only the parts the requirements cite plus what they depend on:
   - `business-requirements.md`: the FR-, BR-, AC- and journey IDs in scope, and BRD §13
   - `technical-design.md`: the cited sections (data model §7, providers §8, domain §9, jobs §10,
     agent §11, API §12, config §13, testing §16), the §19 index and open items §20.2
   - `ui-ux-design.md`: the cited screens, components, states and copy
4. The existing documents in `.claude/technical-designs/`: their "Implemented" sections show what
   already exists and the patterns and format to follow (`m0-foundation.md` is the reference); also
   check the other requirements files so the design doesn't duplicate or contradict planned work.
5. The actual code the design touches: real modules, models, migrations, endpoints, packages and
   screens (`Explore` or targeted `Grep`/`Read`). A design that doesn't name real files, functions and
   current behavior isn't grounded. Where docs and code disagree, the code is the current state: say so.

## 3. Write the design

**Output path:** `.claude/technical-designs/<output-name>.md`. If the input's base name ends in
`-requirements` (or is exactly `requirements`), replace that with `-design`
(`watch-parties-requirements.md` → `watch-parties-design.md`); otherwise keep the base name
(`m1-preferences-and-schedule.md` stays `m1-preferences-and-schedule.md`). Kebab-case, `.md`, no spaces.

If that file already exists, tell the user and ask (`AskUserQuestion`) whether to overwrite it, merge
into it, or pick another name. Never silently clobber a design: it may hold hand-refined detail or a
record of what was implemented.

**Header table:** **Document type** `Milestone technical design` or `Feature technical design`;
**Requirements** (the source file path); **Milestone** (for a feature: the milestone it should be built
in or after, with the reason); **Status** `Designed`; **Date**; **Builds on** (the BRD, TDD and UI/UX doc).

**Sections**, adapted to the input but covering all of it:

- **Objective**: one or two sentences: the BRD §13 outcome and journeys for a milestone, or what the
  feature achieves; cite the requirements file by name.
- **Scope**: requirement IDs covered; anything deferred, with where it moves.
- **Prerequisites**: keys, accounts and open items (T-, V-) to resolve first, how to resolve each, and
  which ones block starting. For a feature: the milestones that must be implemented first.
- **Current state**: what exists today that this builds on, by real file path.
- **Design by area**: database (tables, columns, indexes, migrations, `secure_table()`), domain rules
  (function signatures, edge cases), providers (adapter, budget, rate limit, cache, mock, contract
  fixtures), services and API (endpoints, request/response shapes, error codes), jobs, agent pieces,
  frontend (routes, screens, components, every loading / empty / error state, copy from UI/UX §8).
  Record genuine decisions with their rationale.
- **Configuration**: new settings with defaults (from TDD §13, or proposed and added there).
- **Security and non-functional**: authorization, hardening, redaction, quotas, accessibility,
  performance targets.
- **Implementation phases**: ordered, each ending in something verifiable (default order:
  database → domain → providers → services/API and `pnpm api:generate` → jobs → frontend).
- **Test plan**: automated tests per phase mapped to AC- IDs; numbered manual test steps with expected
  results; and the database queries that confirm each step's data, in the M0 format (Supabase `auth.*`
  as `postgres`; schema `app` only as `gamedaygo_app`).
- **Open questions and risks**: real unknowns only.
- **Exit checklist**: exit criteria, automated checks, manual tests per platform, CI.

Keep it as long as it needs to be and no longer.

## 4. Keep the other docs consistent

- **Requirements file:** set its **Status** to `Designed` and add a link to the design. Don't
  rewrite its requirements; if the design finds one wrong or missing, say so and ask.
- **High-level docs:** the BRD, TDD and UI/UX doc stay the source of truth. If the design needs a change
  there (a setting, endpoint, table, column or decision that differs), make it in the same edit,
  following `CLAUDE.md`'s doc rules (BRD business-only; no history of dropped ideas), and list each
  change in the report. Update the TDD §19 index (add a row for a new feature).
- **New business scope:** if a feature requirements file adds scope the BRD lacks, propose the new BRD
  entries (requirement and acceptance-criteria IDs following its numbering) and ask
  (`AskUserQuestion`) before adding them; then cite those IDs in the design.
- Any library, service or provider not already approved in TDD §4–5 needs the user's approval first.

## 5. Report back

Give the design's path and its requirements file, a 2–4 sentence summary, the prerequisites that still
need the user (keys, accounts, decisions), and any changes made to other docs. Don't commit.
