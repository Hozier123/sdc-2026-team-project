import type { RefObject } from "react";
import { finishWhenHidden, gsap, useGSAP } from "../lib/motion";

export function useWorkbenchMotion(root: RefObject<HTMLDivElement | null>) {
  useGSAP(() => {
    const element = root.current;
    if (!element) return;
    const media = gsap.matchMedia();
    media.add({ reduce: "(prefers-reduced-motion: reduce)", normal: "(prefers-reduced-motion: no-preference)" }, (context) => {
      const reduce = context.conditions?.reduce;
      const select = gsap.utils.selector(element);
      element.dataset.motionPhase = "entering";
      const timeline = gsap.timeline({
        defaults: { duration: reduce ? 0.12 : 0.28, ease: "power3.out", clearProps: "opacity,transform,clipPath" },
        onComplete: () => { element.dataset.motionPhase = "ready"; },
      });
      if (reduce) {
        timeline.from(element, { opacity: 0.8 });
      } else {
        timeline
          .from(select(".desk-heading h1"), { clipPath: "inset(0 0 100% 0)" }, 0)
          .from(select(".desk-stats .stat-card > div, .desk-stats .stat-card > strong"), {
            y: 8, opacity: 0.55, stagger: { amount: 0.09 },
          }, 0)
          .from(select(".desk-next"), { x: 14, opacity: 0.65, duration: 0.24 }, 0.08)
          .from(select(".queue-panel"), { y: 12, opacity: 0.7 }, 0.12)
          .from(select(".recent-activity"), { opacity: 0.6, duration: 0.2 }, 0.18);
      }
      const stop = finishWhenHidden(timeline);
      return () => { stop(); delete element.dataset.motionPhase; };
    });
    return () => media.revert();
  }, { scope: root });
}

export function useDialogMotion(root: RefObject<HTMLDivElement | null>) {
  useGSAP(() => {
    if (!root.current) return;
    const media = gsap.matchMedia();
    media.add({ reduce: "(prefers-reduced-motion: reduce)", normal: "(prefers-reduced-motion: no-preference)" }, (context) => {
      const reduce = context.conditions?.reduce;
      const timeline = gsap.timeline({ defaults: { ease: "power3.out", clearProps: "opacity,transform" } });
      timeline.from(root.current, { opacity: 0.65, duration: 0.15 })
        .from(root.current!.querySelector(".modal"), {
          opacity: 0.65, y: reduce ? 0 : 14, scale: reduce ? 1 : 0.985,
          duration: reduce ? 0.12 : 0.22,
        }, 0);
      return finishWhenHidden(timeline);
    });
    return () => media.revert();
  }, { scope: root });
}
