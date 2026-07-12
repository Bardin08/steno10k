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

test("Select renders its label and the selected option's text", () => {
  render(
    <Select
      label="Language"
      value="uk"
      options={[
        { value: "en", label: "English" },
        { value: "uk", label: "Ukrainian" },
      ]}
    />,
  );
  expect(screen.getByLabelText("Language")).toBeInTheDocument();
  // Closed trigger shows the selected option's label.
  expect(screen.getByText("Ukrainian")).toBeInTheDocument();
});
