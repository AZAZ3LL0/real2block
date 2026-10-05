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
        className="mt-0.5 h-5 w-5 shrink-0 rounded border-neutral-500 accent-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
      />
      <label htmlFor={id} className="cursor-pointer">
        {children}
      </label>
    </div>
  );
}
