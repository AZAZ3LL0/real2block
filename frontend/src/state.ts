import type {
  AnalyzeResponse,
  ErrorCode,
  ImportedSkin,
  PdfLang,
  PdfSettings,
  SkinModel,
  SkinSpec,
  WarningCode,
} from "./api/client";

export const STEPS = ["upload", "processing", "preview", "download"] as const;
export type Step = (typeof STEPS)[number];

export interface State {
  step: Step;
  /** The uploaded photo, kept only while /analyze runs (tech.md §6.3). */
  photo: Blob | null;
  skin: Blob | null;
  /** Present for generated skins; imported skins have no spec and no palette. */
  spec: SkinSpec | null;
  model: SkinModel;
  warnings: WarningCode[];
  error: ErrorCode | null;
  pdf: PdfSettings;
  /** Explicit PDF language; null follows the interface language (tech.md §6.5). */
  pdfLang: PdfLang | null;
}

export type Action =
  | { type: "start"; photo?: Blob }
  | { type: "imported"; result: ImportedSkin }
  | { type: "analyzed"; result: AnalyzeResponse }
  | { type: "failed"; code: ErrorCode }
  | { type: "cancelled" }
  | { type: "setModel"; model: SkinModel }
  | { type: "setSpec"; spec: SkinSpec }
  | { type: "styled"; skin: Blob }
  | { type: "setPdf"; pdf: Partial<PdfSettings> }
  | { type: "setPdfLang"; lang: PdfLang }
  | { type: "pdfReady"; warnings: readonly WarningCode[] }
  | { type: "goto"; step: "preview" | "download" }
  | { type: "reset" };

/** Same defaults as the server's PapercraftOptions (tech.md §5.4). */
export const DEFAULT_PDF: PdfSettings = { paper: "A4", pixel_mm: 5, mode: "color", grid_lines: true };

export const initialState: State = {
  step: "upload",
  photo: null,
  skin: null,
  spec: null,
  model: "classic",
  warnings: [],
  error: null,
  pdf: DEFAULT_PDF,
  pdfLang: null,
};

function merge(a: readonly WarningCode[], b: readonly WarningCode[]): WarningCode[] {
  return [...new Set([...a, ...b])];
}

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initialState, step: "processing", photo: action.photo ?? null };
    case "analyzed":
      // The first /skin render moves the flow on to the preview.
      return {
        ...state,
        photo: null,
        spec: action.result.spec,
        model: action.result.spec.model,
        warnings: action.result.warnings,
        error: null,
      };
    case "imported":
      return { ...state, step: "preview", ...action.result, spec: null, error: null };
    case "failed":
      // Without a skin there is nothing to preview: back to upload, dropping the photo and spec.
      return state.skin
        ? { ...state, error: action.code }
        : { ...state, step: "upload", photo: null, spec: null, error: action.code };
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
      return {
        ...state,
        step: state.step === "processing" ? "preview" : state.step,
        skin: action.skin,
        error: null,
      };
    case "setPdf":
      // An error about the previous settings no longer applies.
      return { ...state, pdf: { ...state.pdf, ...action.pdf }, error: null };
    case "setPdfLang":
      return { ...state, pdfLang: action.lang };
    case "pdfReady":
      return { ...state, warnings: merge(state.warnings, action.warnings), error: null };
    case "goto":
      return state.skin ? { ...state, step: action.step, error: null } : state;
    case "reset":
      return initialState;
  }
}
