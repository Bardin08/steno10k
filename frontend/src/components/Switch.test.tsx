import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { Switch } from "./Switch";

test("renders label + description and toggles", () => {
  const onChange = vi.fn();
  render(
    <Switch
      label="Summarize with an LLM"
      description="Off = transcript only."
      checked={false}
      onCheckedChange={onChange}
    />,
  );
  expect(screen.getByText("Summarize with an LLM")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("switch"));
  expect(onChange).toHaveBeenCalledWith(true);
});
