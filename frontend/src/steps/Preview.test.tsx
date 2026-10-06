import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SkinSpec } from "../api/client";
import { I18nProvider } from "../i18n";
import { SPEC } from "../test/spec";
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

function renderPreview(spec: SkinSpec | null = null, onSpec = vi.fn()) {
  render(
    <I18nProvider initial="en">
      <Preview
        skin={new Blob(["png"])}
        model="classic"
        spec={spec}
        onModel={vi.fn()}
        onSpec={onSpec}
        onNext={vi.fn()}
        onReset={vi.fn()}
      />
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

  it("labels the view and model controls visibly", () => {
    renderPreview();
    for (const name of ["View", "Model"]) {
      expect(screen.getByText(name)).toBeVisible();
      expect(screen.getByRole("radiogroup", { name })).toBeInTheDocument();
    }
  });

  it("has no palette for an imported skin", () => {
    renderPreview();
    expect(screen.queryByRole("group", { name: "Colors" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Hairstyle")).not.toBeInTheDocument();
  });

  it("shows a color field for every palette role", () => {
    renderPreview(SPEC);
    const labels: Record<keyof SkinSpec["palette"], string> = {
      skin: "Skin",
      hair: "Hair",
      eye_white: "Eye whites",
      iris: "Eyes",
      mouth: "Mouth",
      shirt: "T-shirt",
      pants: "Pants",
      shoes: "Shoes",
    };
    for (const [role, label] of Object.entries(labels)) {
      const value = SPEC.palette[role as keyof SkinSpec["palette"]];
      expect(screen.getByLabelText(label)).toHaveValue(value.toLowerCase());
    }
  });

  it("reports a recolored role as a new spec", () => {
    const onSpec = vi.fn();
    renderPreview(SPEC, onSpec);
    fireEvent.change(screen.getByLabelText("T-shirt"), { target: { value: "#ff0000" } });
    expect(onSpec).toHaveBeenCalledWith({ ...SPEC, palette: { ...SPEC.palette, shirt: "#FF0000" } });
  });

  it("switches to the photo face style when the spec has one", async () => {
    const onSpec = vi.fn();
    const face = Array.from({ length: 8 }, () => Array.from({ length: 8 }, () => "#AA7755"));
    renderPreview({ ...SPEC, face_front: face }, onSpec);
    const group = screen.getByRole("radiogroup", { name: "Style" });
    expect(screen.getByRole("radio", { name: "Pixel style" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(within(group).getByRole("radio", { name: "Like the photo" }));
    expect(onSpec).toHaveBeenCalledWith({ ...SPEC, face_front: face, stylizer: "downsample" });
  });

  it("offers no photo style without a photo face", () => {
    renderPreview(SPEC);
    expect(screen.queryByRole("radiogroup", { name: "Style" })).not.toBeInTheDocument();
  });

  it("reports a new hairstyle as a new spec", async () => {
    const onSpec = vi.fn();
    renderPreview(SPEC, onSpec);
    await userEvent.selectOptions(screen.getByLabelText("Hairstyle"), "Fringe");
    expect(onSpec).toHaveBeenCalledWith({ ...SPEC, hair_style: "fringe" });
  });
});
