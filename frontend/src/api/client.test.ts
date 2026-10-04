import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, normalizeSkin, papercraft } from "./client";

function respond(body: BodyInit, init: ResponseInit): void {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(body, init))));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("decodes the normalized skin", async () => {
    respond(JSON.stringify({ skin_png_base64: btoa("PNG"), model: "slim", warnings: [] }), { status: 200 });
    const result = await normalizeSkin(new Blob(["x"]));
    expect(result.model).toBe("slim");
    expect(await result.skin.text()).toBe("PNG");
    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/skin/normalize");
    expect((init?.body as FormData).get("skin")).toBeInstanceOf(Blob);
  });

  it("maps the error envelope to ApiError", async () => {
    respond(JSON.stringify({ error: { code: "INVALID_SKIN", message: "x", request_id: "r" } }), { status: 422 });
    await expect(normalizeSkin(new Blob(["x"]))).rejects.toEqual(new ApiError("INVALID_SKIN"));
  });

  it("treats a non-JSON failure as INTERNAL", async () => {
    respond("<html>bad gateway</html>", { status: 502 });
    await expect(normalizeSkin(new Blob(["x"]))).rejects.toMatchObject({ code: "INTERNAL" });
  });

  it("treats a network failure as INTERNAL", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("offline"))));
    await expect(normalizeSkin(new Blob(["x"]))).rejects.toMatchObject({ code: "INTERNAL" });
  });

  it("sends options as JSON and reads warnings header", async () => {
    respond("%PDF-1.4", { status: 200, headers: { "X-Blockfold-Warnings": "TRANSPARENT_BASE_PIXELS" } });
    const result = await papercraft(new Blob(["png"]), { model: "classic", lang: "en" });
    expect(result.warnings).toEqual(["TRANSPARENT_BASE_PIXELS"]);
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    const options = (init?.body as FormData).get("options");
    expect(typeof options === "string" && JSON.parse(options)).toEqual({ model: "classic", lang: "en" });
  });
});
