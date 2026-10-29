import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import { renderWithApi, TEST_TEAMS } from "../test-utils";
import { SettingsScreen } from "./SettingsScreen";

jest.mock("expo-location", () => ({
  requestForegroundPermissionsAsync: jest.fn(),
  getCurrentPositionAsync: jest.fn(),
  Accuracy: { Balanced: 3 },
}));

const PREFS = {
  favorite_team_ids: ["CHI"],
  home_zip: "60601",
  home_place: { place_name: "Chicago", state: "IL" },
  travel: "low",
  spending: "less",
  max_ticket_price_usd: 90,
  viewing: "bar",
  notification_level: "low",
  timezone: "America/Chicago",
};
const NOTIFY = {
  level: "low",
  categories: { watch_hit: true, schedule_change: true, reminder: true, digest: true },
};

function routes(deleteStatus = 204) {
  return {
    "GET /api/v1/me/preferences": () => ({ body: PREFS }),
    "GET /api/v1/me/notification-settings": () => ({ body: NOTIFY }),
    "GET /api/v1/teams": () => ({ body: TEST_TEAMS }),
    "PUT /api/v1/me/preferences": (_: string, body: unknown) => ({
      body: { ...PREFS, ...(body as object) },
    }),
    "DELETE /api/v1/me": () =>
      deleteStatus === 204
        ? { status: 204 }
        : { status: deleteStatus, body: { code: "auth_deletion_failed" } },
  };
}

describe("SettingsScreen (UI/UX §7.11)", () => {
  it("shows the preferences and greys out categories the level doesn't send", async () => {
    await renderWithApi(<SettingsScreen onBack={jest.fn()} appVersion="0.1.0" />, routes());
    expect(await screen.findByText("Bears")).toBeTruthy();
    expect(screen.getByText("60601 · Chicago, IL")).toBeTruthy();
    expect(screen.getByText("Less · max $90")).toBeTruthy();
    expect(screen.getAllByText("Not sent at the low level")).toHaveLength(2);
  });

  it("won't save favorites without a team (AC-2)", async () => {
    await renderWithApi(<SettingsScreen onBack={jest.fn()} appVersion="0.1.0" />, routes());
    await fireEvent.press(await screen.findByLabelText("Favorite teams: Bears. Edit"));
    await fireEvent.press(await screen.findByLabelText("Chicago Bears"));
    expect(await screen.findByText("Keep at least one team.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(
      screen.getByText("Changes apply to new plans. Saved plans stay as they are."),
    ).toBeTruthy();
  });

  it("deletes the account only after typing DELETE", async () => {
    const { calls } = await renderWithApi(
      <SettingsScreen onBack={jest.fn()} appVersion="0.1.0" />,
      routes(),
    );
    await fireEvent.press(await screen.findByText("Delete account"));
    // The dialog's confirm button is the last "Delete account" on screen.
    const confirm = (await screen.findAllByRole("button", { name: "Delete account" })).at(-1);
    expect(confirm).toBeDisabled();
    await fireEvent.changeText(screen.getByLabelText("Type DELETE to confirm"), "DELETE");
    await fireEvent.press(screen.getAllByText("Delete account").at(-1)!);
    await waitFor(() => expect(calls.some((c) => c.method === "DELETE")).toBe(true));
  });

  it("offers Try again when the sign-in removal fails", async () => {
    await renderWithApi(<SettingsScreen onBack={jest.fn()} appVersion="0.1.0" />, routes(503));
    await fireEvent.press(await screen.findByText("Delete account"));
    await fireEvent.changeText(await screen.findByLabelText("Type DELETE to confirm"), "DELETE");
    await fireEvent.press(screen.getAllByText("Delete account").at(-1)!);
    expect(
      await screen.findByText(
        "Your data was deleted, but we couldn't close your sign-in. Try again.",
      ),
    ).toBeTruthy();
  });
});
