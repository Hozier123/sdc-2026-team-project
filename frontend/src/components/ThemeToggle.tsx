import { Moon, Sun } from "lucide-react";
import { toggleTheme, useTheme } from "../lib/theme";

export function ThemeToggle({ intro = false }: { intro?: boolean }) {
  const light = useTheme() === "light";
  const label = light ? "Switch to dark mode" : "Switch to light mode";
  return (
    <button
      className={`theme-toggle${intro ? " theme-toggle-intro" : ""}`}
      title={label}
      aria-label={label}
      aria-pressed={light}
      // The reveal grows out of this control, wherever it sits on screen.
      onClick={(event) => toggleTheme(event.currentTarget)}
    >
      <span className="theme-toggle-icon" data-light={light} aria-hidden="true">
        <Sun size={17} className="theme-toggle-sun" />
        <Moon size={17} className="theme-toggle-moon" />
      </span>
      <span className="theme-toggle-label">{light ? "Dark mode" : "Light mode"}</span>
    </button>
  );
}
