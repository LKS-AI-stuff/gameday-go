import { ApiError, createApiClient } from "./client";

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
