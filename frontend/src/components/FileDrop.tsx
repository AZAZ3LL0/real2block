import { useId, useState, type DragEvent } from "react";

export type RejectReason = "type" | "size";

export interface FileDropProps {
  label: string;
  hint: string;
  dropText: string;
  chooseText: string;
  accept: readonly string[];
  maxBytes: number;
  onFile: (file: File) => void;
  onReject: (reason: RejectReason) => void;
}

export function FileDrop({ label, hint, dropText, chooseText, accept, maxBytes, onFile, onReject }: FileDropProps) {
  const id = useId();
  const hintId = useId();
  const [over, setOver] = useState(false);

  const take = (file: File | undefined) => {
    if (!file) return;
    if (!accept.includes(file.type)) onReject("type");
    else if (file.size > maxBytes) onReject("size");
    else onFile(file);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setOver(false);
    take(e.dataTransfer.files[0]);
  };

  // The file input itself is the only tab stop; the zone shows its focus ring.
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => {
        setOver(false);
      }}
      onDrop={onDrop}
      className={`flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center text-sm focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent sm:p-8 ${
        over ? "border-accent bg-accent-light" : "border-neutral-500"
      }`}
    >
      <label htmlFor={id} className="font-pixel text-xs">
        {label}
      </label>
      <p>
        {dropText}{" "}
        <label htmlFor={id} className="inline-block min-h-10 cursor-pointer py-2 font-medium text-accent-dark underline">
          {chooseText}
        </label>
      </p>
      <p id={hintId} className="text-xs text-neutral-600">
        {hint}
      </p>
      <input
        id={id}
        type="file"
        accept={accept.join(",")}
        aria-describedby={hintId}
        className="sr-only"
        onChange={(e) => {
          take(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
    </div>
  );
}
