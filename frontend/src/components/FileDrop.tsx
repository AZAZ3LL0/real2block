import { useId, useRef, useState, type DragEvent } from "react";

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
  const input = useRef<HTMLInputElement>(null);
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
      className={`flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 text-center text-sm ${
        over ? "border-accent bg-accent-light" : "border-neutral-300"
      }`}
    >
      <label htmlFor={id} className="font-pixel text-xs">
        {label}
      </label>
      <p>
        {dropText}{" "}
        <button
          type="button"
          onClick={() => input.current?.click()}
          className="font-medium text-accent-dark underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          {chooseText}
        </button>
      </p>
      <p className="text-xs text-neutral-500">{hint}</p>
      <input
        id={id}
        ref={input}
        type="file"
        accept={accept.join(",")}
        className="sr-only"
        onChange={(e) => {
          take(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
    </div>
  );
}
