import type { PdfSettings } from "../api/client";
import { Button } from "../components/Button";
import { Checkbox } from "../components/Checkbox";
import { SegmentedControl } from "../components/SegmentedControl";
import { Slider } from "../components/Slider";
import { Spinner } from "../components/Spinner";
import { useI18n } from "../i18n";

// Bounds of PapercraftOptions.pixel_mm (tech.md §5.4).
const PIXEL_MM_MIN = 3;
const PIXEL_MM_MAX = 8;
const PIXEL_MM_STEP = 0.5;
// Head 8 + body 12 + legs 12 skin pixels (tech.md §4.3).
const FIGURE_HEIGHT_CELLS = 32;

export interface DownloadProps {
  settings: PdfSettings;
  onSettings: (settings: Partial<PdfSettings>) => void;
  busy: boolean;
  onPng: () => void;
  onPdf: () => void;
  onBack: () => void;
}

function PdfOptions({ settings, onSettings }: Pick<DownloadProps, "settings" | "onSettings">) {
  const { t } = useI18n();
  const height = Math.round(FIGURE_HEIGHT_CELLS * settings.pixel_mm);
  return (
    <fieldset className="flex w-full max-w-sm flex-col gap-4">
      <legend className="mb-2 font-pixel text-sm">{t("download.options")}</legend>
      <div className="flex flex-col gap-1 text-sm">
        <span className="font-medium">{t("download.paper")}</span>
        <SegmentedControl<PdfSettings["paper"]>
          label={t("download.paper")}
          value={settings.paper}
          onChange={(paper) => {
            onSettings({ paper });
          }}
          options={[
            { value: "A4", label: "A4" },
            { value: "Letter", label: "Letter" },
          ]}
        />
      </div>
      <Slider
        label={t("download.cell")}
        value={settings.pixel_mm}
        min={PIXEL_MM_MIN}
        max={PIXEL_MM_MAX}
        step={PIXEL_MM_STEP}
        onChange={(pixel_mm) => {
          onSettings({ pixel_mm });
        }}
        hint={t("download.height", { height })}
      />
      <div className="flex flex-col gap-1 text-sm">
        <span className="font-medium">{t("download.mode")}</span>
        <SegmentedControl<PdfSettings["mode"]>
          label={t("download.mode")}
          value={settings.mode}
          onChange={(mode) => {
            onSettings({ mode });
          }}
          options={[
            { value: "color", label: t("download.mode.color") },
            { value: "numbered", label: t("download.mode.numbered") },
          ]}
        />
        <p className="text-xs text-neutral-500">{t(`download.modeHint.${settings.mode}`)}</p>
      </div>
      <Checkbox
        checked={settings.grid_lines}
        onChange={(grid_lines) => {
          onSettings({ grid_lines });
        }}
      >
        {t("download.grid")}
      </Checkbox>
    </fieldset>
  );
}

export function Download({ settings, onSettings, busy, onPng, onPdf, onBack }: DownloadProps) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col items-start gap-6">
      <Button variant="secondary" onClick={onPng}>
        {t("download.png")}
      </Button>
      <PdfOptions settings={settings} onSettings={onSettings} />
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={onPdf} disabled={busy}>
          {t("download.pdf")}
        </Button>
        {busy && <Spinner label={t("download.pdfBusy")} />}
      </div>
      <Button variant="ghost" onClick={onBack}>
        {t("download.back")}
      </Button>
    </div>
  );
}
