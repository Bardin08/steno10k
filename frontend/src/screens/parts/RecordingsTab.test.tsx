import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, expect, test, vi } from "vitest";
import { makeQueryClient } from "../../app/queryClient";
import * as hooks from "../../api/hooks";
import { RecordingsTab } from "./RecordingsTab";

afterEach(() => vi.restoreAllMocks());

function noopMutation() {
  return { mutate: vi.fn(), isPending: false } as unknown;
}

function mutationSpy() {
  return { mutate: vi.fn(), isPending: false };
}

function mockCommon() {
  vi.spyOn(hooks, "useUploadRecordings").mockReturnValue(
    noopMutation() as ReturnType<typeof hooks.useUploadRecordings>,
  );
  vi.spyOn(hooks, "useDeleteRecording").mockReturnValue(
    noopMutation() as ReturnType<typeof hooks.useDeleteRecording>,
  );
  vi.spyOn(hooks, "useCancelRun").mockReturnValue(
    noopMutation() as ReturnType<typeof hooks.useCancelRun>,
  );
  vi.spyOn(hooks, "useRuns").mockReturnValue({
    data: [],
  } as unknown as ReturnType<typeof hooks.useRuns>);
  vi.spyOn(hooks, "useConfig").mockReturnValue({
    data: {
      stages: {
        enabled: { normalize: true, chunk: true, transcribe: true },
      },
    },
  } as unknown as ReturnType<typeof hooks.useConfig>);
}

function renderTab(enqueue = mutationSpy()) {
  mockCommon();
  vi.spyOn(hooks, "useEnqueueRun").mockReturnValue(
    enqueue as unknown as ReturnType<typeof hooks.useEnqueueRun>,
  );
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <MemoryRouter>
        <RecordingsTab project="con-law" set="jr" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return enqueue;
}

test("lists recordings", () => {
  vi.spyOn(hooks, "useRecordings").mockReturnValue({
    data: [
      {
        source_name: "lecture1.mp3",
        normalized_name: "lecture1.mp3",
        duration_seconds: 3600,
        chunks: ["a", "b"],
      },
    ],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useRecordings>);
  renderTab();
  expect(screen.getByText("lecture1.mp3")).toBeInTheDocument();
});

test("empty state when no recordings", () => {
  vi.spyOn(hooks, "useRecordings").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useRecordings>);
  renderTab();
  expect(screen.getByText(/drop audio/i)).toBeInTheDocument();
});

test("clicking Transcribe enqueues a run for this project/set and shows the pipeline", () => {
  vi.spyOn(hooks, "useRecordings").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useRecordings>);
  const enqueue = renderTab();
  fireEvent.click(screen.getByRole("button", { name: "Transcribe" }));
  expect(enqueue.mutate).toHaveBeenCalledWith(
    { project: "con-law", set: "jr" },
    expect.anything(),
  );
  expect(screen.getByText(/pipeline · idle/i)).toBeInTheDocument();
});

test("gear opens the run settings modal", () => {
  vi.spyOn(hooks, "useRecordings").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useRecordings>);
  renderTab();
  fireEvent.click(screen.getByRole("button", { name: /run settings/i }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});

test("confirming the modal with force enqueues force: true", () => {
  vi.spyOn(hooks, "useRecordings").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useRecordings>);
  const enqueue = renderTab();
  fireEvent.click(screen.getByRole("button", { name: /run settings/i }));
  const dialog = screen.getByRole("dialog");
  fireEvent.click(
    within(dialog).getByRole("switch", { name: /re-run from scratch/i }),
  );
  fireEvent.click(within(dialog).getByRole("button", { name: /transcribe/i }));
  expect(enqueue.mutate).toHaveBeenCalledWith(
    { project: "con-law", set: "jr", force: true },
    expect.anything(),
  );
});
