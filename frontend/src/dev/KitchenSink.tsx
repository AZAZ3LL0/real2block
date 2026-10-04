import { useEffect, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { Checkbox } from "../components/Checkbox";
import { ColorField } from "../components/ColorField";
import { FileDrop } from "../components/FileDrop";
import { SegmentedControl } from "../components/SegmentedControl";
import { Select } from "../components/Select";
import { SkinViewer, type ViewRequest } from "../components/SkinViewer";
import { Slider } from "../components/Slider";
import { Spinner } from "../components/Spinner";
import { Stepper } from "../components/Stepper";
import { WarningList } from "../components/WarningList";

const SKIN_SIZE = 64;

/** Checkerboard skin drawn on a canvas so the viewer has something to show. */
function useDemoSkin(): Blob | null {
  const [skin, setSkin] = useState<Blob | null>(null);
  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.width = SKIN_SIZE;
    canvas.height = SKIN_SIZE;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    for (let y = 0; y < SKIN_SIZE; y += 4) {
      for (let x = 0; x < SKIN_SIZE; x += 4) {
        ctx.fillStyle = (x + y) % 8 === 0 ? "#2F7D5B" : "#E3C9A8";
        ctx.fillRect(x, y, 4, 4);
      }
    }
    canvas.toBlob(setSkin, "image/png");
  }, []);
  return skin;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 border-t border-neutral-200 pt-4">
      <h2 className="font-pixel text-xs text-neutral-500">{title}</h2>
      {children}
    </section>
  );
}

function Controls() {
  const [checked, setChecked] = useState(true);
  const [paper, setPaper] = useState<"A4" | "Letter">("A4");
  const [mode, setMode] = useState<"color" | "numbered">("color");
  const [color, setColor] = useState("#3FA7A0");
  const [pixel, setPixel] = useState(5);
  return (
    <>
      <Section title="Button">
        <div className="flex flex-wrap gap-2">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button disabled>Disabled</Button>
        </div>
      </Section>
      <Section title="Checkbox">
        <Checkbox checked={checked} onChange={setChecked}>
          I agree to photo processing
        </Checkbox>
      </Section>
      <Section title="Select / SegmentedControl">
        <Select label="Paper" value={paper} onChange={setPaper} options={[{ value: "A4", label: "A4" }, { value: "Letter", label: "Letter" }]} />
        <SegmentedControl label="Mode" value={mode} onChange={setMode} options={[{ value: "color", label: "Color" }, { value: "numbered", label: "Numbered" }]} />
      </Section>
      <Section title="ColorField / Slider">
        <ColorField label="Shirt" value={color} onChange={setColor} />
        <Slider label="Cell size, mm" value={pixel} min={3} max={8} step={0.5} onChange={setPixel} hint={`Figure height ${String(pixel * 32)} mm`} />
      </Section>
    </>
  );
}

export function KitchenSink() {
  const skin = useDemoSkin();
  const [view, setView] = useState<ViewRequest>({ side: "front" });
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-4 sm:p-8">
      <h1 className="font-pixel text-lg">Kitchen sink</h1>
      <Stepper steps={["Upload", "Processing", "Preview", "Download"]} current={2} />
      <Controls />
      <Section title="FileDrop">
        <FileDrop label="Skin" hint="PNG up to 64 KB" dropText="Drop a file or" chooseText="choose" accept={["image/png"]} maxBytes={65536} onFile={() => undefined} onReject={() => undefined} />
      </Section>
      <Section title="Alert / WarningList / Spinner">
        <Alert>Info message</Alert>
        <Alert tone="error" title="Error">Something failed</Alert>
        <WarningList warnings={["TORSO_NOT_VISIBLE", "TRANSPARENT_BASE_PIXELS"]} />
        <Spinner label="Working…" />
      </Section>
      <Section title="SkinViewer">
        <SegmentedControl label="Side" value={view.side} onChange={(side) => { setView({ side }); }} options={[{ value: "front", label: "Front" }, { value: "back", label: "Back" }]} />
        {skin && <SkinViewer skin={skin} model="classic" view={view} label="Demo skin" size={240} />}
      </Section>
    </main>
  );
}
