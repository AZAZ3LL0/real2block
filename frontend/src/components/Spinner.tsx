export function Spinner({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-sm text-neutral-700">
      <span
        aria-hidden="true"
        className="h-5 w-5 animate-spin rounded-sm border-2 border-accent border-t-transparent"
      />
      <span>{label}</span>
    </div>
  );
}
