import { useState } from "react";
import type { SkinModel } from "../api/client";
import { Button } from "../components/Button";
import { SegmentedControl } from "../components/SegmentedControl";
import { SkinViewer, type ViewRequest, type ViewSide } from "../components/SkinViewer";
import { useI18n } from "../i18n";

export interface PreviewProps {
  skin: Blob;
  model: SkinModel;
  onModel: (model: SkinModel) => void;
  onNext: () => void;
  onReset: () => void;
}

export function Preview({ skin, model, onModel, onNext, onReset }: PreviewProps) {
  const { t } = useI18n();
  const [view, setView] = useState<ViewRequest>({ side: "front" });
  return (
    <div className="flex flex-col gap-6 md:flex-row">
      <SkinViewer skin={skin} model={model} view={view} label={t("viewer.label")} />
      <div className="flex flex-col gap-4">
        <SegmentedControl
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
          label={t("preview.model")}
          value={model}
          onChange={onModel}
          options={[
            { value: "classic", label: t("preview.classic") },
            { value: "slim", label: t("preview.slim") },
          ]}
        />
        <div className="flex gap-2">
          <Button onClick={onNext}>{t("preview.next")}</Button>
          <Button variant="ghost" onClick={onReset}>
            {t("preview.again")}
          </Button>
        </div>
      </div>
    </div>
  );
}
