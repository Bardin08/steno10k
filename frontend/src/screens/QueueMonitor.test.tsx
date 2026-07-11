import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { QueueMonitor, type QueueItem } from "./QueueMonitor";
import { setReducedMotion } from "../test/matchMedia";

const items: QueueItem[] = [
  {
    id: "1",
    title: "Judicial Review — parts 1–3",
    sub: "3 recordings · 02:41:12 · large-v3",
    status: "run",
    statusLabel: "transcribing",
    progress: 64,
  },
];

test("ready state renders the queue rows", () => {
  render(<QueueMonitor state="ready" items={items} />);
  expect(screen.getByText(/Judicial Review/)).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute(
    "aria-valuenow",
    "64",
  );
});

test("loading state renders skeletons", () => {
  render(<QueueMonitor state="loading" items={[]} />);
  expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
});

test("empty state renders the EmptyState", () => {
  render(<QueueMonitor state="empty" items={[]} />);
  expect(screen.getByText(/no recordings/i)).toBeInTheDocument();
});

test("error state renders the ErrorState", () => {
  render(<QueueMonitor state="error" items={[]} />);
  expect(screen.getByText(/couldn't load/i)).toBeInTheDocument();
});

test("reduced motion removes the staggered reveal", () => {
  setReducedMotion(true);
  const { container } = render(<QueueMonitor state="ready" items={items} />);
  expect(container.querySelector("[data-reveal]")).toBeNull();
  setReducedMotion(false);
});
