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

beforeEach(() => {
  globalThis.fetch = jest.fn().mockRejectedValue(new Error("offline"));
});

async function renderAt(initialUrl: string, signedIn: boolean): Promise<RenderRouterResult> {
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

it("sends signed-in users from / to home", async () => {
  const router = await renderAt("/", true);
  expect(router.getPathname()).toBe("/home");
  expect(await screen.findByText("You're signed in")).toBeTruthy();
});

it("keeps signed-out users away from home", async () => {
  const router = await renderAt("/home", false);
  expect(router.getPathname()).not.toBe("/home");
});

it("keeps signed-in users away from sign-in", async () => {
  const router = await renderAt("/sign-in", true);
  expect(router.getPathname()).not.toBe("/sign-in");
});
