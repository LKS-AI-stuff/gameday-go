import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";

import type { ApiClient } from "./client";

const ApiClientContext = createContext<ApiClient | null>(null);

export function ApiClientProvider({
  client,
  children,
}: {
  client: ApiClient;
  children: ReactNode;
}) {
  return <ApiClientContext.Provider value={client}>{children}</ApiClientContext.Provider>;
}

export function useApiClient(): ApiClient {
  const client = useContext(ApiClientContext);
  if (!client) throw new Error("useApiClient must be used inside ApiClientProvider");
  return client;
}

// Keys are scoped by user ID so one user's cached data is never shown to another.
export const queryKeys = {
  me: (userId: string) => ["me", userId] as const,
};

export function useMe(userId: string | null) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.me(userId ?? "signed-out"),
    queryFn: () => client.getMe(),
    enabled: userId !== null,
  });
}
