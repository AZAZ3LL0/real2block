import { useEffect, useMemo } from "react";
import { Button } from "../components/Button";
import { Spinner } from "../components/Spinner";
import { useI18n } from "../i18n";

/** Object URL for a blob, revoked as soon as the blob goes away (tech.md §6.1). */
function useObjectUrl(blob: Blob | null): string | null {
  const url = useMemo(() => (blob ? URL.createObjectURL(blob) : null), [blob]);
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );
  return url;
}

export interface ProcessingProps {
  /** The photo under analysis; null while a ready skin is imported or after /analyze answered. */
  photo: Blob | null;
  onCancel: () => void;
}

export function Processing({ photo, onCancel }: ProcessingProps) {
  const { t } = useI18n();
  const url = useObjectUrl(photo);
  return (
    <div className="flex flex-col gap-4 sm:items-start">
      {url && (
        <img src={url} alt={t("processing.photoAlt")} className="max-h-64 w-auto self-center rounded-md sm:self-start" />
      )}
      <Spinner label={t(photo ? "processing.photo" : "processing.label")} />
      <Button variant="secondary" onClick={onCancel}>
        {t("processing.cancel")}
      </Button>
    </div>
  );
}
