import { useRef, useState, type RefObject } from "react";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { finishWhenHidden, gsap, useGSAP } from "../lib/motion";
import { watchPageVisibility } from "../lib/page-visibility";
import { INTRO_CLOSE_AT, INTRO_WINDOWS, introChapterAt, type IntroChapter } from "../lib/intro-depth";

gsap.registerPlugin(ScrollTrigger);

type IntroLayers = {
  background: RefObject<HTMLDivElement | null>;
  scene: RefObject<HTMLDivElement | null>;
  foreground: RefObject<HTMLDivElement | null>;
  opening: RefObject<HTMLElement | null>;
  notes: RefObject<(HTMLElement | null)[]>;
  closing: RefObject<HTMLDivElement | null>;
  entry: RefObject<HTMLDivElement | null>;
  stages: number;
};

export function useIntroChoreography(root: RefObject<HTMLDivElement | null>, layers: IntroLayers) {
  const [chapter, setChapter] = useState<IntroChapter>("welcome");
  const [reduced, setReduced] = useState(false);
  const currentChapter = useRef<IntroChapter>("welcome");
  const welcomed = useRef(false);
  useGSAP(() => {
    const element = root.current;
    const { background, scene, foreground, opening, notes, closing, entry, stages } = layers;
    if (!element || !background.current || !scene.current || !foreground.current || !opening.current || !closing.current || !entry.current) return;
    const entryAnchor = entry.current.querySelector<HTMLElement>("[data-intro-entry-anchor]");
    const entrySlot = closing.current.querySelector<HTMLElement>("[data-intro-entry-slot]");
    if (!entryAnchor || !entrySlot) return;
    const media = gsap.matchMedia();
    media.add({ reduce: "(prefers-reduced-motion: reduce)", normal: "(prefers-reduced-motion: no-preference)", phone: "(max-width: 760px)" }, (context) => {
      // This homepage explicitly opts into full motion at the user's request.
      // Other consumers can retain the system fallback by omitting that policy.
      const reduce = !!context.conditions?.reduce && element.dataset.motionPolicy !== "full";
      const phone = !!context.conditions?.phone;
      setReduced(reduce);
      const select = gsap.utils.selector(element);
      const duration = stages - 1;
      const at = (progress: number) => progress * duration;
      // Separate planes keep GSAP away from the spring and WebGL local transforms.
      gsap.set(background.current, { z: reduce ? 0 : -360, scale: reduce ? 1 : 1.3, y: 0, rotation: 0 });
      gsap.set(scene.current, { z: reduce ? 0 : -100, scale: reduce ? 1 : 1.09, y: 0, x: reduce ? 0 : innerWidth * (phone ? 0.05 : 0.18), rotationY: 0, opacity: phone ? 0.6 : 1 });
      gsap.set(foreground.current, { z: reduce ? 0 : 120, scale: reduce ? 1 : 0.9 });
      gsap.set(entry.current, { y: 0 });
      let welcome: gsap.core.Timeline | undefined;
      if (!welcomed.current) {
        element.dataset.motionPhase = "welcome";
        welcome = gsap.timeline({
          defaults: { ease: "power3.out", clearProps: "opacity,transform" },
          onComplete: () => { welcomed.current = true; element.dataset.motionPhase = "ready"; },
        });
        welcome.from(select("[data-intro-welcome]"), { opacity: 0.6, scale: reduce ? 1 : 1.035, duration: reduce ? 0.12 : 0.7 }, 0)
          .from(select("[data-intro-brand], [data-intro-prompt]"), { opacity: 0.7, duration: reduce ? 0.12 : 0.35 }, 0);
      } else element.dataset.motionPhase = "ready";

      const story = gsap.timeline({
        defaults: { ease: "none" },
        onUpdate: () => {
          const progress = story.progress();
          element.dataset.storyProgress = progress.toFixed(3);
          const next = introChapterAt(progress);
          if (next !== currentChapter.current) { currentChapter.current = next; setChapter(next); }
        },
        scrollTrigger: {
          id: "intro-depth", trigger: element, start: "top top",
          end: () => `+=${Math.max(1, element.offsetHeight - innerHeight)}`,
          scrub: reduce ? true : 0.55, invalidateOnRefresh: true,
        },
      });
      story.to(background.current, { z: reduce ? 0 : -240, scale: reduce ? 1 : 1.26, y: reduce ? 0 : -(phone ? 30 : 80), rotation: reduce ? 0 : 2.4, duration }, 0)
        .to(scene.current, { z: reduce ? 0 : 87.2, scale: reduce ? 1 : 1.02, y: reduce ? 0 : -(phone ? 74 : 164), duration: at(0.78) }, 0)
        .to(scene.current, { z: reduce ? 0 : -220, scale: reduce ? 1 : 1.25, y: reduce ? 0 : -(phone ? 80 : 180), duration: at(0.14), ease: "power2.inOut" }, at(0.78));
      // The language field yields to the current reading side.
      [
        { start: 0.32, end: 0.43, x: -0.2, rotate: 7 },
        { start: 0.54, end: 0.65, x: 0.2, rotate: -5 },
        { start: 0.76, end: 0.88, x: 0, rotate: 0 },
      ].forEach(pose => story.to(scene.current, {
        x: () => reduce ? 0 : innerWidth * pose.x * (phone ? 0.35 : 1), rotationY: reduce ? 0 : pose.rotate,
        duration: at(pose.end - pose.start), ease: "power2.inOut",
      }, at(pose.start)));
      gsap.set(notes.current.filter(Boolean), { autoAlpha: 0 });
      gsap.set(closing.current, { autoAlpha: 0 });
      gsap.set(opening.current, { autoAlpha: 1, z: 0, y: 0 });
      story.to(opening.current, { autoAlpha: 0, z: reduce ? 0 : 220, y: reduce ? 0 : -80, duration: at(0.1) }, at(0.08));
      notes.current.forEach((note, index) => {
        if (!note) return;
        const window = INTRO_WINDOWS[index];
        const pose = index === 1 ? { x: phone ? 28 : 70, y: 0, rotationY: phone ? -3 : -7 }
          : { x: 0, y: phone ? 65 : index === 2 ? 110 : 130, rotationY: 0 };
        story.fromTo(note, { autoAlpha: 0, z: reduce ? 0 : index === 2 ? -180 : -120, x: reduce ? 0 : pose.x, y: reduce ? 0 : pose.y, rotationY: reduce ? 0 : pose.rotationY },
          { autoAlpha: 1, z: 0, x: 0, y: 0, rotationY: 0, ease: "power2.out", duration: at(window.full - window.enter) }, at(window.enter))
          .to(note, { autoAlpha: 0, z: reduce ? 0 : 240, y: reduce ? 0 : -85, duration: at(window.gone - window.exit) }, at(window.exit));
      });
      story.fromTo(closing.current, { autoAlpha: 0, z: reduce ? 0 : -40, y: reduce ? 0 : 24 }, { autoAlpha: 1, z: 0, y: 0, duration: at(0.08), ease: "power2.out" }, at(INTRO_CLOSE_AT))
        // Move the fixed dock; the pointer spring continues to own the inner button.
        .fromTo(entry.current, { y: 0 }, { y: () => {
          const target = foreground.current!.getBoundingClientRect().top + entrySlot.offsetTop + entrySlot.offsetHeight / 2;
          const origin = entry.current!.offsetTop + entryAnchor.offsetTop + entryAnchor.offsetHeight / 2;
          return target - origin;
        }, duration: at(0.08), ease: "power2.inOut" }, at(INTRO_CLOSE_AT))
        .to(select("[data-intro-scroll-hint]"), { autoAlpha: 0, duration: at(0.08) }, at(0.76))
        .to(select("[data-intro-story-shade]"), { opacity: 0.36, duration: at(0.1) }, at(0.1))
        .to(scene.current, { opacity: 0.28, duration: at(0.16) }, at(0.76));
      const stopWelcome = welcome ? finishWhenHidden(welcome) : () => {};
      const trigger = story.scrollTrigger!;
      const stopVisibility = watchPageVisibility(document, visible => {
        if (visible) trigger.enable(false, true);
        else { trigger.getTween()?.progress(1); trigger.disable(false); }
      });
      return () => {
        stopWelcome(); stopVisibility();
        delete element.dataset.motionPhase;
        delete element.dataset.storyProgress;
      };
    });
    return () => media.revert();
  }, { scope: root });
  return { chapter, reduced };
}
