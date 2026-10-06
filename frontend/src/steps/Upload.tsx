import type { ErrorCode } from "../api/client";
import { Checkbox } from "../components/Checkbox";
import { FileDrop, type RejectReason } from "../components/FileDrop";
import { SegmentedControl } from "../components/SegmentedControl";
import { useI18n, type MessageKey } from "../i18n";
import { PRIVACY_PATH } from "../Layout";

export const SKIN_MAX_BYTES = 64 * 1024;
/** Mirrors MAX_PHOTO_BYTES on the server, which stays the source of truth (tech.md §6.1). */
export const PHOTO_MAX_BYTES = 10 * 1024 * 1024;
const SKIN_TYPES = ["image/png"] as const;
const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
const TIPS: readonly MessageKey[] = ["upload.tip.face", "upload.tip.light", "upload.tip.shoulders"];

export type UploadSource = "photo" | "skin";

/** Upload choices that must survive a failed attempt, so the parent keeps them. */
export interface UploadChoice {
  source: UploadSource;
  consent: boolean;
}

export const INITIAL_UPLOAD: UploadChoice = { source: "photo", consent: false };

export interface UploadProps {
  choice: UploadChoice;
  onChoice: (choice: UploadChoice) => void;
  onPhoto: (file: File) => void;
  onSkin: (file: File) => void;
  onError: (code: ErrorCode) => void;
}

function rejectCode(reason: RejectReason): ErrorCode {
  return reason === "type" ? "UNSUPPORTED_FORMAT" : "FILE_TOO_LARGE";
}

function PhotoUpload({ choice, onChoice, onPhoto, onError }: Omit<UploadProps, "onSkin">) {
  const { t } = useI18n();
  const { consent } = choice;
  return (
    <div className="flex flex-col gap-4">
      <div className="text-sm">
        <p className="font-medium">{t("upload.tipsTitle")}</p>
        <ul className="list-disc pl-5 text-neutral-700">
          {TIPS.map((key) => (
            <li key={key}>{t(key)}</li>
          ))}
        </ul>
      </div>
      <Checkbox
        checked={consent}
        onChange={(checked) => {
          onChoice({ ...choice, consent: checked });
        }}
      >
        {t("upload.consent")}{" "}
        <a
          href={PRIVACY_PATH}
          target="_blank"
          rel="noopener"
          className="text-accent-dark underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          {t("upload.consentLink")}
        </a>
      </Checkbox>
      <FileDrop
        label={t("upload.photoTitle")}
        hint={t("upload.photoHint")}
        dropText={t("upload.drop")}
        chooseText={t("upload.choose")}
        accept={PHOTO_TYPES}
        maxBytes={PHOTO_MAX_BYTES}
        onFile={(file) => {
          // The server refuses without consent too; this only saves a pointless upload.
          if (consent) onPhoto(file);
          else onError("CONSENT_REQUIRED");
        }}
        onReject={(reason) => {
          onError(rejectCode(reason));
        }}
      />
    </div>
  );
}

export function Upload({ choice, onChoice, onPhoto, onSkin, onError }: UploadProps) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-4">
      <SegmentedControl<UploadSource>
        showLabel
        label={t("upload.source")}
        value={choice.source}
        onChange={(source) => {
          onChoice({ ...choice, source });
        }}
        options={[
          { value: "photo", label: t("upload.tabPhoto") },
          { value: "skin", label: t("upload.skinTitle") },
        ]}
      />
      {choice.source === "photo" ? (
        <PhotoUpload choice={choice} onChoice={onChoice} onPhoto={onPhoto} onError={onError} />
      ) : (
        <FileDrop
          label={t("upload.skinTitle")}
          hint={t("upload.skinHint")}
          dropText={t("upload.drop")}
          chooseText={t("upload.choose")}
          accept={SKIN_TYPES}
          maxBytes={SKIN_MAX_BYTES}
          onFile={onSkin}
          onReject={(reason) => {
            onError(rejectCode(reason));
          }}
        />
      )}
    </div>
  );
}
