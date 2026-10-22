/** Shares the same pause signal with video, WebGL and pointer animation. */
export function watchPageVisibility(
  source: Pick<Document, "hidden" | "addEventListener" | "removeEventListener">,
  update: (visible: boolean) => void,
) {
  const changed = () => update(!source.hidden);
  source.addEventListener("visibilitychange", changed);
  changed();
  return () => source.removeEventListener("visibilitychange", changed);
}
