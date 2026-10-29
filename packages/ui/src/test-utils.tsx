import { ApiClientProvider, createApiClient } from "@gamedaygo/api-client";
import type { SupabaseClient } from "@supabase/supabase-js";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react-native";
import type { ReactElement } from "react";
import { PaperProvider } from "react-native-paper";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "./auth/AuthProvider";
import { paperTheme } from "./theme/paperTheme";

type AuthMethods = Record<string, jest.Mock>;

/** A Supabase client stub covering the auth calls the app makes. */
export function fakeSupabase(auth: AuthMethods = {}) {
  const methods: AuthMethods = {
    getSession: jest.fn().mockResolvedValue({ data: { session: null } }),
    onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
    signInWithPassword: jest.fn().mockResolvedValue({ error: null }),
    signUp: jest.fn().mockResolvedValue({ error: null }),
    resend: jest.fn().mockResolvedValue({ error: null }),
    signOut: jest.fn().mockResolvedValue({ error: null }),
    ...auth,
  };
  return { client: { auth: methods } as unknown as SupabaseClient, auth: methods };
}

export async function renderWithProviders(ui: ReactElement, supabase: SupabaseClient) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { x: 0, y: 0, width: 390, height: 844 },
        insets: { top: 0, left: 0, right: 0, bottom: 0 },
      }}
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider supabase={supabase}>
          <PaperProvider theme={paperTheme}>{ui}</PaperProvider>
        </AuthProvider>
      </QueryClientProvider>
    </SafeAreaProvider>,
  );
}

export const TEST_SESSION = {
  access_token: "tok",
  user: { id: "00000000-0000-0000-0000-000000000001", email: "ben@example.com" },
};

type Handler = (method: string, body: unknown) => { status?: number; body?: unknown };

/** Renders with a signed-in session and a fake API keyed by "METHOD /path" (query ignored). */
export async function renderWithApi(ui: ReactElement, routes: Record<string, Handler>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fetchMock = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    const method = (init?.method ?? "GET").toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path: url.pathname, body });
    const handler = routes[`${method} ${url.pathname}`];
    const result = handler ? handler(method, body) : { status: 404, body: { code: "not_found" } };
    const status = result.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(result.body ?? {}), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  const api = createApiClient({
    baseUrl: "http://api.test",
    getAccessToken: async () => "tok",
    fetch: fetchMock as unknown as typeof fetch,
  });
  const { client } = fakeSupabase({
    getSession: jest.fn().mockResolvedValue({ data: { session: TEST_SESSION } }),
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = await render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { x: 0, y: 0, width: 390, height: 844 },
        insets: { top: 0, left: 0, right: 0, bottom: 0 },
      }}
    >
      <QueryClientProvider client={queryClient}>
        <ApiClientProvider client={api}>
          <AuthProvider supabase={client}>
            <PaperProvider theme={paperTheme}>{ui}</PaperProvider>
          </AuthProvider>
        </ApiClientProvider>
      </QueryClientProvider>
    </SafeAreaProvider>,
  );
  return { view, calls, queryClient };
}

export const TEST_TEAMS = [
  {
    id: "CHI",
    name: "Chicago Bears",
    nickname: "Bears",
    city: "Chicago",
    conference: "NFC",
    division: "North",
  },
  {
    id: "DET",
    name: "Detroit Lions",
    nickname: "Lions",
    city: "Detroit",
    conference: "NFC",
    division: "North",
  },
  {
    id: "KC",
    name: "Kansas City Chiefs",
    nickname: "Chiefs",
    city: "Kansas City",
    conference: "AFC",
    division: "West",
  },
];
