import { act, screen } from "@testing-library/react-native";
import { renderRouter, type RenderRouterResult } from "expo-router/testing-library";

// Renders the real app/ routes to check where each user lands.
const mockAuth = {
  getSession: jest.fn(),
  onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
  signOut: jest.fn().mockResolvedValue({ error: null }),
};

jest.mock("../src/supabase", () => ({ supabase: { auth: mockAuth } }));
jest.mock("../src/env", () => ({
  env: { apiUrl: "http://api.test", supabaseUrl: "http://sb.test", supabaseAnonKey: "k" },
}));
jest.mock("@gamedaygo/ui", () => ({
  ...jest.requireActual("@gamedaygo/ui"),
  useAppFonts: () => true,
}));

const session = {
  access_token: "tok",
  user: { id: "00000000-0000-0000-0000-000000000001", email: "ben@example.com" },
};

function json(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

/** A tiny fake API: the user has onboarded or not; next season's schedule isn't out. */
function fakeApi(onboarded: boolean) {
  globalThis.fetch = jest.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/v1/me")) {
      return json({
        id: session.user.id,
        email: session.user.email,
        age_confirmed: true,
        timezone: "America/Chicago",
        onboarded,
      });
    }
    if (url.includes("/api/v1/season")) {
      return json({
        year: 2027,
        status: "upcoming",
        schedule_available: false,
        current_week: null,
        weeks: [],
        planning_window_days: 30,
        schedule_updated_at: null,
        source: "API-Sports",
      });
    }
    if (url.includes("/api/v1/teams")) return json([]);
    if (url.includes("/api/v1/app-events")) {
      return Promise.resolve(new Response(null, { status: 202 }));
    }
    return json({ code: "not_found" }, 404);
  }) as typeof fetch;
}

async function renderAt(
  initialUrl: string,
  signedIn: boolean,
  onboarded = true,
): Promise<RenderRouterResult> {
  fakeApi(onboarded);
  mockAuth.getSession.mockResolvedValue({ data: { session: signedIn ? session : null } });
  let result: RenderRouterResult | undefined;
  await act(async () => {
    result = await renderRouter("./app", { initialUrl });
  });
  return result!;
}

it("sends signed-out users from / to sign-in", async () => {
  const router = await renderAt("/", false);
  expect(router.getPathname()).toBe("/sign-in");
  expect(await screen.findByText("New here? Create account")).toBeTruthy();
});

it("sends onboarded users from / to home", async () => {
  const router = await renderAt("/", true);
  expect(await screen.findByText("YOUR NEXT GAMES")).toBeTruthy();
  expect(router.getPathname()).toBe("/home");
  expect(await screen.findByText("Next season's schedule isn't out yet.")).toBeTruthy();
});

it("sends users who haven't onboarded to onboarding (FR-P1)", async () => {
  const router = await renderAt("/", true, false);
  expect(await screen.findByText("Who do you root for?")).toBeTruthy();
  expect(router.getPathname()).toBe("/onboarding");
});

it("keeps users who haven't onboarded away from the schedule", async () => {
  const router = await renderAt("/schedule", true, false);
  expect(await screen.findByText("Who do you root for?")).toBeTruthy();
  expect(router.getPathname()).not.toBe("/schedule");
});

it("keeps signed-out users away from home", async () => {
  const router = await renderAt("/home", false);
  expect(router.getPathname()).not.toBe("/home");
});

it("keeps signed-in users away from sign-in", async () => {
  const router = await renderAt("/sign-in", true);
  expect(router.getPathname()).not.toBe("/sign-in");
});
