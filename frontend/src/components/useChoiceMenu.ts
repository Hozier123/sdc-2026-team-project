import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { finishWhenHidden, gsap, useGSAP } from "../lib/motion";

/** Shared focus, placement and dismissal for menus and form selection lists. */
export function useChoiceMenu(
  align: "start" | "end" = "start",
  {
    matchTrigger = false,
    maxWidth = 300,
    itemRole = "menuitemradio",
  }: { matchTrigger?: boolean; maxWidth?: number; itemRole?: "menuitemradio" | "option" } = {},
) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{
    left: number;
    top: number;
    width: number;
    maxHeight: number;
  } | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const id = useId();
  const typed = useRef({ text: "", at: 0 });
  const close = (restore = false) => {
    setOpen(false);
    if (restore) trigger.current?.focus();
  };
  const toggle = () => {
    setPosition(null);
    setOpen((value) => !value);
  };
  const onTriggerKeyDown = (event: KeyboardEvent) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
    }
  };
  const onMenuKeyDown = (event: KeyboardEvent) => {
    const items = Array.from(
      menu.current?.querySelectorAll<HTMLButtonElement>(
        `[role="${itemRole}"]`,
      ) ?? [],
    );
    const current = items.indexOf(document.activeElement as HTMLButtonElement);
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      event.stopPropagation();
      const index =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? items.length - 1
            : (current + (event.key === "ArrowDown" ? 1 : -1) + items.length) %
              items.length;
      items[index]?.focus();
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
    } else if (event.key === "Tab") close(true);
    else if (event.key.length === 1 && event.key !== " " && !event.metaKey && !event.ctrlKey && !event.altKey) {
      const now = Date.now();
      typed.current.text = (now - typed.current.at < 600 ? typed.current.text : "") + event.key.toLocaleLowerCase();
      typed.current.at = now;
      const label = (item: HTMLButtonElement) => (item.dataset.label ?? item.textContent ?? "").toLocaleLowerCase();
      const found = items.find(item => label(item).startsWith(typed.current.text))
        ?? items.find(item => label(item).startsWith(event.key.toLocaleLowerCase()));
      if (found) {
        event.preventDefault();
        found.focus();
      }
    }
  };

  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const anchor = trigger.current?.getBoundingClientRect();
      if (!anchor) return;
      if (getComputedStyle(trigger.current!).visibility === "hidden" || anchor.bottom <= 0 || anchor.top >= innerHeight) {
        setOpen(false);
        return;
      }
      const width = Math.min(matchTrigger ? anchor.width : maxWidth, maxWidth, innerWidth - 32);
      const height = Math.min((menu.current?.scrollHeight ?? 258) + 2, 420);
      const below = Math.max(0, innerHeight - anchor.bottom - 20);
      const above = Math.max(0, anchor.top - 20);
      const down = below >= height || (above < height && (below >= Math.min(height, 200) || below >= above));
      const maxHeight = Math.min(420, down ? below : above);
      setPosition({
        left: Math.max(
          16,
          Math.min(
            align === "end" ? anchor.right - width : anchor.left,
            innerWidth - width - 16,
          ),
        ),
        top: down ? anchor.bottom + 8 : anchor.top - Math.min(height, maxHeight) - 8,
        width,
        maxHeight,
      });
    };
    place();
    const observer = new ResizeObserver(place);
    if (menu.current) observer.observe(menu.current);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
      observer.disconnect();
    };
  }, [open, align, matchTrigger, maxWidth]);
  const positioned = position !== null;
  useGSAP(() => {
    const element = menu.current;
    if (!open || !positioned || !element) return;
    const anchor = trigger.current?.getBoundingClientRect();
    const below = !anchor || element.getBoundingClientRect().top >= anchor.bottom;
    const media = gsap.matchMedia();
    media.add({ reduce: "(prefers-reduced-motion: reduce)", normal: "(prefers-reduced-motion: no-preference)" }, (context) => {
      const reduce = context.conditions?.reduce;
      const tween = gsap.from(element, {
        opacity: 0.55, y: reduce ? 0 : below ? -6 : 6,
        scale: reduce ? 1 : 0.985, transformOrigin: below ? "top center" : "bottom center",
        duration: reduce ? 0.1 : 0.18, ease: "power3.out",
        clearProps: "opacity,transform,transformOrigin",
      });
      return finishWhenHidden(tween);
    });
    return () => media.revert();
  }, { scope: menu, dependencies: [open, positioned], revertOnUpdate: true });
  useLayoutEffect(() => {
    if (open && positioned) {
      const selected = menu.current?.querySelector<HTMLElement>('[aria-checked="true"], [aria-selected="true"]');
      const active = selected ?? menu.current?.querySelector<HTMLElement>(`[role="${itemRole}"]`);
      active?.focus({ preventScroll: true });
      active?.scrollIntoView({ block: "nearest" });
      typed.current = { text: "", at: 0 };
    }
  }, [open, positioned, itemRole]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !trigger.current?.contains(event.target) &&
        !menu.current?.contains(event.target)
      )
        setOpen(false);
    };
    document.addEventListener("pointerdown", outside, true);
    return () => document.removeEventListener("pointerdown", outside, true);
  }, [open]);
  return {
    open,
    position,
    trigger,
    menu,
    id,
    close,
    toggle,
    onTriggerKeyDown,
    onMenuKeyDown,
  };
}
