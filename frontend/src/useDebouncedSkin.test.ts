import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, type SkinSpec } from "./api/client";
import { SPEC } from "./test/spec";
import { RESTYLE_DELAY_MS, useDebouncedSkin } from "./useDebouncedSkin";

type Pending = { body: SkinSpec; signal: AbortSignal; resolve: (r: Response) => void };

let pending: Pending[] = [];

function respond(index: number, body = "PNG") {
  pending[index]?.resolve(new Response(body, { status: 200, headers: { "Content-Type": "image/png" } }));
}

function recolor(shirt: string): SkinSpec {
  return { ...SPEC, palette: { ...SPEC.palette, shirt } };
}

function setup(initial: SkinSpec | null) {
  const onSkin = vi.fn();
  const onError = vi.fn();
  const hook = renderHook(({ spec }) => {
    useDebouncedSkin(spec, { onSkin, onError });
  }, { initialProps: { spec: initial } });
  return { ...hook, onSkin, onError };
}

// Resolving a response settles fetch, body reading and the hook's callbacks.
async function settle(fn: () => void) {
  await act(async () => {
    fn();
    await vi.advanceTimersByTimeAsync(0);
  });
}

async function flush() {
  await act(async () => {
    await vi.runOnlyPendingTimersAsync();
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  pending = [];
  vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) =>
    new Promise<Response>((resolve, reject) => {
      const signal = init.signal as AbortSignal;
      signal.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      });
      pending.push({ body: JSON.parse(init.body as string) as SkinSpec, signal, resolve });
    }),
  ));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useDebouncedSkin", () => {
  it("does nothing without a spec", async () => {
    setup(null);
    await flush();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("waits 300 ms of quiet before calling /skin", async () => {
    setup(SPEC);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(RESTYLE_DELAY_MS - 1);
    });
    expect(fetch).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/skin");
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
    expect(pending[0]?.body).toEqual(SPEC);
  });

  it("sends only the last of rapid edits", async () => {
    const { rerender, onSkin } = setup(SPEC);
    for (const shirt of ["#000001", "#000002", "#000003"]) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(RESTYLE_DELAY_MS / 2);
      });
      rerender({ spec: recolor(shirt) });
    }
    await flush();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(pending[0]?.body.palette.shirt).toBe("#000003");
    await settle(() => {
      respond(0);
    });
    expect(onSkin).toHaveBeenCalledTimes(1);
    expect(await (onSkin.mock.calls[0]?.[0] as Blob).text()).toBe("PNG");
  });

  it("aborts the request in flight when the spec changes", async () => {
    const { rerender, onSkin, onError } = setup(SPEC);
    await flush();
    rerender({ spec: recolor("#123456") });
    expect(pending[0]?.signal.aborted).toBe(true);
    await flush();
    await settle(() => {
      respond(0, "STALE");
      respond(1, "FRESH");
    });
    expect(onSkin).toHaveBeenCalledTimes(1);
    expect(await (onSkin.mock.calls[0]?.[0] as Blob).text()).toBe("FRESH");
    expect(onError).not.toHaveBeenCalled();
  });

  it("drops the pending call on unmount", async () => {
    const { unmount } = setup(SPEC);
    unmount();
    await flush();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("reports server errors", async () => {
    const { onError } = setup(SPEC);
    await flush();
    await settle(() => {
      pending[0]?.resolve(new Response(
        JSON.stringify({ error: { code: "INVALID_SPEC", message: "", request_id: "r" } }),
        { status: 422 },
      ));
    });
    expect(onError).toHaveBeenCalledWith(new ApiError("INVALID_SPEC"));
  });
});
