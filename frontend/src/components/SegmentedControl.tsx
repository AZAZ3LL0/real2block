import { useId } from "react";
import type { Option } from "./Select";

export interface SegmentedControlProps<T extends string> {
  label: string;
  value: T;
  options: readonly Option<T>[];
  onChange: (value: T) => void;
  /** Print the label above the control instead of keeping it for screen readers only. */
  showLabel?: boolean;
}

export function SegmentedControl<T extends string>({
  label,
  value,
  options,
  onChange,
  showLabel = false,
}: SegmentedControlProps<T>) {
  const labelId = useId();
  const group = (
    <div
      role="radiogroup"
      {...(showLabel ? { "aria-labelledby": labelId } : { "aria-label": label })}
      className="inline-flex self-start rounded-md border border-neutral-300 p-0.5"
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => {
              onChange(o.value);
            }}
            className={`rounded px-3 py-1.5 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ${
              active ? "bg-accent text-white" : "text-neutral-700 hover:bg-neutral-100"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
  if (!showLabel) return group;
  return (
    <div className="flex flex-col gap-1 text-sm">
      <span id={labelId} className="font-medium">
        {label}
      </span>
      {group}
    </div>
  );
}
