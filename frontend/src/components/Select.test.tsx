import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test } from "vitest";
import { Select } from "./Select";

test("open content does not use the centered modal-in keyframe", () => {
  render(
    <Select
      label="Model"
      value="small"
      onValueChange={() => {}}
      options={[{ value: "small" }, { value: "medium" }]}
    />,
  );
  fireEvent.click(screen.getByRole("combobox"));
  expect(screen.getByRole("listbox").className).not.toMatch(/modal-in/);
});
