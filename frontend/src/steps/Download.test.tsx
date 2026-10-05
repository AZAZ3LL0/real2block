import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PdfSettings } from "../api/client";
import { I18nProvider } from "../i18n";
import { DEFAULT_PDF } from "../state";
import { Download } from "./Download";

function renderDownload(settings: PdfSettings = DEFAULT_PDF, busy = false, onPdfLang = vi.fn()) {
  const onSettings = vi.fn();
  render(
    <I18nProvider initial="en">
      <Download
        settings={settings}
        onSettings={onSettings}
        pdfLang="en"
        onPdfLang={onPdfLang}
        busy={busy}
        onPng={vi.fn()}
        onPdf={vi.fn()}
        onBack={vi.fn()}
      />
    </I18nProvider>,
  );
  return onSettings;
}

describe("Download", () => {
  it("shows the finished figure height for the cell size", () => {
    renderDownload({ ...DEFAULT_PDF, pixel_mm: 6.5 });
    expect(screen.getByText("Finished figure height: 208 mm")).toBeInTheDocument();
  });

  it("limits the cell size to the API range", () => {
    renderDownload();
    const slider = screen.getByLabelText("Cell size, mm");
    expect(slider).toHaveAttribute("min", "3");
    expect(slider).toHaveAttribute("max", "8");
  });

  it("reports each changed setting", async () => {
    const onSettings = renderDownload();
    await userEvent.click(screen.getByRole("radio", { name: "Letter" }));
    await userEvent.click(screen.getByRole("radio", { name: "By numbers" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Pixel grid" }));
    fireEvent.change(screen.getByLabelText("Cell size, mm"), { target: { value: "3.5" } });
    expect(onSettings.mock.calls).toEqual([
      [{ paper: "Letter" }],
      [{ mode: "numbered" }],
      [{ grid_lines: false }],
      [{ pixel_mm: 3.5 }],
    ]);
  });

  it("shows the PDF language and reports a new one", async () => {
    const onPdfLang = vi.fn();
    renderDownload(DEFAULT_PDF, false, onPdfLang);
    const group = screen.getByRole("radiogroup", { name: "PDF language" });
    expect(within(group).getByRole("radio", { name: "English" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(within(group).getByRole("radio", { name: "Русский" }));
    expect(onPdfLang).toHaveBeenCalledWith("ru");
  });

  it("explains the numbered mode", () => {
    renderDownload({ ...DEFAULT_PDF, mode: "numbered" });
    expect(screen.getByText(/Gray cells with color numbers/)).toBeInTheDocument();
  });

  it("disables the PDF button while the PDF is prepared", () => {
    renderDownload(DEFAULT_PDF, true);
    expect(screen.getByRole("button", { name: "Download PDF" })).toBeDisabled();
    expect(screen.getByText("Preparing PDF…")).toBeInTheDocument();
  });
});
