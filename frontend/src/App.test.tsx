import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";

test("renders the queue monitor with a live item", () => {
  render(<App />);
  expect(screen.getByText(/Judicial Review/)).toBeInTheDocument();
});
