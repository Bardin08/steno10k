import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { Card } from "./Card";
import { Skeleton } from "./Skeleton";
import { ErrorState } from "./ErrorState";
import { EmptyState } from "./EmptyState";

test("Card renders children in a region", () => {
  render(<Card aria-label="panel">body</Card>);
  expect(screen.getByLabelText("panel")).toHaveTextContent("body");
});

test("Skeleton exposes an accessible busy status", () => {
  render(<Skeleton />);
  expect(screen.getByRole("status")).toBeInTheDocument();
});

test("ErrorState shows message and a retry action", () => {
  const onRetry = vi.fn();
  render(<ErrorState message="Load failed" onRetry={onRetry} />);
  screen.getByRole("button", { name: /retry/i }).click();
  expect(onRetry).toHaveBeenCalledOnce();
});

test("EmptyState shows title and description", () => {
  render(
    <EmptyState title="No recordings" description="Drop audio to start." />,
  );
  expect(screen.getByText("No recordings")).toBeInTheDocument();
  expect(screen.getByText("Drop audio to start.")).toBeInTheDocument();
});
