export const INTRO_CHAPTERS = [
  { chapter: "read", enter: 0.18 },
  { chapter: "check", enter: 0.4 },
  { chapter: "approve", enter: 0.62 },
] as const;
export type IntroChapter = "welcome" | typeof INTRO_CHAPTERS[number]["chapter"] | "close";
export const INTRO_CLOSE_AT = 0.84;

/** Absolute progress keeps forward and reverse scroll symmetric. */
export function introChapterAt(progress: number): IntroChapter {
  const value = Number.isNaN(progress) ? 0 : Math.max(0, Math.min(1, progress));
  if (value >= INTRO_CLOSE_AT) return "close";
  for (let index = INTRO_CHAPTERS.length - 1; index >= 0; index--) {
    if (value >= INTRO_CHAPTERS[index].enter) return INTRO_CHAPTERS[index].chapter;
  }
  return "welcome";
}
