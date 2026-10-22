import { useEffect, useState } from "react";
import { watchPageVisibility } from "../lib/page-visibility";

export function usePageVisibility() {
  const [visible, setVisible] = useState(() => !document.hidden);
  useEffect(() => watchPageVisibility(document, setVisible), []);
  return visible;
}
