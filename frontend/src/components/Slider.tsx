import { useId } from "react";

export interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  hint?: string;
}

export function Slider({ label, value, min, max, step, onChange, hint }: SliderProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1 text-sm">
      <div className="flex justify-between">
        <label htmlFor={id} className="font-medium">
          {label}
        </label>
        <output htmlFor={id}>{value}</output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => {
          onChange(Number(e.target.value));
        }}
        className="h-11 w-full accent-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      />
      {hint && <p className="text-xs text-neutral-600">{hint}</p>}
    </div>
  );
}
