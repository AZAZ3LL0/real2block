import { useState } from "react";
import type { SkinModel, SkinSpec } from "../api/client";
import { Button } from "../components/Button";
import { SegmentedControl } from "../components/SegmentedControl";
import { SkinViewer, type ViewRequest, type ViewSide } from "../components/SkinViewer";
import { useI18n } from "../i18n";
import { PalettePanel } from "./PalettePanel";

export interface PreviewProps {
  skin: Blob;
  model: SkinModel;
  /** Spec of a generated skin; null for an imported one, which has no palette. */
  spec: SkinSpec | null;
  onModel: (model: SkinModel) => void;
  onSpec: (spec: SkinSpec) => void;
  onNext: () => void;
  onReset: () => void;
}

export function Preview({ skin, model, spec, onModel, onSpec, onNext, onReset }: PreviewProps) {
  const { t } = useI18n();
  const [view, setView] = useState<ViewRequest>({ side: "front" });
  return (
    // Narrow screens stack the viewer above the panel (tech.md §6.4).
    <div className="flex flex-col gap-6 md:flex-row md:items-start">
      <div className="flex justify-center md:block">
        <SkinViewer skin={skin} model={model} view={view} label={t("viewer.label")} />
      </div>
      <div className="flex flex-1 flex-col gap-4">
        <SegmentedControl
          showLabel
          label={t("preview.side")}
          value={view.side}
          onChange={(side: ViewSide) => {
            setView({ side });
          }}
          options={[
            { value: "front", label: t("preview.front") },
            { value: "back", label: t("preview.back") },
          ]}
        />
        <SegmentedControl
          showLabel
          label={t("preview.model")}
          value={model}
          onChange={onModel}
          options={[
            { value: "classic", label: t("preview.classic") },
            { value: "slim", label: t("preview.slim") },
          ]}
        />
        {spec && <PalettePanel spec={spec} onChange={onSpec} />}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button onClick={onNext}>{t("preview.next")}</Button>
          <Button variant="ghost" onClick={onReset}>
            {t("preview.again")}
          </Button>
        </div>
      </div>
    </div>
  );
}
