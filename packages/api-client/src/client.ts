import type { components, paths } from "./schema";

type Schemas = components["schemas"];
export type Me = Schemas["Me"];
export type Preferences = Schemas["Preferences"];
export type PreferencesIn = Schemas["PreferencesIn"];
export type NotificationSettings = Schemas["NotificationSettings"];
export type ZipInfo = Schemas["ZipInfo"];
export type Team = Schemas["Team"];
export type TeamRef = Schemas["TeamRef"];
export type Season = Schemas["Season"];
export type GameSummary = Schemas["GameSummary"];
export type GameDetail = Schemas["GameDetail"];
export type GamePage = Schemas["GamePage"];
export type GameTag = Schemas["GameTag"];
export type ClientEvent = Schemas["ClientEvent"];

export interface GameFilters {
  season?: number;
  week?: number;
  team?: string;
  favorites?: boolean;
  /** UTC ISO-8601 */
  from?: string;
  to?: string;
  cursor?: string;
  limit?: number;
}

type Method = "get" | "post" | "put" | "patch" | "delete";

// The JSON body of an operation's 200 response, taken from the generated schema.
type JsonResponse<Op> = Op extends {
  responses: { 200: { content: { "application/json": infer T } } };
}
  ? T
  : never;

type PathsWith<M extends Method> = {
  [P in keyof paths]: paths[P][M] extends undefined | never ? never : P;
}[keyof paths];

/** An RFC 9457 problem response from the API (TDD §12). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly detail: string | undefined,
    readonly requestId: string | null,
  ) {
    super(detail ?? code);
    this.name = "ApiError";
  }
}

/** The request never reached the API (offline, server down, DNS). */
export class ApiNetworkError extends Error {
  constructor(cause: unknown) {
    super("Network request failed", { cause });
    this.name = "ApiNetworkError";
  }
}

export interface ApiClientOptions {
  /** Backend origin, e.g. http://localhost:8000 (EXPO_PUBLIC_API_URL). */
  baseUrl: string;
  /** Returns the current Supabase access token, or null when signed out. */
  getAccessToken: () => Promise<string | null>;
  fetch?: typeof fetch;
}

type Query = Record<string, string | number | boolean | undefined>;

function queryString(query: Query | undefined): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export function createApiClient({ baseUrl, getAccessToken, fetch: fetchImpl }: ApiClientOptions) {
  const doFetch = fetchImpl ?? globalThis.fetch.bind(globalThis);
  const origin = baseUrl.replace(/\/+$/, "");

  async function send<T>(
    method: Method,
    path: string,
    options: { body?: unknown; query?: Query } = {},
  ): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    const token = await getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body !== undefined) headers["Content-Type"] = "application/json";

    let response: Response;
    try {
      response = await doFetch(`${origin}${path}${queryString(options.query)}`, {
        method: method.toUpperCase(),
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
      });
    } catch (error) {
      throw new ApiNetworkError(error);
    }
    const requestId = response.headers.get("X-Request-ID");
    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      const problem = (payload ?? {}) as { code?: string; detail?: string };
      throw new ApiError(response.status, problem.code ?? "http_error", problem.detail, requestId);
    }
    return payload as T;
  }

  function request<M extends Method, P extends PathsWith<M>>(
    method: M,
    path: P,
    body?: unknown,
  ): Promise<JsonResponse<NonNullable<paths[P][M]>>> {
    return send(method, path, { body });
  }

  return {
    request,
    getMe: () => request("get", "/api/v1/me"),
    confirmAge: () => request("post", "/api/v1/me/age-confirmation"),
    deleteMe: () => send<void>("delete", "/api/v1/me"),
    getPreferences: () => request("get", "/api/v1/me/preferences"),
    putPreferences: (body: PreferencesIn) => request("put", "/api/v1/me/preferences", body),
    getNotificationSettings: () => request("get", "/api/v1/me/notification-settings"),
    putNotificationSettings: (body: NotificationSettings) =>
      request("put", "/api/v1/me/notification-settings", body),
    getZip: (zip: string) => send<ZipInfo>("get", `/api/v1/zip/${encodeURIComponent(zip)}`),
    // Coordinates go in the body so they never appear in URLs or logs (FR-P3a).
    nearestZip: (lat: number, lng: number) => request("post", "/api/v1/zip/nearest", { lat, lng }),
    listTeams: () => request("get", "/api/v1/teams"),
    getSeason: () => request("get", "/api/v1/season"),
    listGames: (filters: GameFilters = {}) => {
      const { from, ...rest } = filters;
      return send<GamePage>("get", "/api/v1/games", { query: { ...rest, from } });
    },
    getGame: (id: string) => send<GameDetail>("get", `/api/v1/games/${encodeURIComponent(id)}`),
    postAppEvents: (events: ClientEvent[]) =>
      send<void>("post", "/api/v1/app-events", { body: { events } }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
