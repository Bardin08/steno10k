import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
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
    data: [
      {
        id: "1",
        slug: "con-law",
        title: "Con Law",
        sets: [
          {
            id: "s1",
            slug: "judicial-review",
            title: "Judicial Review",
            project_slug: "con-law",
            recordings: [],
            stages: {},
          },
        ],
      },
    ],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useProjects>);
  renderSidebar();
  expect(screen.getByText("Con Law")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /Judicial Review/ }),
  ).toBeInTheDocument();
});

test("shows empty state when there are no projects", () => {
  vi.spyOn(hooks, "useProjects").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useProjects>);
  renderSidebar();
  expect(screen.getByText(/no projects/i)).toBeInTheDocument();
});

test("the new-project dialog submits the typed title", () => {
  vi.spyOn(hooks, "useProjects").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useProjects>);
  const mutate = vi.fn();
  vi.spyOn(hooks, "useCreateProject").mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof hooks.useCreateProject>);

  renderSidebar();
  fireEvent.click(screen.getByRole("button", { name: /project/i }));
  fireEvent.change(screen.getByLabelText(/project title/i), {
    target: { value: "Con Law" },
  });
  fireEvent.click(screen.getByRole("button", { name: /create project/i }));

  expect(mutate).toHaveBeenCalledWith("Con Law", expect.anything());
});

test("blocks creating a project whose name already exists", () => {
  vi.spyOn(hooks, "useProjects").mockReturnValue({
    data: [{ id: "1", slug: "con-law", title: "Con Law", sets: [] }],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useProjects>);
  const mutate = vi.fn();
  vi.spyOn(hooks, "useCreateProject").mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof hooks.useCreateProject>);

  renderSidebar();
  fireEvent.click(screen.getByRole("button", { name: "project" }));
  fireEvent.change(screen.getByLabelText(/project title/i), {
    target: { value: "con law" }, // case-insensitive clash with "Con Law"
  });
  fireEvent.click(screen.getByRole("button", { name: /create project/i }));

  expect(mutate).not.toHaveBeenCalled();
  expect(screen.getByText(/already exists/i)).toBeInTheDocument();
});
