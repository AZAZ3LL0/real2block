import type { components } from "./schema";

type Schemas = components["schemas"];
export type ErrorCode = Schemas["ErrorBody"]["code"];
export type WarningCode = Schemas["NormalizeResponse"]["warnings"][number];
export type NormalizeResponse = Schemas["NormalizeResponse"];
export type PapercraftOptions = Schemas["PapercraftOptions"];
export type PdfSettings = Pick<PapercraftOptions, "paper" | "pixel_mm" | "mode" | "grid_lines">;
export type PdfLang = PapercraftOptions["lang"];
export type SkinModel = NormalizeResponse["model"];
export type SkinSpec = Schemas["SkinSpec"];
export type Palette = Schemas["Palette"];
export type PaletteRole = keyof Palette;
export type HairStyle = SkinSpec["hair_style"];

const BASE = "/api/v1";
const WARNINGS_HEADER = "X-Real2block-Warnings";

export class ApiError extends Error {
  constructor(readonly code: ErrorCode) {
    super(code);
    this.name = "ApiError";
  }
}

export function isAbort(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

function isErrorResponse(body: unknown): body is Schemas["ErrorResponse"] {
  return typeof body === "object" && body !== null && "error" in body;
}

async function send(
  path: string,
  body: BodyInit,
  signal?: AbortSignal,
  headers?: HeadersInit,
): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method: "POST",
      body,
      signal: signal ?? null,
      ...(headers ? { headers } : {}),
    });
  } catch (err) {
    if (isAbort(err)) throw err;
    throw new ApiError("INTERNAL");
  }
  if (response.ok) return response;
  const payload: unknown = await response.json().catch(() => null);
  throw new ApiError(isErrorResponse(payload) ? payload.error.code : "INTERNAL");
}

function parseWarnings(header: string | null): WarningCode[] {
  if (!header) return [];
  return header.split(",").map((code) => code.trim() as WarningCode);
}

export function base64ToBlob(data: string, type: string): Blob {
  const bytes = Uint8Array.from(atob(data), (c) => c.charCodeAt(0));
  return new Blob([bytes], { type });
}

export interface ImportedSkin {
  skin: Blob;
  model: SkinModel;
  warnings: WarningCode[];
}

export async function normalizeSkin(file: Blob, signal?: AbortSignal): Promise<ImportedSkin> {
  const form = new FormData();
  form.append("skin", file, "skin.png");
  const response = await send("/skin/normalize", form, signal);
  const body = (await response.json()) as NormalizeResponse;
  return {
    skin: base64ToBlob(body.skin_png_base64, "image/png"),
    model: body.model,
    warnings: body.warnings,
  };
}

export interface PapercraftPdf {
  pdf: Blob;
  warnings: WarningCode[];
}

export async function papercraft(
  skin: Blob,
  options: Partial<PapercraftOptions>,
  signal?: AbortSignal,
): Promise<PapercraftPdf> {
  const form = new FormData();
  form.append("skin", skin, "skin.png");
  form.append("options", JSON.stringify(options));
  const response = await send("/papercraft", form, signal);
  return { pdf: await response.blob(), warnings: parseWarnings(response.headers.get(WARNINGS_HEADER)) };
}

export async function renderSkin(spec: SkinSpec, signal?: AbortSignal): Promise<Blob> {
  const response = await send("/skin", JSON.stringify(spec), signal, {
    "Content-Type": "application/json",
  });
  return response.blob();
}
