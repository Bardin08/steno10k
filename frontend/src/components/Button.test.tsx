import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { Button } from "./Button";

test("renders label and fires onClick", async () => {
  const onClick = vi.fn();
  render(<Button onClick={onClick}>Run it</Button>);
  const btn = screen.getByRole("button", { name: "Run it" });
  btn.click();
  expect(onClick).toHaveBeenCalledOnce();
});

test("primary is the default variant; ghost opts out", () => {
  const { rerender } = render(<Button>Go</Button>);
  expect(screen.getByRole("button")).toHaveAttribute("data-variant", "primary");
  rerender(<Button variant="ghost">Go</Button>);
  expect(screen.getByRole("button")).toHaveAttribute("data-variant", "ghost");
});
