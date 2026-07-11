import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { makeQueryClient } from "../../app/queryClient";
import * as hooks from "../../api/hooks";
import { RecordingsTab } from "./RecordingsTab";

afterEach(() => vi.restoreAllMocks());

function noopMutation() {
  return { mutate: vi.fn(), isPending: false } as unknown;
}

function renderTab() {
  vi.spyOn(hooks, "useUploadRecordings").mockReturnValue(
    noopMutation() as ReturnType<typeof hooks.useUploadRecordings>,
  );
  vi.spyOn(hooks, "useDeleteRecording").mockReturnValue(
    noopMutation() as ReturnType<typeof hooks.useDeleteRecording>,
  );
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <RecordingsTab project="con-law" set="jr" />
    </QueryClientProvider>,
  );
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
