import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { makeQueryClient } from "../../app/queryClient";
import * as hooks from "../../api/hooks";
import { ArtifactsTab } from "./ArtifactsTab";

afterEach(() => vi.restoreAllMocks());

function renderTab() {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <ArtifactsTab project="con-law" set="jr" />
    </QueryClientProvider>,
  );
}

test("lists artifacts", () => {
  vi.spyOn(hooks, "useArtifacts").mockReturnValue({
    data: [
      { name: "summary.md", kind: "text", size: 1200, stage: "summarize" },
    ],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useArtifacts>);
  renderTab();
  expect(screen.getByText("summary.md")).toBeInTheDocument();
});

test("pending state shows skeleton placeholders when no artifacts", () => {
  vi.spyOn(hooks, "useArtifacts").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useArtifacts>);
  renderTab();
  expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
});
