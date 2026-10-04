import { describe, expect, it } from "vitest";
import { DEFAULT_PDF, initialState, reducer, type State } from "./state";

const skin = new Blob(["png"], { type: "image/png" });
const imported: State = reducer(reducer(initialState, { type: "start" }), {
  type: "imported",
  result: { skin, model: "slim", warnings: ["TRANSPARENT_BASE_PIXELS"] },
});

describe("reducer", () => {
  it("moves upload → processing → preview on import", () => {
    expect(reducer(initialState, { type: "start" }).step).toBe("processing");
    expect(imported).toMatchObject({ step: "preview", model: "slim", skin, error: null });
  });

  it("returns to upload when import fails", () => {
    const failed = reducer(reducer(initialState, { type: "start" }), { type: "failed", code: "INVALID_SKIN" });
    expect(failed).toMatchObject({ step: "upload", error: "INVALID_SKIN" });
  });

  it("keeps the current step when a later call fails", () => {
    const onDownload = reducer(imported, { type: "goto", step: "download" });
    expect(reducer(onDownload, { type: "failed", code: "RATE_LIMITED" }).step).toBe("download");
  });

  it("does not leave upload without a skin", () => {
    expect(reducer(initialState, { type: "goto", step: "download" })).toBe(initialState);
  });

  it("merges PDF warnings without duplicates and clears an old error", () => {
    const failed = reducer(imported, { type: "failed", code: "RATE_LIMITED" });
    const next = reducer(failed, { type: "pdfReady", warnings: ["TRANSPARENT_BASE_PIXELS", "PALETTE_REDUCED"] });
    expect(next.warnings).toEqual(["TRANSPARENT_BASE_PIXELS", "PALETTE_REDUCED"]);
    expect(next.error).toBeNull();
  });

  it("clears an error when PDF settings change", () => {
    const failed = reducer(imported, { type: "failed", code: "INVALID_OPTIONS" });
    expect(reducer(failed, { type: "setPdf", pdf: { pixel_mm: 5 } }).error).toBeNull();
  });

  it("cancel and reset drop the skin", () => {
    expect(reducer(imported, { type: "cancelled" })).toEqual(initialState);
    expect(reducer(imported, { type: "reset" })).toEqual(initialState);
  });

  it("updates PDF settings field by field and resets them", () => {
    const changed = reducer(imported, { type: "setPdf", pdf: { paper: "Letter" } });
    const both = reducer(changed, { type: "setPdf", pdf: { pixel_mm: 6.5 } });
    expect(both.pdf).toEqual({ ...DEFAULT_PDF, paper: "Letter", pixel_mm: 6.5 });
    expect(reducer(both, { type: "reset" }).pdf).toEqual(DEFAULT_PDF);
  });
});
