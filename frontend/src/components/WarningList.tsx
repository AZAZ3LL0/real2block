import type { WarningCode } from "../api/client";
import { useI18n } from "../i18n";
import { Alert } from "./Alert";

export function WarningList({ warnings }: { warnings: readonly WarningCode[] }) {
  const { t } = useI18n();
  if (warnings.length === 0) return null;
  return (
    <Alert tone="warning" title={t("warnings.title")}>
      <ul className="list-disc space-y-0.5 pl-4">
        {warnings.map((code) => (
          <li key={code}>{t(`warnings.${code}`)}</li>
        ))}
      </ul>
    </Alert>
  );
}
