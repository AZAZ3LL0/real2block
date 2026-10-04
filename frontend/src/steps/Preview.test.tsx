import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { Preview } from "./Preview";

const viewers = vi.hoisted(() => [] as { playerObject: { rotation: { y: number } }; resetCameraPose: () => void }[]);

vi.mock("skinview3d", () => ({
  SkinViewer: class {
    playerObject = { rotation: { y: 0 } };
    resetCameraPose = vi.fn();
    loadSkin = vi.fn(() => Promise.resolve());
    dispose = vi.fn();
    constructor() {
      viewers.push(this);
    }
  },
}));

beforeEach(() => {
  viewers.length = 0;
  URL.createObjectURL = vi.fn(() => "blob:test");
  URL.revokeObjectURL = vi.fn();
});

function renderPreview() {
  render(
    <I18nProvider initial="en">
      <Preview skin={new Blob(["png"])} model="classic" onModel={vi.fn()} onNext={vi.fn()} onReset={vi.fn()} />
    </I18nProvider>,
  );
  const viewer = viewers.at(-1);
  if (!viewer) throw new Error("viewer was not created");
  return viewer;
}

describe("Preview", () => {
  it("turns the figure to show the back and the front", async () => {
    const viewer = renderPreview();
    await userEvent.click(screen.getByRole("radio", { name: "Back" }));
    expect(viewer.playerObject.rotation.y).toBeCloseTo(Math.PI);
    await userEvent.click(screen.getByRole("radio", { name: "Front" }));
    expect(viewer.playerObject.rotation.y).toBe(0);
  });

  it("resets the orbited camera when the current side is picked again", async () => {
    const viewer = renderPreview();
    const resets = vi.mocked(viewer.resetCameraPose).mock.calls.length;
    await userEvent.click(screen.getByRole("radio", { name: "Front" }));
    expect(viewer.resetCameraPose).toHaveBeenCalledTimes(resets + 1);
  });
});
