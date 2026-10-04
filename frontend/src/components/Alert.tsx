import type { ReactNode } from "react";

type Tone = "info" | "warning" | "error";

const TONES: Record<Tone, string> = {
  info: "border-accent bg-accent-light text-neutral-900",
  warning: "border-amber-500 bg-amber-50 text-amber-900",
  error: "border-red-600 bg-red-50 text-red-900",
};

export function Alert({ tone = "info", title, children }: { tone?: Tone; title?: string; children: ReactNode }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-md border-l-4 p-3 text-sm ${TONES[tone]}`}>
      {title && <p className="mb-1 font-semibold">{title}</p>}
      {children}
    </div>
  );
}
