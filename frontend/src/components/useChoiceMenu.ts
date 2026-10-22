import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

/** Shared focus, placement and dismissal behavior for company and role menus. */
export function useChoiceMenu(align: "start" | "end" = "start") {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{
    left: number;
    top: number;
    width: number;
  } | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const id = useId();
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
        '[role="menuitemradio"]',
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
  };

  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const anchor = trigger.current?.getBoundingClientRect();
      if (!anchor) return;
      if (getComputedStyle(trigger.current!).visibility === "hidden") {
        setOpen(false);
        return;
      }
      const width = Math.min(300, innerWidth - 32);
      const height = menu.current?.offsetHeight ?? 260;
      setPosition({
        left: Math.max(
          16,
          Math.min(
            align === "end" ? anchor.right - width : anchor.left,
            innerWidth - width - 16,
          ),
        ),
        top:
          anchor.bottom + height + 16 < innerHeight
            ? anchor.bottom + 8
            : Math.max(12, anchor.top - height - 8),
        width,
      });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open, align]);
  const positioned = position !== null;
  useLayoutEffect(() => {
    if (open && positioned)
      menu.current
        ?.querySelector<HTMLElement>('[aria-checked="true"]')
        ?.focus();
  }, [open, positioned]);
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
