import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { I18nProvider } from "./i18n";
import { PRIVACY_PATH } from "./Layout";
import { Privacy } from "./pages/Privacy";
import "./index.css";

async function pickPage(): Promise<ReactNode> {
  // import.meta.env.DEV is a build-time constant, so the kitchen sink is dropped from prod bundles.
  if (import.meta.env.DEV && new URLSearchParams(window.location.search).get("dev") === "kitchen-sink") {
    const { KitchenSink } = await import("./dev/KitchenSink");
    return <KitchenSink />;
  }
  // No router (tech.md §6.1): the privacy policy is the only other page.
  if (window.location.pathname === PRIVACY_PATH) return <Privacy />;
  return <App />;
}

const root = document.getElementById("root");
if (!root) throw new Error("#root is missing");

void pickPage().then((page) => {
  createRoot(root).render(
    <StrictMode>
      <I18nProvider>{page}</I18nProvider>
    </StrictMode>,
  );
});
