import { Button } from "../components/Button";
import { Spinner } from "../components/Spinner";
import { useI18n } from "../i18n";

export interface DownloadProps {
  busy: boolean;
  onPng: () => void;
  onPdf: () => void;
  onBack: () => void;
}

export function Download({ busy, onPng, onPdf, onBack }: DownloadProps) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col items-start gap-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={onPng}>
          {t("download.png")}
        </Button>
        <Button onClick={onPdf} disabled={busy}>
          {t("download.pdf")}
        </Button>
      </div>
      {busy && <Spinner label={t("download.pdfBusy")} />}
      <Button variant="ghost" onClick={onBack}>
        {t("download.back")}
      </Button>
    </div>
  );
}
