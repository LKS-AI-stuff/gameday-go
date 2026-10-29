import { ApiError, ApiNetworkError, createApiClient } from "./client";

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("createApiClient", () => {
  it("sends the bearer token and returns the JSON body", async () => {
    const me = { id: "u1", email: "ben@example.com", age_confirmed: true, timezone: null };
    const fetchMock = jest.fn().mockResolvedValue(jsonResponse(200, me));
    const client = createApiClient({
      baseUrl: "http://api.test/",
      getAccessToken: async () => "tok",
      fetch: fetchMock,
    });

    await expect(client.getMe()).resolves.toEqual(me);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/me");
    expect(init.method).toBe("GET");
    expect(init.headers.Authorization).toBe("Bearer tok");
  });

  it("omits Authorization when signed out", async () => {
    const fetchMock = jest.fn().mockResolvedValue(jsonResponse(200, { status: "ok" }));
    const client = createApiClient({
      baseUrl: "http://api.test",
      getAccessToken: async () => null,
      fetch: fetchMock,
    });
    await client.request("get", "/api/v1/health");
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("turns problem+json responses into ApiError", async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(
        jsonResponse(401, { code: "invalid_token", detail: "Expired" }, { "X-Request-ID": "r1" }),
      );
    const client = createApiClient({
      baseUrl: "http://api.test",
      getAccessToken: async () => "tok",
      fetch: fetchMock,
    });

    const error = await client.getMe().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401, code: "invalid_token", requestId: "r1" });
  });

  it("handles non-JSON error bodies", async () => {
    const fetchMock = jest.fn().mockResolvedValue(new Response("Bad gateway", { status: 502 }));
    const client = createApiClient({
      baseUrl: "http://api.test",
      getAccessToken: async () => null,
      fetch: fetchMock,
    });
    await expect(client.getMe()).rejects.toMatchObject({ status: 502, code: "http_error" });
  });
});

describe("M1 client methods", () => {
  function client(fetchMock: jest.Mock) {
    return createApiClient({
      baseUrl: "http://api.test",
      getAccessToken: async () => "tok",
      fetch: fetchMock,
    });
  }

  it("encodes game filters as a query string and skips undefined ones", async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(jsonResponse(200, { items: [], next_cursor: null }));
    await client(fetchMock).listGames({ week: 9, team: "CHI", favorites: true, from: undefined });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://api.test/api/v1/games?week=9&team=CHI&favorites=true",
    );
  });

  it("sends coordinates in the body, never the URL (FR-P3a)", async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(jsonResponse(200, { zip: "60601", place_name: "Chicago", state: "IL" }));
    await client(fetchMock).nearestZip(41.88, -87.62);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/api/v1/zip/nearest");
    expect(JSON.parse(init.body)).toEqual({ lat: 41.88, lng: -87.62 });
  });

  it("treats 204 as success", async () => {
    const fetchMock = jest.fn().mockResolvedValue(new Response(null, { status: 204 }));
    await expect(client(fetchMock).deleteMe()).resolves.toBeNull();
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
  });

  it("reports unreachable servers as ApiNetworkError", async () => {
    const fetchMock = jest.fn().mockRejectedValue(new TypeError("Network request failed"));
    await expect(client(fetchMock).getSeason()).rejects.toBeInstanceOf(ApiNetworkError);
  });
});
