import type { ReactNode } from "react";
import { SegmentedControl } from "./components/SegmentedControl";
import { useI18n, type Lang } from "./i18n";

export const PRIVACY_PATH = "/privacy";

function Header({ onPrivacy }: { onPrivacy: boolean }) {
  const { t, lang, setLang } = useI18n();
  // The app name is the page heading only on the app itself; other pages have their own h1.
  const Brand = onPrivacy ? "p" : "h1";
  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <Brand className="font-pixel text-lg">
          <a href="/" className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">
            {t("app.title")}
          </a>
        </Brand>
        <p className="text-sm text-neutral-600">{t("app.tagline")}</p>
      </div>
      <SegmentedControl<Lang>
        label={t("lang.label")}
        value={lang}
        onChange={setLang}
        options={[
          { value: "ru", label: "RU" },
          { value: "en", label: "EN" },
        ]}
      />
    </header>
  );
}

function Footer({ onPrivacy }: { onPrivacy: boolean }) {
  const { t } = useI18n();
  return (
    <footer className="border-t border-neutral-200 pt-4 text-sm">
      <a
        href={onPrivacy ? "/" : PRIVACY_PATH}
        className="text-accent-dark underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      >
        {onPrivacy ? t("footer.home") : t("footer.privacy")}
      </a>
    </footer>
  );
}

/** Page frame shared by the app and the privacy policy. */
export function Layout({ children, onPrivacy = false }: { children: ReactNode; onPrivacy?: boolean }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 p-4 sm:p-8">
      <Header onPrivacy={onPrivacy} />
      <main className="flex flex-1 flex-col gap-6">{children}</main>
      <Footer onPrivacy={onPrivacy} />
    </div>
  );
}
