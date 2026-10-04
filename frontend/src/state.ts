import type { ErrorCode, ImportedSkin, SkinModel, SkinSpec, WarningCode } from "./api/client";

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
}

export type Action =
  | { type: "start" }
  | { type: "imported"; result: ImportedSkin }
  | { type: "failed"; code: ErrorCode }
  | { type: "cancelled" }
  | { type: "setModel"; model: SkinModel }
  | { type: "setSpec"; spec: SkinSpec }
  | { type: "styled"; skin: Blob }
  | { type: "addWarnings"; warnings: readonly WarningCode[] }
  | { type: "goto"; step: "preview" | "download" }
  | { type: "reset" };

export const initialState: State = {
  step: "upload",
  skin: null,
  spec: null,
  model: "classic",
  warnings: [],
  error: null,
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
    case "addWarnings":
      return { ...state, warnings: merge(state.warnings, action.warnings) };
    case "goto":
      return state.skin ? { ...state, step: action.step, error: null } : state;
    case "reset":
      return initialState;
  }
}
