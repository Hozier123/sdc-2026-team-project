import { useSyncExternalStore } from "react";

const query = matchMedia("(max-width: 760px)");
const read = () => query.matches;
const subscribe = (listener: () => void) => {
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
};

/** Width changes select a profile; browser toolbar height changes do not. */
export function useIntroPhone() {
  return useSyncExternalStore(subscribe, read, () => false);
}
