import { afterEach, expect, test, vi } from "vitest";
import { ApiError, postForm, request, requestText } from "./client";

afterEach(() => vi.restoreAllMocks());

function mockFetch(status: number, body: unknown, text = false) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: status < 400,
      status,
      json: async () => body,
      text: async () => (text ? body : JSON.stringify(body)),
    })),
  );
}

test("request unwraps the {data,error} envelope", async () => {
  mockFetch(200, { data: { slug: "x" }, error: null });
  await expect(request<{ slug: string }>("/projects")).resolves.toEqual({
    slug: "x",
  });
});

test("request throws ApiError when error is non-null", async () => {
  mockFetch(404, {
    data: null,
    error: { code: "set_not_found", message: "nope", details: {} },
  });
  await expect(request("/x")).rejects.toBeInstanceOf(ApiError);
  await expect(request("/x")).rejects.toMatchObject({
    code: "set_not_found",
    message: "nope",
  });
});

test("postForm unwraps the envelope on multipart upload", async () => {
  mockFetch(200, { data: { id: "r1" }, error: null });
  await expect(
    postForm<{ id: string }>("/recordings", new FormData()),
  ).resolves.toEqual({
    id: "r1",
  });
});

test("requestText returns the raw body (non-enveloped)", async () => {
  mockFetch(200, "# hello", true);
  await expect(requestText("/preview")).resolves.toBe("# hello");
});

test("ApiError is an Error", () => {
  expect(new ApiError("c", "m", {})).toBeInstanceOf(Error);
});
