import type { GameSummary } from "@gamedaygo/api-client";

import { nextGamesPerTeam } from "./HomeScreen";

function game(id: string, away: string, home: string): GameSummary {
  return {
    id,
    away: { id: away, nickname: away, name: away },
    home: { id: home, nickname: home, name: home },
  } as GameSummary;
}

describe("nextGamesPerTeam (FR-SC1)", () => {
  it("keeps the first game for each favorite team, in kickoff order", () => {
    const games = [game("1", "CHI", "GB"), game("2", "DET", "CHI"), game("3", "DET", "MIN")];
    expect(nextGamesPerTeam(games, ["CHI", "DET"]).map((g) => g.id)).toEqual(["1", "2"]);
  });

  it("covers both favorites with one game when they play each other", () => {
    const games = [game("1", "CHI", "DET"), game("2", "DET", "MIN")];
    expect(nextGamesPerTeam(games, ["CHI", "DET"]).map((g) => g.id)).toEqual(["1"]);
  });

  it("returns at most five games", () => {
    const teams = ["A", "B", "C", "D", "E", "F"];
    const games = teams.map((t, i) => game(String(i), t, "X"));
    expect(nextGamesPerTeam(games, teams)).toHaveLength(5);
  });
});

describe("nextGamesPerTeam and the clock", () => {
  it("skips games that have kicked off", () => {
    const started = {
      ...game("1", "CHI", "GB"),
      kickoff_at: "2026-11-01T18:00:00Z",
      kickoff_tbd: false,
    };
    const later = {
      ...game("2", "CHI", "DET"),
      kickoff_at: "2026-11-08T18:00:00Z",
      kickoff_tbd: false,
    };
    const picked = nextGamesPerTeam([started, later], ["CHI"], new Date("2026-11-02T00:00:00Z"));
    expect(picked.map((g) => g.id)).toEqual(["2"]);
  });
});
