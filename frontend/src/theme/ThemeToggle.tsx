import { Moon, Sun } from "@phosphor-icons/react";
import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      className="grid h-8 w-8 place-items-center rounded-sm border border-hairline text-ink-faint transition-colors duration-[var(--dur-micro)] ease-editorial hover:text-ink"
    >
      {dark ? (
        <Sun size={15} weight="duotone" />
      ) : (
        <Moon size={15} weight="duotone" />
      )}
    </button>
  );
}
