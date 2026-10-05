import { useId } from "react";

export interface ColorFieldProps {
  label: string;
  value: string;
  onChange: (hex: string) => void;
}

export function ColorField({ label, value, onChange }: ColorFieldProps) {
  const id = useId();
  return (
    <div className="flex items-center gap-2 text-sm">
      <input
        id={id}
        type="color"
        value={value}
        onChange={(e) => {
          onChange(e.target.value.toUpperCase());
        }}
        className="h-11 w-11 shrink-0 cursor-pointer rounded border border-neutral-500 bg-white p-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      />
      <label htmlFor={id} className="flex-1">
        {label}
      </label>
      <span className="font-mono text-xs text-neutral-600">{value.toUpperCase()}</span>
    </div>
  );
}
