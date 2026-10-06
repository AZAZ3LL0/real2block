import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { INITIAL_UPLOAD, PHOTO_MAX_BYTES, Upload, type UploadChoice } from "./Upload";

function Harness(props: { onPhoto: (f: File) => void; onSkin: (f: File) => void; onError: (c: string) => void }) {
  const [choice, setChoice] = useState<UploadChoice>(INITIAL_UPLOAD);
  return <Upload choice={choice} onChoice={setChoice} {...props} />;
}

function renderUpload() {
  const handlers = { onPhoto: vi.fn(), onSkin: vi.fn(), onError: vi.fn() };
  render(
    <I18nProvider initial="en">
      <Harness {...handlers} />
    </I18nProvider>,
  );
  const pick = (label: string, file: File) => {
    fireEvent.change(screen.getByLabelText(label), { target: { files: [file] } });
  };
  return { ...handlers, pick };
}

const photo = (type = "image/jpeg", bytes = 3) => new File([new Uint8Array(bytes)], "me.jpg", { type });

describe("Upload", () => {
  it("opens on the photo tab with tips and a consent link to the privacy policy", () => {
    renderUpload();
    expect(screen.getByRole("radio", { name: "Photo" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("face the camera")).toBeInTheDocument();
    expect(screen.getByText("good, even light")).toBeInTheDocument();
    expect(screen.getByText("shoulders and clothes in the frame")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "privacy policy" });
    expect(link).toHaveAttribute("href", "/privacy");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("does not send a photo without consent", () => {
    const { onPhoto, onError, pick } = renderUpload();
    pick("Photo of a person", photo());
    expect(onPhoto).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith("CONSENT_REQUIRED");
  });

  it("sends the photo once consent is given", async () => {
    const { onPhoto, pick } = renderUpload();
    await userEvent.click(screen.getByRole("checkbox", { name: /I consent to processing/ }));
    const file = photo("image/webp");
    pick("Photo of a person", file);
    expect(onPhoto).toHaveBeenCalledWith(file);
  });

  it("checks the photo type and size on the client", async () => {
    const { onPhoto, onError, pick } = renderUpload();
    await userEvent.click(screen.getByRole("checkbox", { name: /I consent to processing/ }));
    pick("Photo of a person", photo("image/gif"));
    pick("Photo of a person", photo("image/jpeg", PHOTO_MAX_BYTES + 1));
    expect(onError.mock.calls).toEqual([["UNSUPPORTED_FORMAT"], ["FILE_TOO_LARGE"]]);
    expect(onPhoto).not.toHaveBeenCalled();
  });

  it("switches to the ready skin tab without asking for consent", async () => {
    const { onSkin, pick } = renderUpload();
    await userEvent.click(screen.getByRole("radio", { name: "Ready skin" }));
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    const skin = new File(["png"], "s.png", { type: "image/png" });
    pick("Ready skin", skin);
    expect(onSkin).toHaveBeenCalledWith(skin);
  });
});
