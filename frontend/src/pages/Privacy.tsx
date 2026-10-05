import { Layout } from "../Layout";
import { useI18n, type MessageKey } from "../i18n";

interface Section {
  title: MessageKey;
  items: readonly MessageKey[];
}

// What tech.md §8.1 promises; the texts live in i18n like every other UI string.
const SECTIONS: readonly Section[] = [
  {
    title: "privacy.processed.title",
    items: [
      "privacy.processed.photo",
      "privacy.processed.face",
      "privacy.processed.colors",
      "privacy.processed.faceFront",
      "privacy.processed.skin",
    ],
  },
  {
    title: "privacy.notDone.title",
    items: ["privacy.notDone.identify", "privacy.notDone.external", "privacy.notDone.trackers"],
  },
  {
    title: "privacy.storage.title",
    items: ["privacy.storage.zero", "privacy.storage.logs", "privacy.storage.ip"],
  },
  { title: "privacy.consent.title", items: ["privacy.consent.body"] },
];

export function Privacy() {
  const { t } = useI18n();
  return (
    <Layout onPrivacy>
      <article className="flex flex-col gap-6 text-sm leading-relaxed">
        <h1 className="font-pixel text-base">{t("privacy.title")}</h1>
        <p>{t("privacy.intro")}</p>
        {SECTIONS.map((section) => (
          <section key={section.title} className="flex flex-col gap-2">
            <h2 className="text-base font-semibold">{t(section.title)}</h2>
            <ul className="list-disc space-y-1 pl-5">
              {section.items.map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </section>
        ))}
      </article>
    </Layout>
  );
}
