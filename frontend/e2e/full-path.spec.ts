import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { expect, test, type Download, type Locator, type Page } from "@playwright/test";

// The owner-approved reference skin doubles as the e2e input.
const SKIN = fileURLToPath(new URL("../../backend/tests/fixtures/reference_skin.png", import.meta.url));
// A CC0 photo from the backend fixtures (see its LICENSES.md).
const PHOTO = fileURLToPath(new URL("../../backend/tests/fixtures/photos/frontal_white_tshirt.jpg", import.meta.url));
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

async function saved(download: Download): Promise<Buffer> {
  return readFile(await download.path());
}

/** Waits until the WebGL preview shows something different from `before`. */
async function expectRedrawn(viewer: Locator, before: Buffer): Promise<Buffer> {
  let after = before;
  await expect
    .poll(async () => {
      after = await viewer.screenshot();
      return after.equals(before);
    })
    .toBe(false);
  return after;
}

function collectPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  return errors;
}

test("photo goes through analysis, recoloring and preview to the PDF (tech.md §10.11)", async ({ page }) => {
  const errors = collectPageErrors(page);
  await page.goto("/");
  await page.getByRole("checkbox", { name: /I consent to processing/ }).check();
  await page.getByLabel("Photo of a person").setInputFiles(PHOTO);

  const viewer = page.getByRole("img", { name: "3D skin preview" });
  await expect(viewer).toBeVisible();
  await expect(page.getByRole("group", { name: "Colors" })).toBeVisible();

  // Recoloring the T-shirt goes through the debounced /skin and redraws the preview.
  const before = await viewer.screenshot();
  const restyled = page.waitForResponse((r) => r.url().endsWith("/api/v1/skin") && r.ok());
  await page.getByLabel("T-shirt").fill("#ff0000");
  await restyled;
  await expectRedrawn(viewer, before);

  await page.getByRole("button", { name: "Next" }).click();
  const [pdfDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download PDF" }).click(),
  ]);
  const pdf = await saved(pdfDownload);
  expect(pdf.subarray(0, 4).toString("latin1")).toBe("%PDF");

  expect(errors).toEqual([]);
});

test("imported skin goes through preview to the PNG and the PDF", async ({ page }) => {
  const errors = collectPageErrors(page);
  await page.goto("/");
  const viewer = page.getByRole("img", { name: "3D skin preview" });

  await page.getByRole("radio", { name: "Ready skin" }).click();
  await page.getByLabel("Ready skin").setInputFiles(SKIN);
  await expect(viewer).toBeVisible();
  await expect(page.getByRole("heading", { name: "Preview" })).toBeFocused();

  // A blank or broken WebGL canvas would look the same from both sides.
  const front = await viewer.screenshot();
  await page.getByRole("radio", { name: "Back" }).click();
  const back = await expectRedrawn(viewer, front);
  await page.getByRole("radio", { name: "Slim" }).click();
  await expectRedrawn(viewer, back);

  await page.getByRole("button", { name: "Next" }).click();
  const [pngDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download skin PNG" }).click(),
  ]);
  const png = await saved(pngDownload);
  expect(png.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)).toBe(true);

  const [pdfDownload] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download PDF" }).click(),
  ]);
  expect(pdfDownload.suggestedFilename()).toBe("real2block-figure.pdf");
  const pdf = await saved(pdfDownload);
  expect(pdf.length).toBeGreaterThan(0);
  expect(pdf.subarray(0, 4).toString("latin1")).toBe("%PDF");

  expect(errors).toEqual([]);
});

test("privacy policy is served on its own path in both languages", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByRole("heading", { level: 1, name: "Privacy policy" })).toBeVisible();
  await page.getByRole("radio", { name: "RU" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Политика приватности" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await page.getByRole("link", { name: "К приложению" }).click();
  await expect(page.getByLabel("Photo of a person")).toBeVisible();
});
