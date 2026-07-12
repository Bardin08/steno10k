import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ThemeProvider } from "./ThemeProvider";
import { ThemeToggle } from "./ThemeToggle";

test("toggles the document theme and its label", () => {
  render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  );
  // Defaults to light.
  expect(document.documentElement.dataset.theme).toBe("light");
  const toggle = screen.getByRole("button", { name: /switch to dark theme/i });

  fireEvent.click(toggle);
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(
    screen.getByRole("button", { name: /switch to light theme/i }),
  ).toBeInTheDocument();

  fireEvent.click(
    screen.getByRole("button", { name: /switch to light theme/i }),
  );
  expect(document.documentElement.dataset.theme).toBe("light");
});
