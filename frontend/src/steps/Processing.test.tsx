import { render, screen } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { Processing } from "./Processing";

const created: string[] = [];
const revoked = new Set<string>();

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => {
    const url = `blob:test-${String(created.length)}`;
    created.push(url);
    return url;
  });
  URL.revokeObjectURL = vi.fn((url: string) => {
    revoked.add(url);
  });
});

afterEach(() => {
  created.length = 0;
  revoked.clear();
});

function view(photo: Blob | null) {
  // StrictMode runs effects twice on mount, as the app does in development.
  return (
    <StrictMode>
      <I18nProvider initial="en">
        <Processing photo={photo} onCancel={vi.fn()} />
      </I18nProvider>
    </StrictMode>
  );
}

describe("Processing", () => {
  it("shows the photo through a live object URL", () => {
    render(view(new Blob(["x"], { type: "image/jpeg" })));
    const src = screen.getByRole("img").getAttribute("src");
    expect(src).toMatch(/^blob:/);
    expect(revoked.has(src ?? "")).toBe(false);
  });

  it("revokes every URL once the photo is gone", () => {
    const { rerender } = render(view(new Blob(["x"], { type: "image/jpeg" })));
    rerender(view(null));
    expect(screen.queryByRole("img")).toBeNull();
    expect(created.length).toBeGreaterThan(0);
    expect(created.every((url) => revoked.has(url))).toBe(true);
  });

  it("revokes the URL on unmount", () => {
    const { unmount } = render(view(new Blob(["x"], { type: "image/jpeg" })));
    unmount();
    expect(created.every((url) => revoked.has(url))).toBe(true);
  });
});
