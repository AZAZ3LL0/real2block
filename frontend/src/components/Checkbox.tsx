import { useId, type ReactNode } from "react";

export interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  children: ReactNode;
  disabled?: boolean;
}

export function Checkbox({ checked, onChange, children, disabled = false }: CheckboxProps) {
  const id = useId();
  return (
    <div className="flex items-start gap-2 text-sm">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => {
          onChange(e.target.checked);
        }}
        className="mt-0.5 h-4 w-4 rounded border-neutral-400 accent-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      />
      <label htmlFor={id}>{children}</label>
    </div>
  );
}
