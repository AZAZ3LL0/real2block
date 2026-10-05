import { useEffect, useRef } from "react";
import { isAbort, renderSkin, type SkinSpec } from "./api/client";

export const RESTYLE_DELAY_MS = 300;

export interface RestyleHandlers {
  onSkin: (skin: Blob) => void;
  onError: (err: unknown) => void;
}

/**
 * Re-renders the skin once the spec has been stable for RESTYLE_DELAY_MS.
 * A newer spec cancels the pending timer and aborts the request in flight,
 * so only the latest spec can reach the preview.
 */
export function useDebouncedSkin(spec: SkinSpec | null, handlers: RestyleHandlers): void {
  const latest = useRef(handlers);
  useEffect(() => {
    latest.current = handlers;
  });

  useEffect(() => {
    if (!spec) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      renderSkin(spec, controller.signal)
        .then((skin) => {
          if (!controller.signal.aborted) latest.current.onSkin(skin);
        })
        .catch((err: unknown) => {
          if (!isAbort(err) && !controller.signal.aborted) latest.current.onError(err);
        });
    }, RESTYLE_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [spec]);
}
