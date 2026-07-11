import { act, render, renderHook, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";
import { useReducedMotion } from "./useReducedMotion";
import { setReducedMotion } from "../test/matchMedia";

function Toggle() {
  const { theme, toggle } = useTheme();
  return (
    <button onClick={toggle} data-theme-state={theme}>
      toggle
    </button>
  );
}

test("provider defaults to light and flips data-theme on <html>", () => {
  render(
    <ThemeProvider>
      <Toggle />
    </ThemeProvider>,
  );
  const btn = screen.getByRole("button");
  expect(btn.getAttribute("data-theme-state")).toBe("light");
  expect(document.documentElement.dataset.theme).toBe("light");
  act(() => btn.click());
  expect(document.documentElement.dataset.theme).toBe("dark");
});

test("useReducedMotion reads the media query", () => {
  setReducedMotion(true);
  const { result } = renderHook(() => useReducedMotion());
  expect(result.current).toBe(true);
  setReducedMotion(false);
});
