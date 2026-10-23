import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { watchPageVisibility } from "./page-visibility";

gsap.registerPlugin(useGSAP);

export { gsap, useGSAP };

/** Transient feedback finishes offscreen instead of returning half animated. */
export function finishWhenHidden(animation: gsap.core.Animation) {
  return watchPageVisibility(document, (visible) => {
    if (!visible && animation.progress() < 1) animation.progress(1);
  });
}
