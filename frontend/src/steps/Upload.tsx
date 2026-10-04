import { FileDrop, type RejectReason } from "../components/FileDrop";
import { useI18n } from "../i18n";

export const SKIN_MAX_BYTES = 64 * 1024;
const SKIN_TYPES = ["image/png"] as const;

export interface UploadProps {
  onSkin: (file: File) => void;
  onReject: (reason: RejectReason) => void;
}

export function Upload({ onSkin, onReject }: UploadProps) {
  const { t } = useI18n();
  return (
    <FileDrop
      label={t("upload.skinTitle")}
      hint={t("upload.skinHint")}
      dropText={t("upload.drop")}
      chooseText={t("upload.choose")}
      accept={SKIN_TYPES}
      maxBytes={SKIN_MAX_BYTES}
      onFile={onSkin}
      onReject={onReject}
    />
  );
}
