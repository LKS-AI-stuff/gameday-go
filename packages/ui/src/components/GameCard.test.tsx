import type { GameSummary } from "@gamedaygo/api-client";
import { fireEvent, render, screen } from "@testing-library/react-native";
import { PaperProvider } from "react-native-paper";

import { paperTheme } from "../theme/paperTheme";
import { GameCard, gameAccessibilityLabel } from "./GameCard";

const BASE: GameSummary = {
  id: "g1",
  season: 2026,
  week: 9,
  week_label: "WEEK 9",
  stage: "regular",
  game_date: "2026-11-08",
  kickoff_at: "2026-11-09T01:20:00Z",
  kickoff_tbd: false,
  home: { id: "GB", nickname: "Packers", name: "Green Bay Packers" },
  away: { id: "CHI", nickname: "Bears", name: "Chicago Bears" },
  home_placeholder: null,
  away_placeholder: null,
  venue_name: "Lambeau Field",
  venue_city: "Green Bay",
  venue_state: "WI",
  venue_country: "US",
  status: "scheduled",
  tags: [
    { tag: "division_rivalry", weight: "high", detail: null },
    { tag: "primetime", weight: "medium", detail: null },
    { tag: "home_finale", weight: "medium", detail: null },
  ],
  planning: { status: "open", opens_at: null },
  distance_mi: 183.4,
  is_favorite: true,
  is_sample: false,
};

async function renderCard(game: Partial<GameSummary> = {}, compact = false) {
  const onPress = jest.fn();
  await render(
    <PaperProvider theme={paperTheme}>
      <GameCard
        game={{ ...BASE, ...game }}
        timeZone="America/Chicago"
        onPress={onPress}
        compact={compact}
      />
    </PaperProvider>,
  );
  return onPress;
}

describe("GameCard (UI/UX §6.1)", () => {
  it("shows kickoff with zone, matchup, venue, two tags plus overflow and distance", async () => {
    const onPress = await renderCard();
    expect(screen.getByText("SUN, NOV 8 · 7:20 PM CT")).toBeTruthy();
    expect(screen.getByText("BEARS")).toBeTruthy();
    expect(screen.getByText("Lambeau Field · Green Bay, WI")).toBeTruthy();
    expect(screen.getByText("DIVISION RIVALRY")).toBeTruthy();
    expect(screen.getByText("PRIMETIME")).toBeTruthy();
    expect(screen.queryByText("HOME FINALE")).toBeNull();
    expect(screen.getByText("+1")).toBeTruthy();
    expect(screen.getByText("183 mi away")).toBeTruthy();
    expect(screen.getByText("Planning arrives soon")).toBeTruthy();
    await fireEvent.press(screen.getByRole("button", { name: /^Bears at Packers/ }));
    expect(onPress).toHaveBeenCalled();
  });

  it("shows when planning opens for games outside the window (AC-47)", async () => {
    await renderCard({ planning: { status: "opens_on", opens_at: "2026-12-11T05:00:00Z" } });
    expect(screen.getByText("Planning opens on Dec 10.")).toBeTruthy();
    expect(screen.queryByText("PLAN THIS GAME")).toBeNull();
  });

  it("shows TBD teams and times without guessing", async () => {
    await renderCard({
      home: null,
      away: null,
      home_placeholder: "TBD",
      away_placeholder: "TBD",
      kickoff_at: null,
      kickoff_tbd: true,
      game_date: "2027-01-16",
      stage: "playoff",
      venue_name: null,
      venue_city: null,
      venue_state: null,
      tags: [{ tag: "playoff", weight: "high", detail: null }],
    });
    expect(screen.getByText("SAT, JAN 16 · TIME TBD")).toBeTruthy();
    expect(screen.getByText("PLAYOFF GAME")).toBeTruthy();
  });

  it("marks postponed games with text, not only color", async () => {
    await renderCard({ status: "postponed" });
    expect(screen.getByText("POSTPONED")).toBeTruthy();
  });

  it("shows the sample-data badge (AC-13)", async () => {
    await renderCard({ is_sample: true });
    expect(screen.getByText("SAMPLE DATA")).toBeTruthy();
  });

  it("has a compact variant for the schedule", async () => {
    await renderCard({}, true);
    expect(screen.getByText("BEARS @ PACKERS")).toBeTruthy();
    expect(screen.queryByText("183 mi away")).toBeNull();
  });

  it("reads as one sentence for screen readers", () => {
    expect(gameAccessibilityLabel(BASE, "America/Chicago")).toBe(
      "Bears at Packers, Sun, Nov 8 · 7:20 PM CT, Lambeau Field · Green Bay, WI, division rivalry, primetime, home finale",
    );
  });
});
