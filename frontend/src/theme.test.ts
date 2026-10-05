import { describe, expect, it } from "vitest";
import config from "../tailwind.config";

// WCAG 2.1 relative luminance and contrast ratio.
function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r = 0, g = 0, b = 0] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
}

const accent = config.theme.extend.colors.accent;
const WHITE = "#FFFFFF";
const AA_TEXT = 4.5;

describe("accent colors meet WCAG AA (tech.md §6.4)", () => {
  it.each([
    ["white text on the accent (primary button, active segment)", WHITE, accent.DEFAULT],
    ["dark accent text on white (links, ghost button)", accent.dark, WHITE],
    ["dark accent text on the light accent (done step, hover)", accent.dark, accent.light],
  ])("%s", (_name, fg, bg) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(AA_TEXT);
  });
});
