export const INTRO_WINDOWS = [
  { chapter: "read", enter: 0.18, full: 0.24, exit: 0.32, gone: 0.38 },
  { chapter: "check", enter: 0.4, full: 0.46, exit: 0.54, gone: 0.6 },
  { chapter: "approve", enter: 0.62, full: 0.68, exit: 0.76, gone: 0.82 },
] as const;
export type IntroChapter = "welcome" | typeof INTRO_WINDOWS[number]["chapter"] | "close";
export const INTRO_CLOSE_AT = 0.84;

/** Absolute progress keeps forward and reverse scroll symmetric. */
export function introChapterAt(progress: number): IntroChapter {
  const value = Number.isNaN(progress) ? 0 : Math.max(0, Math.min(1, progress));
  if (value >= INTRO_CLOSE_AT) return "close";
  for (let index = INTRO_WINDOWS.length - 1; index >= 0; index--) {
    if (value >= INTRO_WINDOWS[index].enter) return INTRO_WINDOWS[index].chapter;
  }
  return "welcome";
}
