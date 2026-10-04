import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { saveBlob } from "./download";

const createUrl = vi.fn((_: Blob) => "blob:skin");
const revokeUrl = vi.fn((_: string) => undefined);

beforeEach(() => {
  vi.useFakeTimers();
  URL.createObjectURL = createUrl;
  URL.revokeObjectURL = revokeUrl;
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  createUrl.mockClear();
  revokeUrl.mockClear();
});

describe("saveBlob", () => {
  it("clicks an attached link and revokes the URL only after the download started", () => {
    const blob = new Blob(["png"], { type: "image/png" });
    const clicked: { download: string; href: string; attached: boolean }[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push({ download: this.download, href: this.href, attached: this.isConnected });
    });

    saveBlob(blob, "real2block-skin.png");

    expect(createUrl).toHaveBeenCalledWith(blob);
    expect(clicked).toEqual([{ download: "real2block-skin.png", href: "blob:skin", attached: true }]);
    expect(document.querySelector("a")).toBeNull();
    expect(revokeUrl).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(revokeUrl).toHaveBeenCalledWith("blob:skin");
  });
});
