import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { I18nProvider } from "./i18n";

vi.mock("skinview3d", () => ({
  SkinViewer: class {
    playerObject = { rotation: { y: 0 } };
    resetCameraPose = vi.fn();
    loadSkin = vi.fn(() => Promise.resolve());
    dispose = vi.fn();
  },
}));

const normalized = { skin_png_base64: btoa("PNG"), model: "slim", warnings: [] };

function renderApp() {
  render(
    <I18nProvider initial="en">
      <App />
    </I18nProvider>,
  );
}

function pickSkin(file = new File(["png"], "s.png", { type: "image/png" })) {
  fireEvent.change(screen.getByLabelText("Ready skin"), { target: { files: [file] } });
}

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

const createUrl = vi.fn((_: Blob) => "blob:test");

beforeEach(() => {
  createUrl.mockClear();
  URL.createObjectURL = createUrl;
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("reference vertical", () => {
  it("imports a skin, previews it and requests the PDF", async () => {
    const fetchMock = mockApi();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderApp();
    pickSkin();
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
    renderApp();
    pickSkin();
    expect(await screen.findByRole("alert")).toHaveTextContent("does not look like a 64×64");
    expect(screen.getByLabelText("Ready skin")).toBeInTheDocument();
  });

  it("downloads the normalized skin as PNG", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ ...normalized, warnings: ["TRANSPARENT_BASE_PIXELS"] }), { status: 200 })),
    ));
    const saved: string[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      saved.push(this.download);
    });
    renderApp();
    pickSkin();
    expect(await screen.findByText("The skin has transparent pixels — they will print gray")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await userEvent.click(screen.getByRole("button", { name: "Download skin PNG" }));
    expect(saved).toEqual(["real2block-skin.png"]);
    const blob = createUrl.mock.calls.at(-1)?.[0];
    expect(blob instanceof Blob && (await blob.text())).toBe("PNG");
  });

  it("cancels the import and aborts the request", async () => {
    let signal: AbortSignal | null | undefined;
    vi.stubGlobal("fetch", vi.fn((_url: string, init?: RequestInit) => {
      signal = init?.signal;
      return new Promise<Response>((_resolve, reject) => {
        signal?.addEventListener("abort", () => {
          reject(new DOMException("aborted", "AbortError"));
        });
      });
    }));
    renderApp();
    pickSkin();
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(signal?.aborted).toBe(true);
    expect(screen.getByLabelText("Ready skin")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  it("rejects non-PNG and oversized files without calling the server", () => {
    const fetchMock = mockApi();
    renderApp();
    pickSkin(new File(["jpg"], "s.jpg", { type: "image/jpeg" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Unsupported file format");
    pickSkin(new File([new Uint8Array(64 * 1024 + 1)], "s.png", { type: "image/png" }));
    expect(screen.getByRole("alert")).toHaveTextContent("The file is too large");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
