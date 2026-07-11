import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Input } from "./Input";
import { Textarea } from "./Textarea";
import { Select } from "./Select";

test("Input shows label and inline error, links them via aria", () => {
  render(<Input label="Model" error="required" defaultValue="" />);
  const input = screen.getByLabelText("Model");
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(screen.getByText("required")).toBeInTheDocument();
});

test("Textarea renders its label", () => {
  render(<Textarea label="Prompt" />);
  expect(screen.getByLabelText("Prompt")).toBeInTheDocument();
});

test("Select renders options and its label", () => {
  render(
    <Select label="Language" defaultValue="en">
      <option value="en">English</option>
      <option value="uk">Ukrainian</option>
    </Select>,
  );
  expect(screen.getByLabelText("Language")).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Ukrainian" })).toBeInTheDocument();
});
