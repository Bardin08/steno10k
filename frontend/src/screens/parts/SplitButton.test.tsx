import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { SplitButton } from "./SplitButton";

test("fires onPrimary when the label is clicked and onGear when the gear is clicked", () => {
  const onPrimary = vi.fn();
  const onGear = vi.fn();
  render(
    <SplitButton label="Transcribe" onPrimary={onPrimary} onGear={onGear} />,
  );

  fireEvent.click(screen.getByRole("button", { name: "Transcribe" }));
  expect(onPrimary).toHaveBeenCalledTimes(1);
  expect(onGear).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: /run settings/i }));
  expect(onGear).toHaveBeenCalledTimes(1);
  expect(onPrimary).toHaveBeenCalledTimes(1);
});
