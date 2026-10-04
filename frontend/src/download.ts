// Some browsers start the download asynchronously: revoking the URL right after
// click() can cancel it, and detached links may ignore the click altogether.
const REVOKE_DELAY_MS = 1000;

/** Hands a blob to the browser as a file download and releases its URL afterwards. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, REVOKE_DELAY_MS);
}
