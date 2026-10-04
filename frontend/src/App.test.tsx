import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { I18nProvider } from "./i18n";

vi.mock("skinview3d", () => ({
  SkinViewer: class {
    playerObject = { rotation: { y: 0 } };
    loadSkin = vi.fn(() => Promise.resolve());
    dispose = vi.fn();
  },
}));

const normalized = { skin_png_base64: btoa("PNG"), model: "slim", warnings: [] };

function mockApi() {
  const fetchMock = vi.fn((url: string, _init?: RequestInit) =>
    Promise.resolve(
      url.endsWith("/skin/normalize")
        ? new Response(JSON.stringify(normalized), { status: 200 })
        : new Response("%PDF-1.4", { status: 200, headers: { "Content-Type": "application/pdf" } }),
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:test");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("reference vertical", () => {
  it("imports a skin, previews it and requests the PDF", async () => {
    const fetchMock = mockApi();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    render(
      <I18nProvider initial="en">
        <App />
      </I18nProvider>,
    );
    fireEvent.change(screen.getByLabelText("Ready skin"), {
      target: { files: [new File(["png"], "s.png", { type: "image/png" })] },
    });
    expect(await screen.findByRole("img", { name: "3D skin preview" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Slim" })).toHaveAttribute("aria-checked", "true");

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(screen.getByRole("button", { name: "Download PDF" }));
    await waitFor(() => {
      expect(click).toHaveBeenCalled();
    });
    const pdfCall = fetchMock.mock.calls.find(([url]) => url.endsWith("/papercraft"));
    const options = (pdfCall?.[1]?.body as FormData).get("options");
    expect(typeof options === "string" && JSON.parse(options)).toEqual({ model: "slim", lang: "en" });
  });

  it("shows the server error and stays on upload", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ error: { code: "INVALID_SKIN", message: "", request_id: "r" } }), { status: 422 })),
    ));
    render(
      <I18nProvider initial="en">
        <App />
      </I18nProvider>,
    );
    fireEvent.change(screen.getByLabelText("Ready skin"), {
      target: { files: [new File(["png"], "s.png", { type: "image/png" })] },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("does not look like a 64×64");
    expect(screen.getByLabelText("Ready skin")).toBeInTheDocument();
  });
});
