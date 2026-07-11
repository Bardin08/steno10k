import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { StatusPill } from "./StatusPill";
import { ProgressBar } from "./ProgressBar";
import { QueueRow } from "./QueueRow";

test("StatusPill carries its status as a data attribute", () => {
  render(<StatusPill status="run">transcribing</StatusPill>);
  const pill = screen.getByText("transcribing");
  expect(pill).toHaveAttribute("data-status", "run");
});

test("ProgressBar exposes value via ARIA and clamps to 0..100", () => {
  render(<ProgressBar value={140} />);
  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveAttribute("aria-valuenow", "100");
});

test("QueueRow shows title, mono sub, and status", () => {
  render(
    <QueueRow
      title="Judicial Review — parts 1–3"
      sub="3 recordings · 02:41:12 · large-v3"
      status="run"
      statusLabel="transcribing"
    />,
  );
  expect(screen.getByText(/Judicial Review/)).toBeInTheDocument();
  expect(screen.getByText("transcribing")).toHaveAttribute(
    "data-status",
    "run",
  );
});
