import { useEffect, useRef } from "react";
import { SkinViewer as Viewer3d } from "skinview3d";
import type { SkinModel } from "../api/client";

export type ViewSide = "front" | "back";

/**
 * Requested camera view. Each new object re-applies it, so picking the same side
 * again snaps back after the user has orbited the camera.
 */
export interface ViewRequest {
  side: ViewSide;
}

export interface SkinViewerProps {
  skin: Blob;
  model: SkinModel;
  view: ViewRequest;
  label: string;
  size?: number;
}

const MODEL_TYPES: Record<SkinModel, "default" | "slim"> = { classic: "default", slim: "slim" };
const SIDE_ROTATION: Record<ViewSide, number> = { front: 0, back: Math.PI };

/** The only place that imports skinview3d. */
export function SkinViewer({ skin, model, view, label, size = 320 }: SkinViewerProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const viewer = useRef<Viewer3d | null>(null);

  useEffect(() => {
    if (!canvas.current) return;
    const instance = new Viewer3d({ canvas: canvas.current, width: size, height: size });
    viewer.current = instance;
    return () => {
      instance.dispose();
      viewer.current = null;
    };
  }, [size]);

  useEffect(() => {
    const instance = viewer.current;
    if (!instance) return;
    const url = URL.createObjectURL(skin);
    instance
      .loadSkin(url, { model: MODEL_TYPES[model] })
      // A failed load leaves the previous skin on screen; the server already validated it.
      .catch(() => undefined)
      .finally(() => {
        URL.revokeObjectURL(url);
      });
  }, [skin, model, size]);

  useEffect(() => {
    const instance = viewer.current;
    if (!instance) return;
    instance.resetCameraPose();
    instance.playerObject.rotation.y = SIDE_ROTATION[view.side];
  }, [view, size]);

  return <canvas ref={canvas} role="img" aria-label={label} className="h-auto max-w-full touch-none" />;
}
