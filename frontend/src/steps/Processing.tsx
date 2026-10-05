import { Button } from "../components/Button";
import { Spinner } from "../components/Spinner";
import { useI18n } from "../i18n";

export function Processing({ onCancel }: { onCancel: () => void }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-4 sm:items-start">
      <Spinner label={t("processing.label")} />
      <Button variant="secondary" onClick={onCancel}>
        {t("processing.cancel")}
      </Button>
    </div>
  );
}
