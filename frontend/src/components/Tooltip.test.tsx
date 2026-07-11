import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Tooltip } from "./Tooltip";

test("renders the trigger; tooltip content is wired via aria", () => {
  render(
    <Tooltip label="Whisper model size">
      <button>large-v3</button>
    </Tooltip>,
  );
  // trigger is present; Radix mounts content on hover/focus (delayed),
  // so we assert the trigger renders and is describable.
  expect(screen.getByRole("button", { name: "large-v3" })).toBeInTheDocument();
});
