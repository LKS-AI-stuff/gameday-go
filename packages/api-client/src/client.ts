import type { components, paths } from "./schema";

export type Me = components["schemas"]["Me"];

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

export interface ApiClientOptions {
  /** Backend origin, e.g. http://localhost:8000 (EXPO_PUBLIC_API_URL). */
  baseUrl: string;
  /** Returns the current Supabase access token, or null when signed out. */
  getAccessToken: () => Promise<string | null>;
  fetch?: typeof fetch;
}

export function createApiClient({ baseUrl, getAccessToken, fetch: fetchImpl }: ApiClientOptions) {
  const doFetch = fetchImpl ?? globalThis.fetch.bind(globalThis);
  const origin = baseUrl.replace(/\/+$/, "");

  async function request<M extends Method, P extends PathsWith<M>>(
    method: M,
    path: P,
    body?: unknown,
  ): Promise<JsonResponse<NonNullable<paths[P][M]>>> {
    const headers: Record<string, string> = { Accept: "application/json" };
    const token = await getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";

    const response = await doFetch(`${origin}${path}`, {
      method: method.toUpperCase(),
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const requestId = response.headers.get("X-Request-ID");
    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      const problem = (payload ?? {}) as { code?: string; detail?: string };
      throw new ApiError(response.status, problem.code ?? "http_error", problem.detail, requestId);
    }
    return payload as JsonResponse<NonNullable<paths[P][M]>>;
  }

  return {
    request,
    getMe: () => request("get", "/api/v1/me"),
    confirmAge: () => request("post", "/api/v1/me/age-confirmation"),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
