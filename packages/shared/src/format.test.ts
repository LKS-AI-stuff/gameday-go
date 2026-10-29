import {
  formatDayHeader,
  formatDistance,
  formatKickoff,
  formatMatchup,
  formatPlanningOpens,
  formatRecord,
  formatRelative,
  gameDayKey,
  zoneAbbreviation,
} from "./format";

const SNF = { kickoff_at: "2026-11-09T01:20:00Z", game_date: "2026-11-08", kickoff_tbd: false };
const TBD = { kickoff_at: null, game_date: "2027-01-10", kickoff_tbd: true };

describe("formatKickoff (NFR-4)", () => {
  it("shows the day, time and zone in the viewer's time zone", () => {
    expect(formatKickoff(SNF, "America/Chicago")).toBe("SUN, NOV 8 · 7:20 PM CT");
    expect(formatKickoff(SNF, "America/New_York", "sentence")).toBe("Sun, Nov 8 · 8:20 PM ET");
    expect(formatKickoff(SNF, "America/Los_Angeles")).toBe("SUN, NOV 8 · 5:20 PM PT");
  });

  it("handles daylight saving time", () => {
    const october = { ...SNF, kickoff_at: "2026-10-26T00:20:00Z" };
    expect(formatKickoff(october, "America/New_York")).toBe("SUN, OCT 25 · 8:20 PM ET");
    // Arizona keeps standard time all year, so its zone reads MST.
    expect(formatKickoff(october, "America/Phoenix")).toBe("SUN, OCT 25 · 5:20 PM MST");
  });

  it("never guesses a TBD time (FR-SC5)", () => {
    expect(formatKickoff(TBD, "America/Los_Angeles")).toBe("SUN, JAN 10 · TIME TBD");
    expect(formatKickoff({ kickoff_at: null, game_date: null, kickoff_tbd: true }, "UTC")).toBe(
      "DATE TBD",
    );
  });

  it("falls back to a short zone name outside the US", () => {
    expect(zoneAbbreviation(new Date("2026-11-09T01:20:00Z"), "Europe/Berlin")).toMatch(
      /^(GMT\+1|CET)$/,
    );
  });
});

describe("day grouping", () => {
  it("groups by the viewer's calendar day", () => {
    expect(gameDayKey(SNF, "America/New_York")).toBe("2026-11-08");
    expect(gameDayKey(SNF, "Europe/London")).toBe("2026-11-09");
    expect(gameDayKey(TBD, "America/Los_Angeles")).toBe("2027-01-10");
    expect(formatDayHeader("2026-11-05")).toBe("THURSDAY, NOV 5");
  });
});

describe("formatMatchup", () => {
  it("is AWAY @ HOME, with placeholders for undecided teams", () => {
    expect(formatMatchup({ nickname: "Bears" }, { nickname: "Packers" })).toBe("BEARS @ PACKERS");
    expect(formatMatchup(null, { nickname: "Chiefs" }, "AFC Wild Card winner")).toBe(
      "AFC WILD CARD WINNER @ CHIEFS",
    );
    expect(formatMatchup(null, null)).toBe("TBD @ TBD");
  });
});

describe("numbers", () => {
  it("formats records with ties only when non-zero", () => {
    expect(formatRecord(7, 1)).toBe("7–1");
    expect(formatRecord(6, 2, 1)).toBe("6–2–1");
  });

  it("formats distance with one decimal under 10 miles", () => {
    expect(formatDistance(0.84)).toBe("0.8 mi");
    expect(formatDistance(9.96)).toBe("10.0 mi");
    expect(formatDistance(185.4)).toBe("185 mi");
    expect(formatDistance(1234)).toBe("1,234 mi");
  });
});

describe("relative times", () => {
  const now = new Date("2026-10-29T12:00:00Z");

  it("is relative under a day, absolute after", () => {
    expect(formatRelative("2026-10-29T11:59:40Z", now, "America/Chicago")).toBe("just now");
    expect(formatRelative("2026-10-29T11:54:00Z", now, "America/Chicago")).toBe("6 min ago");
    expect(formatRelative("2026-10-29T09:00:00Z", now, "America/Chicago")).toBe("3 h ago");
    expect(formatRelative("2026-10-12T20:40:00Z", now, "America/Chicago")).toBe(
      "Oct 12, 3:40 PM CT",
    );
  });

  it("shows when planning opens in the viewer's zone", () => {
    expect(formatPlanningOpens("2026-12-11T05:00:00Z", "America/Los_Angeles")).toBe(
      "Planning opens on Dec 10.",
    );
  });
});
