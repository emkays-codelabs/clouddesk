import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  NetworkError,
  TOKEN_KEY,
  api,
  getToken,
  request,
  setToken,
  setUnauthorizedHandler,
} from "@/lib/api";

function reply(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  const unauthorized = vi.fn();

  beforeEach(() => {
    window.localStorage.clear();
    unauthorized.mockReset();
    setUnauthorizedHandler(unauthorized);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("sends the bearer token it holds", async () => {
    setToken("abc");
    const fetchMock = vi.fn().mockResolvedValue(reply(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await request("/x");

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer abc");
  });

  it("clears the token and signals a redirect on a 401", async () => {
    setToken("abc");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(401, { detail: "no" })));

    await expect(request("/x")).rejects.toBeInstanceOf(ApiError);

    expect(unauthorized).toHaveBeenCalledOnce();
    expect(getToken()).toBeNull();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("does not treat a failed login as an expired session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(401, { detail: "Unknown user" })));

    await expect(api.login("x@y.z")).rejects.toMatchObject({ status: 401, detail: "Unknown user" });

    expect(unauthorized).not.toHaveBeenCalled();
  });

  it("retries a GET and then reports a NetworkError", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("offline"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/x", { retries: 2 })).rejects.toBeInstanceOf(NetworkError);

    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("recovers when a retry succeeds", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("blip"))
      .mockResolvedValueOnce(reply(200, { value: 7 }));
    vi.stubGlobal("fetch", fetchMock);

    expect(await request<{ value: number }>("/x")).toEqual({ value: 7 });
  });

  it("never retries a write, so an action cannot run twice", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("offline"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request("/x", { method: "POST", body: {} })).rejects.toBeInstanceOf(NetworkError);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("surfaces the server's detail message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply(409, { detail: "The ticket is waiting." })));

    await expect(request("/x", { method: "POST" })).rejects.toMatchObject({
      status: 409,
      detail: "The ticket is waiting.",
    });
  });

  it("builds the query string and skips empty values", async () => {
    const fetchMock = vi.fn().mockResolvedValue(reply(200, { items: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await api.tickets({ status: "new", search: "", page_size: 5 });

    expect(fetchMock.mock.calls[0][0]).toContain("/api/v1/tickets?status=new&page_size=5");
  });
});
