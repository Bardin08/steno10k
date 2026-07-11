import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";

test("renders the steno10k wordmark", () => {
  render(<App />);
  expect(screen.getByText(/steno/i)).toBeDefined();
});
