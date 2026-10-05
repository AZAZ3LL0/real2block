export interface StepperProps {
  label: string;
  steps: readonly string[];
  current: number;
}

export function Stepper({ label, steps, current }: StepperProps) {
  return (
    <ol aria-label={label} className="flex flex-wrap gap-2 text-xs">
      {steps.map((label, index) => {
        const state = index < current ? "done" : index === current ? "current" : "todo";
        return (
          <li
            key={label}
            aria-current={state === "current" ? "step" : undefined}
            className={`flex items-center gap-1.5 rounded px-2 py-1 ${
              state === "current"
                ? "bg-accent text-white"
                : state === "done"
                  ? "bg-accent-light text-accent-dark"
                  : "bg-neutral-100 text-neutral-600"
            }`}
          >
            <span className="font-pixel text-[0.6rem]">{index + 1}</span>
            {label}
          </li>
        );
      })}
    </ol>
  );
}
