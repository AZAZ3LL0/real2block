import type { HairStyle, PaletteRole, SkinSpec } from "../api/client";
import { SegmentedControl } from "../components/SegmentedControl";
import { ColorField } from "../components/ColorField";
import { Select } from "../components/Select";
import { useI18n, type MessageKey } from "../i18n";

// Records keep the lists exhaustive: a new role or style fails to compile here.
const ROLE_LABELS: Record<PaletteRole, MessageKey> = {
  skin: "palette.skin",
  hair: "palette.hair",
  eye_white: "palette.eye_white",
  iris: "palette.iris",
  mouth: "palette.mouth",
  shirt: "palette.shirt",
  pants: "palette.pants",
  shoes: "palette.shoes",
};

const HAIR_LABELS: Record<HairStyle, MessageKey> = {
  short: "hair.short",
  long: "hair.long",
  bald: "hair.bald",
  fringe: "hair.fringe",
};

type StylizerId = SkinSpec["stylizer"];

const STYLIZER_LABELS: Record<StylizerId, MessageKey> = {
  template: "stylizer.template",
  downsample: "stylizer.downsample",
};

function keysOf<K extends string>(record: Record<K, unknown>): K[] {
  return Object.keys(record) as K[];
}

export interface PalettePanelProps {
  spec: SkinSpec;
  onChange: (spec: SkinSpec) => void;
}

export function PalettePanel({ spec, onChange }: PalettePanelProps) {
  const { t } = useI18n();
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1 text-sm font-medium">{t("palette.title")}</legend>
      {/* "Like the photo" needs the 8x8 face from /analyze; without it only the pixel style exists. */}
      {spec.face_front && (
        <SegmentedControl<StylizerId>
          showLabel
          label={t("preview.stylizer")}
          value={spec.stylizer}
          options={keysOf(STYLIZER_LABELS).map((id) => ({ value: id, label: t(STYLIZER_LABELS[id]) }))}
          onChange={(stylizer) => {
            onChange({ ...spec, stylizer });
          }}
        />
      )}
      <Select<HairStyle>
        label={t("preview.hairStyle")}
        value={spec.hair_style}
        options={keysOf(HAIR_LABELS).map((style) => ({ value: style, label: t(HAIR_LABELS[style]) }))}
        onChange={(hair_style) => {
          onChange({ ...spec, hair_style });
        }}
      />
      {keysOf(ROLE_LABELS).map((role) => (
        <ColorField
          key={role}
          label={t(ROLE_LABELS[role])}
          value={spec.palette[role]}
          onChange={(hex) => {
            onChange({ ...spec, palette: { ...spec.palette, [role]: hex } });
          }}
        />
      ))}
    </fieldset>
  );
}
