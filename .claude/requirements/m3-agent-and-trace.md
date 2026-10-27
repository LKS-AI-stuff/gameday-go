# GameDay Go — M3: Agent and trace

| | |
|---|---|
| **Document type** | Milestone requirements |
| **Milestone** | M3 |
| **Status** | Planned (no technical design yet) |
| **Date** | 2026-10-27 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD §13 and the requirement IDs cited below), `.claude/docs/technical-design.md` (TDD sections cited below), `.claude/docs/ui-ux-design.md` |

These are the milestone's requirements: what must be built, as a checklist that cites the BRD, TDD and UI/UX sections holding the detail. `/generate-technical-design m3` turns them into a technical design at `.claude/technical-designs/m3-agent-and-trace.md`, grounded in the current code; `/implement-technical-design m3` builds that design and ticks the items here as they're delivered.

**Users will be able to:** plan a game day, refine it, inspect the trace and save plans (J3–J5).

## Before starting

- [ ] OpenAI key and a project monthly budget (V6, A16)
- [ ] T2: confirm `expo/fetch` streaming for SSE on native (fallback: poll `GET /agent/runs/{id}`)

## Database (TDD §7.4)

- [ ] `agent_sessions`, `agent_runs` (including `model`, `prompt_version`, `config_snapshot`), `agent_messages`, `agent_trace_steps`, `agent_proposals`, `saved_plans` (`reminder_hours`), `audit_events`
- [ ] LangGraph checkpoint tables created by Alembic in schema `app`, read through `AsyncPostgresSaver` on a psycopg pool

## Agent (TDD §11)

- [ ] `PlanState` and the graph: load context → understand → plan and act with tools → evaluate → replan → compose → ground check → finalize
- [ ] Guards on every edge: 8 tool calls, 4 replans, 45 s, per-run cost cap (AG-1); identical repeated lookups stopped (AG-8); cancellation flag between steps (FR-AG12)
- [ ] Tools (§11.4) with `user_id` from the run context: `get_upcoming_games`, `get_game_detail`, `get_game_status`, `search_tickets`, `search_venues`, `compare_options`, `propose_save_plan`, `propose_watch` (Watches go live in M5)
- [ ] Planning-window refusal as a trace step (FR-SC8); provider text delimited as data (AG-6); minimal user context sent to the model (AG-7)
- [ ] `PlanCard` structured output (§11.7); grounding check for prices, links, distances, kickoff times and records, plus the banned-claims filter (AG-4, BR-G1)
- [ ] Versioned prompts in `agent/prompts/`; token cost recorded per run; session cap of 20 user messages (FR-AG13)

## API

- [ ] `POST`/`GET /agent/sessions`, `GET /agent/sessions/{id}`, `POST /agent/sessions/{id}/messages` (SSE events, TDD §12), `GET /agent/runs/{id}`, `POST /agent/runs/{id}/cancel`, `GET /agent/runs/{id}/trace`, `POST /agent/proposals/{id}/decline`
- [ ] Saved plans: `POST /plans` (from a proposal), `GET /plans`, `GET`/`PATCH`/`DELETE /plans/{id}`, `POST /plans/{id}/refresh`
- [ ] Agent rate limit 10 messages/minute per user

## Frontend (UI/UX §6.5–6.7, §7.6–7.8)

- [ ] Plan tab: session list, chat with streaming text, compact live trace strip, clarification chips, Stop button, turns-remaining hint
- [ ] `PlanCard`: recommended band, alternatives, limitations box, freshness lines, proposal buttons that confirm only after the API succeeds (FR-AG9)
- [ ] Trace screen ("HOW THIS PLAN WAS MADE") with totals; on desktop, a right-hand panel beside the chat
- [ ] My Game Days › Plans and saved plan detail; "Plan this game" wired from game detail and Home
- [ ] All run states: limit reached, failed, cancelled, outside window, reconnecting, planning unavailable

## Evaluation (TDD §11.8)

- [ ] At least 20 scenarios (BRD Appendix A plus variants) with fixed fixtures; deterministic checks for travel, budget, banned phrases, grounding, clarification and injection (AC-18)
- [ ] A scripted fake model in CI; the real model on demand (`pytest -m eval`); compare 2–3 candidate models and pick the cheapest that passes (T7)

## Exit criteria

J3–J5 complete; AC-11, AC-16–AC-19, AC-29 and AC-48 pass; the evaluation set shows 0 rule violations (SM3); plan timing measured against SM4.
