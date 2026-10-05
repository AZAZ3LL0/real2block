import { useId, useRef, type KeyboardEvent } from "react";
import type { Option } from "./Select";

export interface SegmentedControlProps<T extends string> {
  label: string;
  value: T;
  options: readonly Option<T>[];
  onChange: (value: T) => void;
  /** Print the label above the control instead of keeping it for screen readers only. */
  showLabel?: boolean;
}

// Keys of the WAI-ARIA radio group pattern and the index step each one makes.
const STEP_KEYS: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

function nextIndex(key: string, current: number, count: number): number | null {
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  const step = STEP_KEYS[key];
  return step === undefined ? null : (current + step + count) % count;
}

export function SegmentedControl<T extends string>({
  label,
  value,
  options,
  onChange,
  showLabel = false,
}: SegmentedControlProps<T>) {
  const labelId = useId();
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  // Arrow keys move the choice and the focus together; the group is one tab stop.
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const index = nextIndex(e.key, options.findIndex((o) => o.value === value), options.length);
    const option = index === null ? undefined : options[index];
    if (index === null || !option) return;
    e.preventDefault();
    onChange(option.value);
    buttons.current[index]?.focus();
  };

  const group = (
    <div
      role="radiogroup"
      {...(showLabel ? { "aria-labelledby": labelId } : { "aria-label": label })}
      onKeyDown={onKeyDown}
      className="inline-flex self-start rounded-md border border-neutral-500 p-0.5"
    >
      {options.map((o, index) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              buttons.current[index] = el;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => {
              onChange(o.value);
            }}
            className={`min-h-10 rounded px-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
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
