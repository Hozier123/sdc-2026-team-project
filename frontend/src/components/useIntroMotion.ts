import { useEffect, useRef, type RefObject } from "react";
import { advanceSpring } from "../lib/spring";

export function useIntroMotion(
  rootRef: RefObject<HTMLDivElement | null>,
  atmosphereRef: RefObject<HTMLDivElement | null>,
  enterRef: RefObject<HTMLSpanElement | null>,
  paused: boolean,
) {
  const ringRef = useRef<HTMLDivElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);
  const pointer = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const root = rootRef.current,
      ring = ringRef.current,
      dot = dotRef.current;
    if (!root || !ring || !dot) return;
    const media = matchMedia("(hover: hover) and (pointer: fine)");
    const x = { value: 0, velocity: 0 },
      y = { value: 0, velocity: 0 };
    const px = { value: 0, velocity: 0 },
      py = { value: 0, velocity: 0 };
    const size = { value: 1, velocity: 0 };
    const magnetX = { value: 0, velocity: 0 },
      magnetY = { value: 0, velocity: 0 };
    let targetX = 0,
      targetY = 0,
      visible = false,
      down = false,
      hovering = false;
    let anchor: DOMRect | undefined;
    let frame = 0,
      last = 0;
    const measure = () => {
      anchor = enterRef.current?.getBoundingClientRect();
    };
    const hide = () => {
      visible = false;
      down = false;
      hovering = false;
      root.dataset.cursorVisible = "false";
      ring.dataset.visible = dot.dataset.visible = "false";
    };
    const move = (event: PointerEvent) => {
      if (paused || !media.matches || event.pointerType !== "mouse") return;
      targetX = event.clientX;
      targetY = event.clientY;
      hovering =
        event.target instanceof Element &&
        !!event.target.closest("[data-greeting], #intro-enter-hint");
      if (!visible) {
        x.value = targetX;
        y.value = targetY;
        x.velocity = y.velocity = 0;
        visible = true;
        root.dataset.cursorVisible = "true";
        ring.dataset.visible = dot.dataset.visible = "true";
      }
      dot.style.transform = `translate3d(${targetX}px, ${targetY}px, 0)`;
    };
    const press = () => {
      down = true;
    };
    const release = () => {
      down = false;
    };
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Tab") hide();
    };
    const updateMedia = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      last = 0;
      if (!media.matches || paused) {
        hide();
        pointer.current.x = pointer.current.y = 0;
        if (atmosphereRef.current) atmosphereRef.current.style.transform = "";
        if (enterRef.current) enterRef.current.style.transform = "";
        root.dataset.cursorRunning = "false";
      } else {
        root.dataset.cursorRunning = "true";
        frame = requestAnimationFrame(tick);
      }
    };
    const tick = (now: number) => {
      if (paused || !media.matches) return;
      const dt = last ? (now - last) / 1000 : 1 / 60;
      last = now;
      const sx = advanceSpring(x, targetX, dt, 220, 23);
      const sy = advanceSpring(y, targetY, dt, 220, 23);
      const scale = advanceSpring(
        size,
        down ? 0.72 : hovering ? 1.5 : 1,
        dt,
        260,
        18,
      );
      const nx = visible ? (targetX / innerWidth) * 2 - 1 : 0;
      const ny = visible ? (targetY / innerHeight) * 2 - 1 : 0;
      pointer.current.x = advanceSpring(px, nx, dt, 65, 14);
      pointer.current.y = advanceSpring(py, ny, dt, 65, 14);
      ring.style.transform = `translate3d(${sx}px, ${sy}px, 0) scale(${scale})`;
      if (atmosphereRef.current)
        atmosphereRef.current.style.transform = `translate3d(${-pointer.current.x * 20}px, ${-pointer.current.y * 14}px, 0)`;
      let mx = 0,
        my = 0;
      if (visible && anchor) {
        const dx = targetX - (anchor.left + anchor.width / 2);
        const dy = targetY - (anchor.top + anchor.height / 2);
        const proximity = Math.max(0, 1 - Math.hypot(dx, dy) / 180);
        mx = dx * proximity * 0.15;
        my = dy * proximity * 0.15;
      }
      const tx = advanceSpring(magnetX, mx, dt, 180, 17);
      const ty = advanceSpring(magnetY, my, dt, 180, 17);
      if (enterRef.current)
        enterRef.current.style.transform = `translate3d(${tx}px, ${ty}px, 0)`;
      frame = requestAnimationFrame(tick);
    };
    measure();
    root.addEventListener("pointermove", move, { passive: true });
    root.addEventListener("pointerleave", hide);
    root.addEventListener("pointerdown", press, { passive: true });
    window.addEventListener("pointerup", release, { passive: true });
    window.addEventListener("pointercancel", hide);
    window.addEventListener("blur", hide);
    window.addEventListener("keydown", keyboard);
    window.addEventListener("resize", measure);
    media.addEventListener("change", updateMedia);
    updateMedia();
    return () => {
      cancelAnimationFrame(frame);
      root.removeEventListener("pointermove", move);
      root.removeEventListener("pointerleave", hide);
      root.removeEventListener("pointerdown", press);
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", hide);
      window.removeEventListener("blur", hide);
      window.removeEventListener("keydown", keyboard);
      window.removeEventListener("resize", measure);
      media.removeEventListener("change", updateMedia);
      delete root.dataset.cursorVisible;
      delete root.dataset.cursorRunning;
    };
  }, [rootRef, atmosphereRef, enterRef, paused]);

  return { ringRef, dotRef, pointer };
}
