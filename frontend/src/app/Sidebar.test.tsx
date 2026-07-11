import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, expect, test, vi } from "vitest";
import { makeQueryClient } from "./queryClient";
import * as hooks from "../api/hooks";
import { Sidebar } from "./Sidebar";

afterEach(() => vi.restoreAllMocks());

function renderSidebar() {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("renders projects and their sets", () => {
  vi.spyOn(hooks, "useProjects").mockReturnValue({
    data: [{ id: "1", slug: "con-law", title: "Con Law", sets: [
      { id: "s1", slug: "judicial-review", title: "Judicial Review", project_slug: "con-law", recordings: [], stages: {} },
    ] }],
    isLoading: false, isError: false,
  } as unknown as ReturnType<typeof hooks.useProjects>);
  renderSidebar();
  expect(screen.getByText("Con Law")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Judicial Review/ })).toBeInTheDocument();
});

test("shows empty state when there are no projects", () => {
  vi.spyOn(hooks, "useProjects").mockReturnValue({
    data: [], isLoading: false, isError: false,
  } as unknown as ReturnType<typeof hooks.useProjects>);
  renderSidebar();
  expect(screen.getByText(/no projects/i)).toBeInTheDocument();
});
