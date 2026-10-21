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
          <PaperProvider theme={paperTheme("light")}>{ui}</PaperProvider>
        </AuthProvider>
      </QueryClientProvider>
    </SafeAreaProvider>,
  );
}
