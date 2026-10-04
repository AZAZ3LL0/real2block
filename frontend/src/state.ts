import type { ErrorCode, ImportedSkin, PdfSettings, SkinModel, SkinSpec, WarningCode } from "./api/client";

export const STEPS = ["upload", "processing", "preview", "download"] as const;
export type Step = (typeof STEPS)[number];

export interface State {
  step: Step;
  skin: Blob | null;
  /** Present for generated skins; imported skins have no spec and no palette. */
  spec: SkinSpec | null;
  model: SkinModel;
  warnings: WarningCode[];
  error: ErrorCode | null;
  pdf: PdfSettings;
}

export type Action =
  | { type: "start" }
  | { type: "imported"; result: ImportedSkin }
  | { type: "failed"; code: ErrorCode }
  | { type: "cancelled" }
  | { type: "setModel"; model: SkinModel }
  | { type: "setSpec"; spec: SkinSpec }
  | { type: "styled"; skin: Blob }
  | { type: "setPdf"; pdf: Partial<PdfSettings> }
  | { type: "pdfReady"; warnings: readonly WarningCode[] }
  | { type: "goto"; step: "preview" | "download" }
  | { type: "reset" };

/** Same defaults as the server's PapercraftOptions (tech.md §5.4). */
export const DEFAULT_PDF: PdfSettings = { paper: "A4", pixel_mm: 5, mode: "color", grid_lines: true };

export const initialState: State = {
  step: "upload",
  skin: null,
  spec: null,
  model: "classic",
  warnings: [],
  error: null,
  pdf: DEFAULT_PDF,
};

function merge(a: readonly WarningCode[], b: readonly WarningCode[]): WarningCode[] {
  return [...new Set([...a, ...b])];
}

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initialState, step: "processing" };
    case "imported":
      return { ...state, step: "preview", ...action.result, spec: null, error: null };
    case "failed":
      return { ...state, step: state.skin ? state.step : "upload", error: action.code };
    case "cancelled":
      return initialState;
    case "setModel":
      return {
        ...state,
        model: action.model,
        spec: state.spec && { ...state.spec, model: action.model },
      };
    case "setSpec":
      return { ...state, spec: action.spec, model: action.spec.model };
    case "styled":
      return { ...state, skin: action.skin, error: null };
    case "setPdf":
      // An error about the previous settings no longer applies.
      return { ...state, pdf: { ...state.pdf, ...action.pdf }, error: null };
    case "pdfReady":
      return { ...state, warnings: merge(state.warnings, action.warnings), error: null };
    case "goto":
      return state.skin ? { ...state, step: action.step, error: null } : state;
    case "reset":
      return initialState;
  }
}
