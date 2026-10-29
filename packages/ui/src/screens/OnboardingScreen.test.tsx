import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { renderWithApi, TEST_TEAMS } from "../test-utils";
import { OnboardingScreen } from "./OnboardingScreen";

jest.mock("expo-location", () => ({
  requestForegroundPermissionsAsync: jest.fn().mockResolvedValue({ status: "denied" }),
  getCurrentPositionAsync: jest.fn(),
  Accuracy: { Balanced: 3 },
}));

const ME = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "ben@example.com",
  age_confirmed: true,
  timezone: null,
  onboarded: false,
};

function routes(saveStatus = 200) {
  return {
    "GET /api/v1/me": () => ({ body: ME }),
    "GET /api/v1/teams": () => ({ body: TEST_TEAMS }),
    "GET /api/v1/zip/60601": () => ({ body: { zip: "60601", place_name: "Chicago", state: "IL" } }),
    "PUT /api/v1/me/preferences": (_: string, body: unknown) =>
      saveStatus === 200
        ? { body: { ...(body as object), home_place: null } }
        : { status: saveStatus },
    "POST /api/v1/app-events": () => ({ status: 202 }),
  };
}

async function next() {
  await fireEvent.press(screen.getByText("Next"));
}

async function completeSteps() {
  expect(await screen.findByText("Who do you root for?")).toBeTruthy();
  expect(screen.getByText("Step 1 of 6")).toBeTruthy();
  await fireEvent.press(await screen.findByLabelText("Chicago Bears"));
  await next();
  await fireEvent.changeText(screen.getByLabelText("ZIP code"), "60601");
  expect(await screen.findByText("Chicago, IL")).toBeTruthy();
  await next();
  // Defaults are pre-selected (UI/UX §7.2).
  expect(
    screen.getByText("We'll suggest trips for big games, like playoffs and rivalries."),
  ).toBeTruthy();
  await next();
  await next();
  await next();
  expect(
    screen.getByText("Alerts you set up, schedule changes and game-day reminders."),
  ).toBeTruthy();
  await next();
}

describe("OnboardingScreen (FR-P1, AC-1)", () => {
  it("asks exactly six questions, then saves P1-P6 and the device time zone", async () => {
    const { calls } = await renderWithApi(<OnboardingScreen />, routes());
    await completeSteps();

    expect(screen.getByText("Review")).toBeTruthy();
    expect(screen.getByText("Bears")).toBeTruthy();
    expect(screen.getByText("60601 · Chicago, IL")).toBeTruthy();

    await fireEvent.press(screen.getByText("Start planning"));

    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    const saved = calls.find((c) => c.method === "PUT")?.body as Record<string, unknown>;
    expect(Object.keys(saved).sort()).toEqual([
      "favorite_team_ids",
      "home_zip",
      "max_ticket_price_usd",
      "notification_level",
      "spending",
      "timezone",
      "travel",
      "viewing",
    ]);
    expect(saved).toMatchObject({
      favorite_team_ids: ["CHI"],
      home_zip: "60601",
      travel: "medium",
      spending: "medium",
      max_ticket_price_usd: null,
      viewing: "flexible",
      notification_level: "medium",
    });
    expect(typeof saved.timezone).toBe("string");
    await waitFor(() =>
      expect(
        calls
          .filter((c) => c.path === "/api/v1/app-events")
          .map((c) => (c.body as { events: { name: string }[] }).events[0]?.name),
      ).toEqual(["onboarding_started", "onboarding_completed"]),
    );
  });

  it("needs a team and a known ZIP before moving on", async () => {
    await renderWithApi(<OnboardingScreen />, routes());
    expect(await screen.findByText("Who do you root for?")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    await fireEvent.press(await screen.findByLabelText("Chicago Bears"));
    await next();
    await fireEvent.changeText(screen.getByLabelText("ZIP code"), "00000");
    expect(await screen.findByText("We couldn't find that ZIP. Check the 5 digits.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("explains a denied location permission", async () => {
    await renderWithApi(<OnboardingScreen />, routes());
    await fireEvent.press(await screen.findByLabelText("Chicago Bears"));
    await next();
    await fireEvent.press(screen.getByText("Use my location"));
    expect(await screen.findByText("No problem, enter your ZIP instead.")).toBeTruthy();
  });

  it("edits from the review and returns to it", async () => {
    const { calls } = await renderWithApi(<OnboardingScreen />, routes());
    await completeSteps();
    await fireEvent.press(screen.getByLabelText("Edit: How far will you go for a game?"));
    await fireEvent.press(screen.getByText("Low"));
    await fireEvent.press(screen.getByText("Done"));
    expect(screen.getByText("Review")).toBeTruthy();
    await fireEvent.press(screen.getByText("Start planning"));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "PUT")?.body).toMatchObject({ travel: "low" }),
    );
  });

  it("stays on review with Try again when saving fails", async () => {
    await renderWithApi(<OnboardingScreen />, routes(500));
    await completeSteps();
    await fireEvent.press(screen.getByText("Start planning"));
    expect(await screen.findByText("Something went wrong. Try again.")).toBeTruthy();
    expect(screen.getByText("Review")).toBeTruthy();
  });
});
