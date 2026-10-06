import { useEffect, useRef, type RefObject } from "react";
import { Button } from "../components/Button";
import { Spinner } from "../components/Spinner";
import { useI18n } from "../i18n";

/**
 * Shows a blob in an <img> through an object URL, revoked as soon as the blob goes away
 * (tech.md §6.1). The URL is created and revoked by the same effect: StrictMode re-runs
 * effects, so a URL made during render would be revoked while still displayed.
 */
function useBlobImage(blob: Blob | null): RefObject<HTMLImageElement> {
  const img = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const node = img.current;
    if (!blob || !node) return;
    const url = URL.createObjectURL(blob);
    node.src = url;
    return () => {
      node.removeAttribute("src");
      URL.revokeObjectURL(url);
    };
  }, [blob]);
  return img;
}

export interface ProcessingProps {
  /** The photo under analysis; null while a ready skin is imported or after /analyze answered. */
  photo: Blob | null;
  onCancel: () => void;
}

export function Processing({ photo, onCancel }: ProcessingProps) {
  const { t } = useI18n();
  const img = useBlobImage(photo);
  return (
    <div className="flex flex-col gap-4 sm:items-start">
      {photo && (
        <img ref={img} alt={t("processing.photoAlt")} className="max-h-64 w-auto self-center rounded-md sm:self-start" />
      )}
      <Spinner label={t(photo ? "processing.photo" : "processing.label")} />
      <Button variant="secondary" onClick={onCancel}>
        {t("processing.cancel")}
      </Button>
    </div>
  );
}
