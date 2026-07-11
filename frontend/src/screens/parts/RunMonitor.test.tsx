import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { RunMonitor } from "./RunMonitor";
import type { RunView } from "../../api/sse";
import { STAGE_NAMES } from "../../api/types";

function view(overrides: Partial<RunView>): RunView {
  const stages = Object.fromEntries(
    STAGE_NAMES.map((s) => [s, { status: "queued" }]),
  );
  return {
    status: "running",
    stages,
    log: [],
    terminal: false,
    ...overrides,
  } as RunView;
}

test("renders a row per stage with the active one's progress", () => {
  const v = view({
    stages: {
      ...Object.fromEntries(STAGE_NAMES.map((s) => [s, { status: "queued" }])),
      transcribe: { status: "running", progress: 0.64 },
    } as RunView["stages"],
  });
  render(<RunMonitor view={v} onCancel={() => {}} />);
  expect(screen.getByText("transcribe")).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute(
    "aria-valuenow",
    "64",
  );
});

test("hides cancel when terminal", () => {
  render(
    <RunMonitor
      view={view({ status: "completed", terminal: true })}
      onCancel={() => {}}
    />,
  );
  expect(screen.queryByRole("button", { name: /cancel/i })).toBeNull();
});
