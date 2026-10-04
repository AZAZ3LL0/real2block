import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import en from "./en.json";
import ru from "./ru.json";

export type Lang = "ru" | "en";
export type MessageKey = keyof typeof ru;

const MESSAGES: Record<Lang, Record<MessageKey, string>> = { ru, en };

export function detectLang(language: string | undefined): Lang {
  return language?.toLowerCase().startsWith("en") ? "en" : "ru";
}

interface I18n {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: MessageKey) => string;
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Lang }) {
  const [lang, setLang] = useState<Lang>(initial ?? detectLang(navigator.language));
  const value = useMemo<I18n>(
    () => ({ lang, setLang, t: (key) => MESSAGES[lang][key] }),
    [lang],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}
