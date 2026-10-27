import { ApiClientProvider, createApiClient } from "@gamedaygo/api-client";
import type { SupabaseClient } from "@supabase/supabase-js";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMemo, useState, type ReactNode } from "react";
import { PaperProvider } from "react-native-paper";

import { AuthProvider } from "./auth/AuthProvider";
import { paperTheme } from "./theme/paperTheme";

interface AppProvidersProps {
  supabase: SupabaseClient;
  /** Backend origin (EXPO_PUBLIC_API_URL). */
  apiUrl: string;
  emailRedirectTo?: string;
  children: ReactNode;
}

/** Everything both app shells wrap their routes in. */
export function AppProviders({ supabase, apiUrl, emailRedirectTo, children }: AppProvidersProps) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000 } } }),
  );
  const apiClient = useMemo(
    () =>
      createApiClient({
        baseUrl: apiUrl,
        // getSession refreshes an expired access token before returning it.
        getAccessToken: async () =>
          (await supabase.auth.getSession()).data.session?.access_token ?? null,
      }),
    [apiUrl, supabase],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ApiClientProvider client={apiClient}>
        <AuthProvider supabase={supabase} emailRedirectTo={emailRedirectTo}>
          <PaperProvider theme={paperTheme}>{children}</PaperProvider>
        </AuthProvider>
      </ApiClientProvider>
    </QueryClientProvider>
  );
}
