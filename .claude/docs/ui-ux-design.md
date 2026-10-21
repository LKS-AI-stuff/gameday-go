# GameDay Go — UI/UX Design Document

| | |
|---|---|
| **Product** | GameDay Go |
| **Document type** | UI/UX Design |
| **Version** | 0.3 (draft) |
| **Date** | 2026-10-21 |
| **Builds on** | BRD v0.15 (`business-requirements.md`), Technical Design v0.7 §4 (`technical-design.md`) |
| **Visual reference** | `.claude/docs/Template/` (Nicepage "Modern Football Team" template): direction only, no assets reused |

This document defines what each screen shows, how it's laid out, how it behaves, and what it looks like in every state (loading, empty, error, limited). Design tokens (colors, type, spacing, motion) are defined in Technical Design §4.4 and referenced here by name (e.g. `color.primary`, `type.h2`). Requirement IDs refer to the BRD.

Wireframes are low-fidelity ASCII sketches of **mobile** layouts unless marked otherwise. They show structure and priority, not final visuals.

---

## 1. Design Principles

1. **Planner first.** Every main screen leads toward one question: *how should I experience this game?* Scores and stats support that; they never dominate.
2. **Honest by default.** Every price, score, record and venue detail shows where it came from and how fresh it is. Unknowns are labeled, never hidden (BRD principle 3).
3. **Glanceable.** A fan should understand a game card or Plan Card in under three seconds: matchup, when, where, and what to do.
4. **Bold, not loud.** The template's style (dark surfaces, condensed uppercase headings, one strong accent) used with restraint. Orange-red marks the single most important action or recommendation on a screen.
5. **Calm proactivity.** Alerts and prompts are few and specific. No badges or banners for things that don't need action.
6. **Accessible everywhere.** WCAG 2.1 AA on web, platform accessibility on iOS and Android, reduce-motion respected (NFR-3).

## 2. Information Architecture and Navigation

### 2.1 Structure

```text
Auth ── Sign in / Sign up ── Verify email ── Age confirmation
  │
Onboarding (6 steps + review)
  │
Main app
├── Home                    next games, live now, recent finals
├── Schedule                season by week, team filter
│     └── Game detail       matchup, records, tags, score, plan / watch, tickets, bars
├── Plan                    agent sessions
│     ├── Session (chat)    messages, live trace, Plan Cards, proposals
│     └── Trace             full step timeline for one run
├── My Game Days            Plans | Alerts
│     ├── Saved plan detail
│     └── Watch detail / edit
├── Inbox                   alert history
└── Settings                preferences, notifications, appearance, account, about
```

### 2.2 Navigation patterns

| | Mobile (iOS/Android) | Web, < 1024 px | Web, ≥ 1024 px |
|---|---|---|---|
| Primary nav | Bottom tabs: **Home, Schedule, Plan, My Game Days** | Same bottom tabs | Left navigation rail with the same four items |
| Inbox | Bell icon with badge, top-right of the app bar | Same | Rail item with badge |
| Settings | Avatar/gear icon, top-right | Same | Rail item (bottom) |
| Game detail | Pushed screen with back button | Same | Opens in the main column; "Plan this game" can open the agent in a right-side panel |
| Agent session | Full screen | Full screen | Two columns: chat (left), trace or Plan Card detail (right) |

Tab labels use `type.label` (Oswald, uppercase). The active tab uses `color.primary`.

### 2.3 Entry points into planning

1. **Game detail → "Plan this game"** (preselects the game) — primary path.
2. **Plan tab → "New plan"** with suggested prompts ("Plan my Sunday", "Cheapest way to watch the Bears this week").
3. **Home → game card overflow → "Plan this game."**
4. **Saved plan → "Refresh plan."**

## 3. Layout and Responsiveness

| Breakpoint | Width | Columns | Gutters / side margin | Notes |
|---|---|---|---|---|
| Phone | < 600 px | 1 | 16 px | Default design target |
| Tablet / small web | 600–1023 px | 1–2 | 24 px | Game cards in a 2-column grid |
| Desktop web | ≥ 1024 px | Rail + content (max 1200 px) | 32 px | Game cards 3 across (like the template's match row); game detail in 2 columns |

- Minimum touch target 44 × 44 pt (iOS) / 48 × 48 dp (Android and web).
- Content never runs edge to edge on desktop: max reading width 720 px for chat and text.
- Safe areas respected on mobile; the chat composer sits above the keyboard.

## 4. Visual Language (summary)

Full token tables are in Technical Design §4.4. In practice:

- **Surfaces:** dark theme is the signature look (template style): `color.background` `#111111`, cards on `color.surface` `#1A1A1A`. Light theme mirrors it with white cards on `#F5F5F5`. Theme follows the OS by default; users can override in Settings.
- **Accent:** `color.primary` (`#F0502A`) for the main action, the recommended option and the active tab. Never more than one primary button per screen. Text and icons on a primary fill use `color.onPrimary` (`#111111`), which passes AA at every size (white on this orange is only about 3.3:1).
- **Terminology:** users see **"Alerts"** ("Set an alert", the Alerts tab). "Watch" remains the internal term in code, the API and the BRD.
- **Semantic colors:** `color.live` (yellow) only for in-progress games; `color.success` (teal) for "within budget", "Alert active"; `color.info` (blue) for links and info banners; `color.danger` for errors and destructive actions.
- **Typography:** Oswald uppercase for screen titles, section titles, labels and scores; Open Sans for everything people read in sentences.
- **Shape:** near-square corners (Paper roundness 2), thin `color.outline` dividers, minimal shadows.
- **Imagery:** no photos and no team logos in the MVP (A12). Heroes use a dark gradient with a subtle field-line pattern drawn in code. Team identity comes from text (abbreviation + name).
- **Iconography:** MaterialCommunityIcons (Paper's default set), outlined style, 24 px.

## 5. Global Patterns

### 5.1 Data freshness line

Every block of external data ends with a one-line caption in `type.caption`, `color.textMuted`:

```text
Ticketmaster · listed price range · updated 6 min ago
API-Sports · updated 52 min ago · Delayed
Google Places · hours may change · call ahead
```

- Relative time under 24 h ("6 min ago"), then absolute ("Oct 12, 3:40 PM CT").
- Tapping the line on mobile shows a tooltip/sheet with the exact timestamp and source (FR-LS3, FR-T2, FR-V2).

### 5.2 Badges and notices

| Element | When | Look |
|---|---|---|
| `SampleDataBadge` | Any `is_sample` data (score replay, fixtures) | Small outlined chip "SAMPLE DATA", `color.info` |
| "Delayed" tag | Provider marks scores delayed | Caption-sized tag next to the score |
| `Banner`: Scores paused | Score budget exhausted or provider failing (FR-LS8) | Paper `Banner`, info style: "Scores are paused. Showing the last update from 3:12 PM." |
| `Banner`: Provider unavailable | Kill switch or outage (FR-O5) | "Ticket data is temporarily unavailable. Try again later." |
| `PlanningWindowNotice` | Game more than 30 days out (FR-SC8) | Inline notice with calendar icon: "Planning opens on Oct 18." Replaces the plan/watch buttons |
| Call-ahead notice | Every venue (FR-V3) | Caption with phone icon: "Call ahead to confirm they're showing the game." |
| Not affiliated note | Settings › About, sign-in footer, emails (NFR-17) | "GameDay Go is not affiliated with the NFL or any team." |

### 5.3 Loading, empty and error states (standard components)

| Component | Use | Spec |
|---|---|---|
| `Skeleton` | First load of any list or card | Shape-matched grey blocks with a soft shimmer (no shimmer when reduce motion is on). Shown only if loading takes > 300 ms |
| `InlineSpinner` | Refetch, pull-to-refresh, button in progress | Paper `ActivityIndicator`, small |
| `EmptyState` | Nothing to show | Icon (48 px, muted), one-line title (`type.h3`), one sentence, at most one action button |
| `ErrorState` | Request failed | Icon, plain-language title, short reason, **Try again** button. Never shows raw error codes; a "Details" link reveals the request ID for support |
| `OfflineBanner` | No connectivity | Top banner: "You're offline. Showing saved data." Cached TanStack Query data stays visible |
| `Snackbar` | Confirmations and undo | "Plan saved" / "Alert paused · Undo", 4 s |

Rules:
- Cached data is always preferred over a spinner. Refetches never blank the screen.
- Errors are scoped: one failing section (e.g. tickets) shows its own `ErrorState`, the rest of the screen still works (NFR-11).
- Empty states explain **why** and **what next**, never just "No data."

### 5.4 Confirmations

| Action | Pattern |
|---|---|
| Agent proposal (save plan, create Watch) | Buttons on the Plan Card; tapping creates the item and shows a Snackbar (FR-AG8) |
| Delete plan / Watch | Snackbar with Undo (5 s), no dialog |
| Delete account | Paper `Dialog`: explains what's deleted, requires typing `DELETE` (FR-A4) |
| Change preferences from the agent | Never automatic; agent suggests, user edits in Settings (FR-P5) |
| Sign out | No confirmation |

### 5.5 Formatting

| Item | Format | Example |
|---|---|---|
| Kickoff | Day, date · time + zone abbreviation (NFR-4) | `SUN, NOV 8 · 12:00 PM CT` (cards, uppercase label) / `Sun, Nov 8 · 12:00 PM CT` (sentences) |
| TBD kickoff | Literal | `SUN, NOV 8 · TIME TBD` |
| Matchup | `AWAY @ HOME` | `BEARS @ PACKERS` |
| TBD team | Placeholder text | `AFC WILD CARD WINNER @ CHIEFS` |
| Record | W–L or W–L–T (ties only if non-zero) | `7–1`, `6–2–1` |
| Price | Whole dollars, "from" for minimums | `From $120`, `$120–$340`, `Price not available` |
| Estimated total | Labeled estimate | `≈ $480 for 4 (estimate)` |
| Distance | 1 decimal under 10 mi, whole above | `0.8 mi`, `185 mi` |
| Score | Oswald tabular figures | `24 – 17` |

### 5.6 Refresh behavior

- Score views (Home "Live now", game detail score strip) reload from the GameDay Go backend on a configurable interval while visible (`EXPO_PUBLIC_SCORE_REFRESH_SEC`, default 300 = every 5 minutes; FR-LS11, TDD §21.2). These reloads read the backend's cache only, so they cost no provider quota and keep the screen within a few minutes of the backend's hourly score updates. They also reload whenever the screen is opened or the app returns to the foreground, and every list supports pull-to-refresh. Refreshing never blanks the screen (§5.3).
- Ticket and venue sections refresh when their section is opened, not on a timer (saves provider quota).

### 5.7 Motion (from TDD §4.4)

- Entering content: fade + 12 px rise, 300 ms, ease-out; lists stagger 50 ms; first mount only.
- Score changes: 600 ms highlight pulse on the changed number.
- Trace steps: slide in, 200 ms, as they stream.
- Plan Card arrival: fade + scale from 0.98, 250 ms.
- Reduce motion: all disabled; state changes are instant.

## 6. Component Specifications

### 6.1 `GameCard`

The template's "upcoming match" card, adapted.

```text
┌──────────────────────────────────────────┐
│ SUN, NOV 8 · 12:00 PM CT        [LIVE ●] │  ← date label (type.label); status pill when live/final
│                                          │
│ BEARS        3–5                         │  ← team name (type.h3) + record
│ @ PACKERS    6–2                         │
│                                          │
│ Lambeau Field · Green Bay, WI            │  ← venue (type.body, muted)
│ [DIVISION RIVALRY] [PRIMETIME]           │  ← up to 2 TagChips, "+1" overflow
│──────────────────────────────────────────│
│ 180 mi away            PLAN THIS GAME  › │  ← distance from home + primary text action
└──────────────────────────────────────────┘
```

| Variant | Differences |
|---|---|
| Upcoming, in window | As above; footer action "PLAN THIS GAME" |
| Upcoming, outside window | Footer shows `PlanningWindowNotice` ("Planning opens Oct 18") instead of the action |
| Saved | Small bookmark icon next to the date; footer "VIEW PLAN" |
| Live | Status pill `LIVE` in `color.live`; scores replace records in `type.score`; quarter/clock caption; freshness line |
| Final | Status `FINAL` / `FINAL/OT`; final score; winner in full-strength text, loser muted |
| TBD teams | Placeholder names, no records, tags limited to "PLAYOFF GAME" |
| Postponed / cancelled | Status pill in `color.danger`; kickoff struck through with new time if known |
| Sample | `SampleDataBadge` in the header row |

Accessibility label (single read-out): "Bears at Packers, Sunday November 8, 12 PM Central, Lambeau Field, division rivalry. Plan this game."

### 6.2 `MatchupHero` (game detail header)

Template hero, without photography.

```text
┌──────────────────────────────────────────┐
│ ‹ Back                         ☆ Alert   │
│                                          │
│  WEEK 9 · SUNDAY NIGHT                   │  ← type.label, muted
│  BEARS                                   │  ← type.display
│  @ PACKERS                               │
│  3–5 · 2nd NFC North   6–2 · 1st NFC N.  │  ← RecordBadges + division rank (FR-ST4)
│  SUN, NOV 8 · 7:20 PM CT                 │
│  Lambeau Field · Green Bay, WI · 180 mi  │
│  [DIVISION RIVALRY] [PRIMETIME]          │
│  Records as of Tue 6:00 AM               │  ← freshness line
└──────────────────────────────────────────┘
   dark gradient + field-line pattern, color.overlay
```

When the game is live or final, a `ScoreStrip` sits directly under the hero.

### 6.3 `ScoreStrip`

```text
┌──────────────────────────────────────────┐
│  BEARS  17   –   24  PACKERS     Q4 2:31 │
│  API-Sports · updated 41 min ago         │
└──────────────────────────────────────────┘
```

- Live: `color.live` left border. Final: no border, "FINAL" label.
- Updates pulse the changed number. Screen readers announce score changes politely, at most once per update.
- Scores paused: shows the last known score plus the "Scores paused" banner (FR-LS8).

### 6.4 `TagChip` and `RecordBadge`

| Tag weight | Style |
|---|---|
| High (Playoff game, Division rivalry, Featured rivalry, Division leaders meet, Top-record matchup, Late-season division race) | Outlined, `color.primaryText` border and text |
| Medium (Primetime, Home opener / finale, Winning-record matchup) | Outlined, `color.outline` border, `color.text` |
| Informational (International game, Lopsided matchup) | Text-only, muted |

Tapping a tag opens a small sheet explaining it in one sentence (e.g. "Both teams lead their divisions, per API-Sports standings as of Tue 6:00 AM").

`RecordBadge`: `7–1` in Oswald, with optional "1st NFC West" caption on game detail.

### 6.5 `PlanCard`

The template's orange-red highlighted block becomes the recommended option.

```text
┌──────────────────────────────────────────┐
│████ RECOMMENDED █████████████████████████│  ← filled color.primary band, dark label text
│ WATCH AT KELLY'S PUB                     │  ← type.h2
│ 0.8 mi · open at kickoff                 │
│ • Your favorite way to watch             │  ← reasons (max 4)
│ • No tickets or travel needed            │
│ • Away game is outside your area (180mi) │
│ Trade-off: bar hasn't confirmed it's     │  ← trade-offs (max 3), muted
│ showing the game. Call ahead.            │
│ [Call]  [Website]  [Map]                 │  ← links (outbound icon)
│──────────────────────────────────────────│
│ ALTERNATIVES                             │
│ ▸ Watch at home · free                   │  ← collapsed rows; expand for reasons
│ ▸ Go to Lambeau · not recommended:       │
│   outside your travel area (180 mi)      │
│──────────────────────────────────────────│
│ Assumes: party of 1.                     │  ← assumptions
│ Google Places · updated 2 min ago        │  ← facts_as_of lines
│ API-Sports · schedule updated today      │
│──────────────────────────────────────────│
│ [ SAVE PLAN ]                            │  ← proposal button; a "Set a ticket alert" text button appears when tickets are relevant
│                         View trace ›     │
└──────────────────────────────────────────┘
```

- The raw score isn't shown to users by default (BRD: reasons over numbers). It appears only in the trace.
- `limitations` render as an info box above the actions: "Ticket prices weren't available for this game."
- Excluded options appear under Alternatives with the reason in plain words, so the user sees the rules at work (e.g. "Over your $90 max").
- Saved-plan view: same card, header adds "Saved Oct 12 · Refresh plan".

### 6.6 `TraceTimeline`

```text
 ● Understood: plan Bears @ Packers on Sunday            0.4s
 │
 ● Checked travel rule                                   ✓
 │  Low travel → Lambeau Field is 180 mi, outside 75 mi.
 │  Stadium option excluded.                         FILTERED
 │
 ● Searched nearby sports bars (near 60601)             1.2s
 │  6 found, 4 open at kickoff                       SUCCESS
 │
 ● Ranked options: bar 0.94 · home 0.84                  ✓
 │
 ● Wrote recommendation                                  2.1s
 ─────────────────────────────────────────────────────────────
 5 steps · 2 tool calls · 4.6 s · ≈ $0.004
```

| Status | Icon / color |
|---|---|
| success | filled dot, `color.success` |
| empty | hollow dot, muted, "No results" |
| filtered | funnel icon, `color.primaryText` |
| failed | alert icon, `color.danger`, short reason |
| limit | stop icon, `color.info`, "Run limit reached: answered with what was found" |

- In chat, the trace streams as a **compact strip** (current step only, e.g. "Searching nearby bars…") with "Show steps" to expand inline.
- The full timeline screen adds totals (FR-TR6). Steps are expandable for detail (redacted, FR-TR5).
- Screen readers: each new step is announced politely ("Searching nearby bars").

### 6.7 `ChatComposer`

```text
┌──────────────────────────────────────────┐
│ Ask about a game, tickets or bars…    ➤ │
└──────────────────────────────────────────┘
  4 messages left in this plan
```

- Turns-remaining hint appears from 5 left (FR-AG13). At 0: composer replaced by "This plan has reached its limit. [START A NEW PLAN]".
- While a run is active the send button becomes **Stop** (FR-AG12).
- Suggested prompts (chips) show above the composer in an empty session.
- Device location: a location-pin toggle "Use my current location for bars" (asks permission on first use, FR-P3).

### 6.8 Other components

| Component | Spec |
|---|---|
| `WatchRow` | Type icon, game summary, condition ("Tickets ≤ $90"), status chip (Active / Paused / Triggered / Expired / Having trouble checking), last checked. Swipe or overflow: Pause/Resume, Delete |
| `InboxItem` | Category icon, title, one-line body, relative time, unread dot. Tap → linked screen |
| `PreferenceSelector` | Paper `SegmentedButtons` with a one-line helper under the selected option |
| `TeamPicker` | Grid of team tiles grouped by division (8 groups of 4), multi-select with check marks; search field on top |
| `ZipField` | Numeric input, validates against the ZIP dataset as you type 5 digits, shows "Chicago, IL" confirmation; "Use my location" text button |

## 7. Screens

Each screen lists its purpose, layout, actions and states.

### 7.1 Sign in / Sign up (FR-A1–A3, FR-O11)

```text
┌──────────────────────────────┐
│                              │
│   GAMEDAY GO                 │  type.display, wordmark
│   Your NFL game day, planned.│
│                              │
│   [ Continue with Google ]   │  ← M6
│   ─────────── or ─────────── │
│   Email  [               ]   │
│   Password [             ]   │
│   [ SIGN IN ]                │
│   New here? Create account   │
│                              │
│   Not affiliated with the NFL│
└──────────────────────────────┘
```

- **Sign up** adds: confirm password, checkbox "I'm 18 or older" (required, FR-A3), links to privacy notice.
- **Age confirmation screen** (M6; social sign-in only, first sign-in): title "ONE MORE THING", checkbox "I'm 18 or older", privacy notice link, button "CONTINUE" (disabled until checked). Shown before onboarding; the app can't be used until it's confirmed. Email sign-ups skip it because they confirmed on the sign-up form (TDD §6).
- **Verify email screen:** "Check your inbox at ben@… to verify your account." Buttons: "I've verified, sign in" (primary), "Resend email" (with 60 s cooldown), "Use a different email." The verification link opens the web app, which signs the user in there; on a phone the user returns to the app and signs in.

| State | Behavior |
|---|---|
| Loading | Button spinner; inputs disabled |
| Error | Inline under the field ("Incorrect email or password"); network errors as Snackbar |
| Unverified sign-in attempt | Routes to Verify email screen |

### 7.2 Onboarding (FR-P1, AC-1, SM1 < 90 s)

Six steps, one question each, progress bar at top, "Back" and "Next". Defaults pre-selected where the BRD allows, so most steps are one tap.

```text
┌──────────────────────────────┐
│ ▬▬▬▬▬▬▬▬░░░░░░░░  Step 3 of 6│
│                              │
│ HOW FAR WILL YOU GO FOR      │
│ A GAME?                      │
│                              │
│ [ LOW ][ MEDIUM ][ HIGH ]    │
│                              │
│ Medium: we'll suggest trips  │
│ for big games, like playoffs │
│ and rivalries.               │
│                              │
│              [ NEXT ]        │
└──────────────────────────────┘
```

| Step | Question | Control | Default | Helper text examples |
|---|---|---|---|---|
| 1 | Who do you root for? | `TeamPicker` (≥ 1) | none | "Pick as many as you like." |
| 2 | Where's home? | `ZipField` + "Use my location" | none | "We use this for nearby bars and travel distance." |
| 3 | How far will you go for a game? | Segmented Low/Medium/High | Medium | Low: "Local games only (within 75 mi)." High: "Road trips for any game that fits." |
| 4 | How do you like to spend? | Segmented Less/Medium/More + optional "Set a max ticket price" | Medium | "Your max is a hard limit. We never show tickets above it." |
| 5 | How do you like to watch? | 4 option cards: Stadium / Sports bar / Home / Flexible | Flexible | — |
| 6 | How often should we email you? | Segmented Off/Low/Medium/High | Medium | Medium: "Alerts you set up, schedule changes and game-day reminders." |
| Review | Summary of all six with "Edit" links | — | — | Button: "START PLANNING" |

| State | Behavior |
|---|---|
| ZIP not found | Inline: "We couldn't find that ZIP. Check the 5 digits." |
| Location denied | Inline: "No problem, enter your ZIP instead." |
| Save fails | Stay on Review, Snackbar with "Try again" |

### 7.3 Home (FR-SC1, FR-LS4)

```text
┌──────────────────────────────┐
│ GAMEDAY GO           🔔2  ⚙ │
│                              │
│ LIVE NOW                     │  ← only when a favorite-team game is live
│ ┌──────────────────────────┐ │
│ │ BEARS 17 – 24 PACKERS    │ │
│ │ Q4 2:31 · updated 41m ago│ │
│ └──────────────────────────┘ │
│                              │
│ YOUR NEXT GAMES              │
│ [GameCard]                   │
│ [GameCard]                   │
│ [GameCard]                   │
│                              │
│ RECENT FINALS                │
│ Bears 20 – 27 Lions  FINAL   │
│ Cowboys 31 – 14 Giants FINAL │
└──────────────────────────────┘
```

- "Your next games": next game per favorite team, sorted by kickoff, max 5. Saved games show the bookmark.
- Desktop: GameCards in a 3-column row (template match row).

| State | Behavior |
|---|---|
| Loading | Skeleton cards (3) |
| No live game | "Live now" section hidden entirely |
| Schedule not released (FR-O1c) | `EmptyState`: calendar icon, "Next season's schedule isn't out yet", "We'll be ready to plan as soon as it's released." No actions |
| No upcoming games for favorites (e.g. eliminated, season over) | `EmptyState`: "No more games for your teams this season." Action: "Browse schedule" |
| Error | `ErrorState` for the section; cached cards stay visible |
| Sample replay active | Live card shows `SampleDataBadge` |

### 7.4 Schedule (FR-SC2)

```text
┌──────────────────────────────┐
│ SCHEDULE                     │
│ ‹ WK 8 [WK 9] WK 10 WK 11 ›  │  ← horizontally scrolling week chips; current week selected
│ [All teams ▾] [My teams]     │  ← team filter chip + quick toggle
│                              │
│ THURSDAY, NOV 5              │  ← day group headers
│ [GameCard compact]           │
│ SUNDAY, NOV 8                │
│ [GameCard compact]           │
│ [GameCard compact]           │
│ …                            │
└──────────────────────────────┘
```

- Compact GameCard: single-line matchup, time, tags as dots; tap for detail.
- Playoff weeks labeled "WILD CARD", "DIVISIONAL", "CONF. CHAMPIONSHIPS", "SUPER BOWL".

| State | Behavior |
|---|---|
| Loading | Skeleton rows |
| Filter returns nothing (bye week) | "The Bears have a bye in Week 9." Action: "Next game ›" |
| Schedule not released | Same empty state as Home |

### 7.5 Game detail (FR-SC3–SC8, FR-T, FR-V, FR-ST4, FR-LS)

```text
┌──────────────────────────────┐
│ [MatchupHero]                │
│ [ScoreStrip]  (live/final)   │
│                              │
│ [ PLAN THIS GAME ]           │  ← primary; or PlanningWindowNotice
│ [ SET AN ALERT ]             │  ← creates an alert (Watch) via sheet
│                              │
│ TICKETS                      │
│ Ticketmaster · on sale       │
│ From $65 · listed price      │
│ range, fees may apply        │
│ [ View on Ticketmaster ↗ ]   │
│ Fits your $90 max            │  ← budget fit (color.success)
│ updated 3 min ago            │
│                              │
│ NEARBY SPORTS BARS           │
│ Kelly's Pub · 0.8 mi · open  │
│ The Dugout · 1.4 mi · hours? │
│ Call ahead to confirm…       │
│ See all ›                    │
│                              │
│ ABOUT THIS GAME              │
│ Tags explained, venue, source│
└──────────────────────────────┘
```

- Desktop: two columns. Left: hero, score, plan action, About. Right: Tickets, Bars.
- Tickets and bars load lazily when their section scrolls into view (saves quota). Each section has its own states.
- Distance/travel hint under the hero: "Outside your travel area (Low)" in muted text when relevant, so the rule is visible before planning.

| State | Tickets section | Bars section |
|---|---|---|
| Loading | Skeleton (2 lines) | Skeleton (3 rows) |
| No event found | "No ticket listings found for this game yet." Action: "Set availability alert" | — |
| Price not provided | "On sale · Price not available" (BR-S5) | — |
| Over max | "Listed prices start above your $90 max." Action: "Alert me under $90". Ticketmaster gives one price range per game, so the whole event is filtered (BR-S4) | — |
| None nearby | — | "No sports bars found within 5 mi of 60601." Action: "Search wider" |
| Provider down / budget out | Banner "Ticket data is temporarily unavailable." | Banner "Venue search is unavailable right now." |
| Outside planning window | Section hidden; `PlanningWindowNotice` shown once near the top | Hidden |
| Game final | Sections hidden; final score and "Game over" | Hidden |

### 7.6 Plan (agent sessions) (FR-AG1–AG13)

**Session list** (Plan tab root):

```text
┌──────────────────────────────┐
│ PLAN                [+ NEW]  │
│                              │
│ Bears @ Packers · Sun        │
│ "Something cheaper?" · 2h    │
│ Cowboys vs Eagles · Nov 15   │
│ "Worth the trip?" · Yesterday│
└──────────────────────────────┘
```

- Empty: `EmptyState` "Plan your next game day" with suggested prompt chips and "NEW PLAN".
- Sessions older than 90 days disappear (FR-AG11).

**Session (chat):**

```text
┌──────────────────────────────┐
│ ‹  BEARS @ PACKERS     ⋯    │
│                              │
│              Plan my Sunday ▸│  ← user bubble (right, surfaceRaised)
│                              │
│ ◐ Checking travel rules…     │  ← compact live trace strip
│   Show steps ▾               │
│                              │
│ [PlanCard]                   │  ← streamed in when ready
│                              │
│              Something       │
│              cheaper? ▸      │
│ …                            │
│ [ChatComposer]               │
│ 4 messages left in this plan │
└──────────────────────────────┘
```

- Assistant text appears progressively (streaming, FR-AG10); the Plan Card fades in when complete.
- **Clarifying question** (FR-AG6): shown as a message with tappable choice chips, e.g. `[Week 9 vs Packers] [Week 12 vs Lions]`.
- **Proposals:** buttons on the Plan Card; after tapping, the button changes to "✓ Saved" (only after the API confirms, FR-AG9).
- Overflow menu: "View full trace", "Start a new plan", "Delete session".

| State | Behavior |
|---|---|
| Waiting for first trace step | Typing indicator (3 dots) within 300 ms of send |
| Run limit reached (AC-16) | Plan Card with limitation box: "I hit my step limit, so this plan may be incomplete." |
| Run failed | Assistant message: "Something went wrong while planning." Button "Try again" (resends) |
| Cancelled | "Stopped. Here's what I had so far." + partial card if any |
| Game outside window | Assistant explains: "Planning for this game opens on Oct 18." with "Remind me" disabled (no offseason features) |
| Daily limit (M6, FR-O8) | "You've reached today's planning limit. Try again tomorrow." Composer disabled |
| Session limit (FR-AG13) | Composer replaced by "START A NEW PLAN" |
| Agent unavailable (kill switch / spend cap) | Banner at top of Plan tab: "Planning is unavailable right now. You can still browse games." |
| Connection lost during stream | Banner "Reconnecting…"; on reconnect, the run's result is fetched (TDD §11.1) |

### 7.7 Trace (FR-TR1–TR6)

Full-screen `TraceTimeline` for one run, title "HOW THIS PLAN WAS MADE". Desktop: right-hand panel next to the chat.

| State | Behavior |
|---|---|
| Run still active | Steps stream in; totals show "In progress" |
| Old run (expired) | "This trace is no longer available." |

### 7.8 My Game Days (FR-SP1–SP3, FR-W5–W6)

```text
┌──────────────────────────────┐
│ MY GAME DAYS                 │
│ [ PLANS ][ ALERTS ]          │  ← segmented
│                              │
│ SUN, NOV 8                   │
│ Bears @ Packers              │
│ Kelly's Pub · reminder 3h ⏰ │
│                              │
│ SUN, NOV 15                  │
│ Cowboys vs Eagles            │
│ Watch at home                │
└──────────────────────────────┘
```

**Saved plan detail:** the saved Plan Card snapshot (with its original freshness lines), header "Saved Oct 12", actions: "REFRESH PLAN" (re-runs the agent in a new session with the game preselected), reminder control ("Remind me 3 hours before", options 1/3/6/24 h or Off; FR-SP4. At notification level Low or Off it reads "Reminders need notification level Medium or higher" with a link to Settings), "Delete plan" (Snackbar undo). If kickoff changed since saving: info banner "Kickoff moved to 3:25 PM CT."

| State | Behavior |
|---|---|
| No plans | "No game days planned yet." Action: "Plan a game" |
| Past games | Collapsed "Past game days" section; read-only |

### 7.9 Alerts (Watches, FR-W1–W11)

**List** (My Game Days › Alerts): `WatchRow`s grouped by status: Active, Paused, Triggered/Expired (collapsed).

**Create Watch sheet** (from game detail or a proposal):

```text
┌──────────────────────────────┐
│ SET AN ALERT                 │
│ Bears @ Packers · Sun, Nov 8 │
│                              │
│ ( ) Tickets at or under  $[90]│
│ ( ) Tickets become available │
│                              │
│ ☐ Keep watching after it     │
│   triggers (until kickoff)   │
│                              │
│ We'll email you and add it to│
│ your inbox. Expires at       │
│ kickoff.                     │
│               [ CREATE ]     │
└──────────────────────────────┘
```

- If the user's notification level is Off or the category is disabled, the sheet says: "Email is off for alerts. You'll only see this in your inbox. Change in Settings."
- Limit reached (10 active, FR-W7): CREATE disabled with "You have 10 active alerts. Pause or delete one first."

| State | Behavior |
|---|---|
| No alerts | "No alerts set. Set one from a game's page." |
| Having trouble checking (FR-W11) | Row status chip in `color.danger` + "We'll keep trying." |

### 7.10 Inbox (FR-N1)

```text
┌──────────────────────────────┐
│ INBOX           Mark all read│
│ ● Tickets under $90          │
│   Bears @ Packers · from $85 │
│   12 min ago                 │
│   Kickoff moved              │
│   Cowboys vs Eagles now 3:25 │
│   Yesterday                  │
└──────────────────────────────┘
```

- Categories: Watch hit (ticket icon), Schedule change (calendar icon), Reminder (alarm icon), Digest (list icon).
- Empty: "You're all caught up."

### 7.11 Settings (FR-P2, BR-N9, FR-A4, NFR-5, NFR-17)

```text
SETTINGS
  PREFERENCES
    Favorite teams        Bears, Lions ›
    Home ZIP              60601 ›
    Travel                Low ›
    Spending              Less · max $90 ›
    Viewing               Sports bar ›
  NOTIFICATIONS
    Email level           Medium ›
    Alert emails          [on]
    Schedule changes      [on]
    Game-day reminders    [on]
    Weekly digest         (High only)
    Time zone             America/Chicago ›
  APPEARANCE
    Theme                 System / Dark / Light
  ACCOUNT
    Email                 ben@example.com
    Sign out
    Delete account
  ABOUT
    Data sources & attribution (API-Sports, Ticketmaster, Google, OpenAI)
    Privacy notice
    Not affiliated with the NFL or any team
    Version 1.0.0
```

- Each preference opens the same control used in onboarding, with a short note: "Changes apply to new plans. Saved plans stay as they are" (FR-P4).
- Email disabled after a bounce (FR-N6): banner "Emails to ben@… bounced. Update your email to turn alerts back on."

### 7.12 Alert email (FR-N2–N3)

```text
Subject: Tickets for Bears @ Packers are now from $85

GAMEDAY GO                                   (wordmark, dark header bar)

Tickets dropped under your $90 alert.
BEARS @ PACKERS · SUN, NOV 8 · 12:00 PM CT · Lambeau Field

From $85 · listed price range, fees may apply
[ VIEW GAME ]  (primary button → deep link)

Why you got this: you set a ticket alert for this game.
Source: Ticketmaster · checked 3:40 PM CT

Unsubscribe from ticket alerts · Manage email settings
GameDay Go · not affiliated with the NFL · <sender address line>
```

- Same template for all categories; plain-text alternative included.
- Dark header bar with `color.primary` button; body on white for email client compatibility.

### 7.13 Local reminder (FR-N7–N9)

```text
GameDay Go
Bears @ Packers at 12:00 PM CT · your plan: Kelly's Pub
```

Tapping opens the saved plan.

## 8. Content and Microcopy

### 8.1 Voice

- Confident, short, fan-friendly. Like a knowledgeable friend, not a hype machine.
- Second person ("your game day"), active voice, no exclamation marks in system messages.
- State facts plainly, label assumptions plainly: "Assumes a party of 1." "Hours not listed."

### 8.2 Standard strings

| Situation | Copy |
|---|---|
| Price unknown | "Price not available" |
| Price label | "Listed price range, fees may apply" |
| Budget filtering | "Listed prices start above your ${max} max" |
| Venue confirmation | "Call ahead to confirm they're showing the game." |
| Hours unknown | "Hours not listed" |
| Outside travel area | "Outside your travel area ({level})" |
| Planning window | "Planning opens on {date}." |
| Scores paused | "Scores are paused. Showing the last update from {time}." |
| Provider down | "{Ticket data / Venue search / Planning} is temporarily unavailable." |
| Sample data | "Sample data" |
| Schedule not out | "Next season's schedule isn't out yet." |
| Session limit | "This plan has reached its limit. Start a new plan to keep going." |
| Generic error | "Something went wrong. Try again." |

### 8.3 Words to avoid

"Guaranteed", "best price", "must-win", "playoff implications", "clinch" (BR-G1), "AI" in user-facing labels (say "your planner"), and any team or league trademarks used as branding.

## 9. Accessibility Checklist

- [ ] Text contrast ≥ 4.5:1 (≥ 3:1 for large/bold text); text on a `color.primary` fill always uses `color.onPrimary` (`#111111`), never white.
- [ ] All interactive elements have accessible names; icons-only buttons have labels ("Inbox, 2 unread").
- [ ] Logical focus order; visible focus ring on web (`color.info`, 2 px).
- [ ] Full keyboard operation on web, including chat send (Enter) and newline (Shift+Enter).
- [ ] Dynamic type / font scaling up to 200% without clipping; cards grow vertically.
- [ ] Live regions: agent trace steps and score updates announced politely, never assertively.
- [ ] Reduce motion disables all animation (§5.7).
- [ ] Status never conveyed by color alone (icons + text on chips and pills).
- [ ] Touch targets ≥ 44/48.
- [ ] Time zone always shown with times.

## 10. Prototype Flows for Review

1. **First run:** sign up → verify email → onboarding (6 steps) → Home. Target < 90 s from verified sign-in to Home (SM1).
2. **Plan a game:** Home → GameCard → Game detail → Plan this game → Plan Card → Save plan → My Game Days.
3. **Refine:** in session, "Something cheaper?" → updated Plan Card with what changed.
4. **Set an alert:** Plan Card "Set a ticket alert" → Snackbar → Alerts list → (email arrives) → Inbox → Game detail.
5. **Game day:** local reminder → saved plan → game detail with live score.

## 11. Open Design Questions

| ID | Question | Proposed default |
|---|---|---|
| UX1 | Wordmark / app icon | Text wordmark "GAMEDAY GO" in Oswald; icon: orange-red square with a white "GG" monogram. Designed in M0 |
| UX2 | Hero imagery | No photos in MVP (gradient + field lines). Revisit with properly licensed generic stadium photos later |
| UX3 | Default theme | Follow the OS; dark theme is the reference look for screenshots and the demo |
| UX4 | Team color accents | None (A12: neutral styling); team identity by text only |
| UX5 | Empty-state illustrations | Icons only in MVP |
| UX6 | Visual mockups | Done: clickable mockup of Home, Schedule, Game detail, Plan session, Trace and My Game Days (dark theme), approved 2026-10-14: https://claude.ai/artifact/8URqVFmbGDbwAC3sSk8saS |
