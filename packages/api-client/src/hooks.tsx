import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
} from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";

import type {
  ApiClient,
  ClientEvent,
  GameFilters,
  NotificationSettings,
  PreferencesIn,
} from "./client";

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

const SIGNED_OUT = "signed-out";

// Keys are scoped by user ID so one user's cached data is never shown to another.
export const queryKeys = {
  me: (userId: string) => ["me", userId] as const,
  preferences: (userId: string) => ["preferences", userId] as const,
  notificationSettings: (userId: string) => ["notification-settings", userId] as const,
  zip: (userId: string, zip: string) => ["zip", userId, zip] as const,
  teams: (userId: string) => ["teams", userId] as const,
  season: (userId: string) => ["season", userId] as const,
  games: (userId: string, filters?: GameFilters) =>
    (filters ? ["games", userId, filters] : ["games", userId]) as QueryKey,
  game: (userId: string, id: string) => ["game", userId, id] as const,
};

export function useMe(userId: string | null) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.me(userId ?? SIGNED_OUT),
    queryFn: () => client.getMe(),
    enabled: userId !== null,
  });
}

export function usePreferences(userId: string | null) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.preferences(userId ?? SIGNED_OUT),
    queryFn: () => client.getPreferences(),
    enabled: userId !== null,
  });
}

/** Saving preferences changes distances, favorites and the onboarding state. */
export function useSavePreferences(userId: string | null) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PreferencesIn) => client.putPreferences(body),
    onSuccess: async (saved) => {
      const id = userId ?? SIGNED_OUT;
      queryClient.setQueryData(queryKeys.preferences(id), saved);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.me(id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.games(id) }),
        queryClient.invalidateQueries({ queryKey: ["game", id] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.notificationSettings(id) }),
      ]);
    },
  });
}

export function useNotificationSettings(userId: string | null) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.notificationSettings(userId ?? SIGNED_OUT),
    queryFn: () => client.getNotificationSettings(),
    enabled: userId !== null,
  });
}

export function useSaveNotificationSettings(userId: string | null) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: NotificationSettings) => client.putNotificationSettings(body),
    onSuccess: async (saved) => {
      const id = userId ?? SIGNED_OUT;
      queryClient.setQueryData(queryKeys.notificationSettings(id), saved);
      await queryClient.invalidateQueries({ queryKey: queryKeys.preferences(id) });
    },
  });
}

/** Looks a ZIP up once it has 5 digits (FR-P3). */
export function useZipLookup(userId: string | null, zip: string) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.zip(userId ?? SIGNED_OUT, zip),
    queryFn: () => client.getZip(zip),
    enabled: userId !== null && /^\d{5}$/.test(zip),
    retry: false,
    staleTime: Infinity,
  });
}

export function useNearestZip() {
  const client = useApiClient();
  return useMutation({
    mutationFn: ({ lat, lng }: { lat: number; lng: number }) => client.nearestZip(lat, lng),
  });
}

export function useTeams(userId: string | null) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.teams(userId ?? SIGNED_OUT),
    queryFn: () => client.listTeams(),
    enabled: userId !== null,
    staleTime: 60 * 60 * 1000,
  });
}

export function useSeason(userId: string | null) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.season(userId ?? SIGNED_OUT),
    queryFn: () => client.getSeason(),
    enabled: userId !== null,
  });
}

export function useGames(userId: string | null, filters: GameFilters, enabled = true) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.games(userId ?? SIGNED_OUT, filters),
    queryFn: () => client.listGames(filters),
    enabled: userId !== null && enabled,
  });
}

/** Every page of a filtered list, following the cursor (FR-SC2). */
export function useAllGames(userId: string | null, filters: GameFilters, enabled = true) {
  const client = useApiClient();
  return useInfiniteQuery({
    queryKey: [...queryKeys.games(userId ?? SIGNED_OUT, filters), "all"],
    queryFn: ({ pageParam }) => client.listGames({ ...filters, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    enabled: userId !== null && enabled,
  });
}

export function useGame(userId: string | null, id: string | undefined) {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.game(userId ?? SIGNED_OUT, id ?? ""),
    queryFn: () => client.getGame(id ?? ""),
    enabled: userId !== null && !!id,
  });
}

export function useDeleteAccount() {
  const client = useApiClient();
  return useMutation({ mutationFn: () => client.deleteMe() });
}

/** Fire-and-forget product events (SM1); failures are ignored. */
export function useAppEvents() {
  const client = useApiClient();
  return (events: ClientEvent[]) => {
    client.postAppEvents(events).catch(() => undefined);
  };
}
