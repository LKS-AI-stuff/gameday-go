# GameDay Go — M4: Scores and standings

| | |
|---|---|
| **Document type** | Milestone requirements |
| **Milestone** | M4 |
| **Status** | Planned (no technical design yet) |
| **Date** | 2026-10-27 |
| **Builds on** | `.claude/docs/business-requirements.md` (BRD §13 and the requirement IDs cited below), `.claude/docs/technical-design.md` (TDD sections cited below), `.claude/docs/ui-ux-design.md` |

These are the milestone's requirements: what must be built, as a checklist that cites the BRD, TDD and UI/UX sections holding the detail. `/generate-technical-design m4` turns them into a technical design at `.claude/technical-designs/m4-scores-and-standings.md`, grounded in the current code; `/implement-technical-design m4` builds that design and ticks the items here as they're delivered.

**Users will be able to:** see "Live now", scores and final scores, team records and record-based tags (J8).

## Before starting

- [ ] V1: observe real score latency during a live game window; check attribution and portfolio-use terms

## Database

- [ ] `standings_snapshots`, `standings_entries`, `score_recordings`, `job_runs` (TDD §7.3, §7.6)

## Worker (TDD §10)

- [ ] `main_worker.py` with APScheduler and the scheduler advisory lock on a dedicated connection; `job_runs` for idempotent jobs
- [ ] Jobs: `schedule_sync` (daily 09:00 UTC, moved from the CLI), `standings_sync` (daily 10:00 UTC), `score_tick` (every minute), `retention_cleanup` (daily 08:00 UTC, TDD §7.7; not assigned before, placed here with the worker)

## Domain rules

- [ ] `polling.py`: `game_windows` (merging overlaps), `should_poll`, `resolve_scores_mode`
- [ ] `significance.py`: `record_tags` with the Week ≥ 4 gate, the 8-day staleness gate and thresholds; `win_rate` (BR-G4–G6)

## Provider: API-Sports

- [ ] Adapter `games_on_date` and `standings`; reserved-budget path for final confirmation; status mapping for halftime and final/OT

## Scores modes (TDD §10.4)

- [ ] `live`, `replay`, `auto`; replay files in `backend/data/replays/`; recorder and `cli export-replay`; production refuses anything but `live`
- [ ] Replay games marked `is_sample` and excluded from alerts, Watches and plans

## API and frontend

- [ ] `GET /games/live` (in progress plus recent finals for favorites); scores, records and division rank in game responses
- [ ] Home "Live now" and "Recent finals"; `ScoreStrip` with the 600 ms pulse; "Scores paused" banner; "Delayed" tag; sample-data banner; records and division rank on cards and game detail (UI/UX §6.1–6.4, §7.3)
- [ ] Refresh every 5 minutes while visible, on screen focus and app foreground, and with pull-to-refresh (FR-LS11)

## Tests

- [ ] Unit with frozen time: polling windows, UTC-midnight windows, season rollover, scores mode switching (AC-46); every record tag at its boundaries (AC-42)
- [ ] Integration: no polls outside windows and budget never exceeded (AC-31); 100 simulated viewers make the same provider requests as one (AC-33); unmatched records never shown (AC-36); full replay (AC-38); standings at most once a day (AC-41)
- [ ] Agent: "How are the Bears doing?" during a game (Appendix A-14)

## Exit criteria

J8 complete; AC-30–AC-33, AC-36–AC-37 and AC-41–AC-46 pass.
