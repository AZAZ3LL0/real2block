import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { I18nProvider, type Lang } from "../i18n";
import { Privacy } from "./Privacy";

function renderPrivacy(lang: Lang) {
  render(
    <I18nProvider initial={lang}>
      <Privacy />
    </I18nProvider>,
  );
}

describe("Privacy", () => {
  it("states what is processed, what is not and the zero retention in English", () => {
    renderPrivacy("en");
    expect(screen.getByRole("heading", { level: 1, name: "Privacy policy" })).toBeInTheDocument();
    for (const name of ["What is processed", "What we do not do", "How long it is kept", "Consent"]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
    expect(screen.getByText(/Retention is zero/)).toBeInTheDocument();
    expect(screen.getByText(/8×8 pixel copy of the face/)).toBeInTheDocument();
    expect(screen.getByText(/do not estimate age, gender or ethnicity/)).toBeInTheDocument();
  });

  it("is available in Russian and switches language in place", async () => {
    renderPrivacy("ru");
    expect(screen.getByRole("heading", { level: 1, name: "Политика приватности" })).toBeInTheDocument();
    expect(screen.getByText(/Срок хранения — ноль/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "EN" }));
    expect(screen.getByRole("heading", { level: 1, name: "Privacy policy" })).toBeInTheDocument();
  });

  it("leads back to the app", () => {
    renderPrivacy("en");
    expect(screen.getByRole("link", { name: "Back to the app" })).toHaveAttribute("href", "/");
  });
});
