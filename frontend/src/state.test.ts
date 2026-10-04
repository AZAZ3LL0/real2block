import { describe, expect, it } from "vitest";
import { initialState, reducer, type State } from "./state";
import { SPEC } from "./test/spec";

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

  it("merges warnings without duplicates", () => {
    const next = reducer(imported, { type: "addWarnings", warnings: ["TRANSPARENT_BASE_PIXELS", "PALETTE_REDUCED"] });
    expect(next.warnings).toEqual(["TRANSPARENT_BASE_PIXELS", "PALETTE_REDUCED"]);
  });

  it("cancel and reset drop the skin", () => {
    expect(reducer(imported, { type: "cancelled" })).toEqual(initialState);
    expect(reducer(imported, { type: "reset" })).toEqual(initialState);
  });

  it("imported skins carry no spec", () => {
    expect(imported.spec).toBeNull();
  });

  it("stores an edited spec and follows its model", () => {
    const next = reducer(imported, { type: "setSpec", spec: { ...SPEC, model: "slim" } });
    expect(next.spec).toEqual({ ...SPEC, model: "slim" });
    expect(next.model).toBe("slim");
  });

  it("keeps the spec model in sync with the model switch", () => {
    const withSpec = reducer(imported, { type: "setSpec", spec: SPEC });
    expect(reducer(withSpec, { type: "setModel", model: "slim" }).spec?.model).toBe("slim");
    expect(reducer(imported, { type: "setModel", model: "classic" }).spec).toBeNull();
  });

  it("replaces the skin with a restyled one and clears the error", () => {
    const failed = reducer(imported, { type: "failed", code: "RATE_LIMITED" });
    const restyled = new Blob(["new"], { type: "image/png" });
    expect(reducer(failed, { type: "styled", skin: restyled })).toMatchObject({ skin: restyled, error: null });
  });
});
