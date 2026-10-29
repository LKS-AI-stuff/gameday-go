// Display formatting (UI/UX §5.5). Times arrive as UTC ISO-8601 and are always shown with a
// time zone (NFR-4). Intl only: no date library.

const GENERIC_ZONES: Record<string, string> = {
  EST: "ET",
  EDT: "ET",
  CST: "CT",
  CDT: "CT",
  MST: "MT",
  MDT: "MT",
  PST: "PT",
  PDT: "PT",
  AKST: "AKT",
  AKDT: "AKT",
  HST: "HT",
};

function part(parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes): string {
  return parts.find((p) => p.type === type)?.value ?? "";
}

function zoneName(date: Date, timeZone: string, style: "shortGeneric" | "short"): string {
  try {
    const parts = new Intl.DateTimeFormat("en-US", { timeZone, timeZoneName: style }).formatToParts(
      date,
    );
    return part(parts, "timeZoneName");
  } catch {
    return "";
  }
}

/** "CT", "ET", "PT"…; falls back to the short name ("GMT+1") outside the US. */
export function zoneAbbreviation(date: Date, timeZone: string): string {
  const generic = zoneName(date, timeZone, "shortGeneric");
  if (generic && !generic.includes(" ") && !generic.startsWith("GMT")) return generic;
  const short = zoneName(date, timeZone, "short");
  return GENERIC_ZONES[short] ?? short;
}

interface DateParts {
  weekday: string;
  weekdayLong: string;
  month: string;
  day: string;
  time: string;
}

function dateParts(date: Date, timeZone: string): DateParts {
  const fmt = (options: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat("en-US", { timeZone, ...options }).formatToParts(date);
  const day = fmt({ weekday: "short", month: "short", day: "numeric" });
  const time = fmt({ hour: "numeric", minute: "2-digit", hour12: true });
  return {
    weekday: part(day, "weekday"),
    weekdayLong: part(fmt({ weekday: "long" }), "weekday"),
    month: part(day, "month"),
    day: part(day, "day"),
    time: `${part(time, "hour")}:${part(time, "minute")} ${part(time, "dayPeriod")}`,
  };
}

/** A calendar date ("2026-11-08") as a Date at noon UTC, so it formats as that same day. */
function calendarDate(isoDate: string): Date {
  return new Date(`${isoDate}T12:00:00Z`);
}

export interface Kickoff {
  kickoff_at: string | null;
  game_date: string | null;
  kickoff_tbd: boolean;
}

/** `SUN, NOV 8 · 12:00 PM CT` (label) or `Sun, Nov 8 · 12:00 PM CT` (sentence); TBD times
 * show `TIME TBD` and never a guessed time (FR-SC5). */
export function formatKickoff(
  game: Kickoff,
  timeZone: string,
  style: "label" | "sentence" = "label",
): string {
  let text: string;
  if (game.kickoff_at && !game.kickoff_tbd) {
    const date = new Date(game.kickoff_at);
    const p = dateParts(date, timeZone);
    text = `${p.weekday}, ${p.month} ${p.day} · ${p.time} ${zoneAbbreviation(date, timeZone)}`;
  } else if (game.game_date) {
    const p = dateParts(calendarDate(game.game_date), "UTC");
    text = `${p.weekday}, ${p.month} ${p.day} · Time TBD`;
  } else {
    text = "Date TBD";
  }
  return style === "label" ? text.toUpperCase() : text;
}

/** The calendar day a game belongs to in the viewer's zone, for day grouping ("2026-11-08"). */
export function gameDayKey(game: Kickoff, timeZone: string): string {
  if (game.kickoff_at && !game.kickoff_tbd) {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(game.kickoff_at));
  }
  return game.game_date ?? "TBD";
}

/** Day group header: `THURSDAY, NOV 5`. */
export function formatDayHeader(dayKey: string): string {
  if (dayKey === "TBD") return "DATE TBD";
  const p = dateParts(calendarDate(dayKey), "UTC");
  return `${p.weekdayLong}, ${p.month} ${p.day}`.toUpperCase();
}

export interface TeamName {
  nickname: string;
}

/** `BEARS @ PACKERS`; undecided playoff teams show their placeholder. */
export function formatMatchup(
  away: TeamName | null,
  home: TeamName | null,
  awayPlaceholder?: string | null,
  homePlaceholder?: string | null,
): string {
  const a = away?.nickname ?? awayPlaceholder ?? "TBD";
  const h = home?.nickname ?? homePlaceholder ?? "TBD";
  return `${a} @ ${h}`.toUpperCase();
}

/** `7–1`, or `6–2–1` when there are ties. */
export function formatRecord(wins: number, losses: number, ties = 0): string {
  return ties > 0 ? `${wins}–${losses}–${ties}` : `${wins}–${losses}`;
}

/** `0.8 mi` under 10 miles, whole miles above (`185 mi`). */
export function formatDistance(miles: number): string {
  return miles < 10 ? `${miles.toFixed(1)} mi` : `${Math.round(miles).toLocaleString("en-US")} mi`;
}

/** `Oct 12, 3:40 PM CT`. */
export function formatDateTime(iso: string, timeZone: string): string {
  const date = new Date(iso);
  const p = dateParts(date, timeZone);
  return `${p.month} ${p.day}, ${p.time} ${zoneAbbreviation(date, timeZone)}`;
}

/** `Oct 18` in the viewer's zone. */
export function formatShortDate(iso: string, timeZone: string): string {
  const p = dateParts(new Date(iso), timeZone);
  return `${p.month} ${p.day}`;
}

/** `6 min ago` under 24 hours, then the absolute time (UI/UX §5.1). */
export function formatRelative(iso: string, now: Date, timeZone: string): string {
  const minutes = Math.floor((now.getTime() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 24 * 60) return `${Math.floor(minutes / 60)} h ago`;
  return formatDateTime(iso, timeZone);
}

/** "Planning opens on Oct 18." (FR-SC8, UI/UX §8.2). */
export function formatPlanningOpens(opensAt: string, timeZone: string): string {
  return `Planning opens on ${formatShortDate(opensAt, timeZone)}.`;
}

/** The device's IANA time zone (BRD §7.1: detected, not asked). */
export function deviceTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York";
}
