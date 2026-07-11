import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, expect, test, vi } from "vitest";
import { makeQueryClient } from "../app/queryClient";
import * as hooks from "../api/hooks";
import { QueueScreen } from "./QueueScreen";

afterEach(() => vi.restoreAllMocks());

test("maps runs to queue rows with a link to the set run tab", () => {
  vi.spyOn(hooks, "useRuns").mockReturnValue({
    data: [{ id: "r1", project: "con-law", set_: "jr", status: "running", position: 1, stats: {} }],
    isLoading: false, isError: false,
  } as unknown as ReturnType<typeof hooks.useRuns>);
  vi.spyOn(hooks, "useProjects").mockReturnValue({
    data: [{ id: "1", slug: "con-law", title: "Con Law", sets: [
      { id: "s1", slug: "jr", title: "Judicial Review", project_slug: "con-law", recordings: [], stages: {} },
    ] }],
    isLoading: false, isError: false,
  } as unknown as ReturnType<typeof hooks.useProjects>);

  render(
    <QueryClientProvider client={makeQueryClient()}>
      <MemoryRouter><QueueScreen /></MemoryRouter>
    </QueryClientProvider>,
  );
  const link = screen.getByRole("link", { name: /Judicial Review/ });
  expect(link).toHaveAttribute("href", "/p/con-law/s/jr?tab=run");
});
