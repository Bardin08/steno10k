import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, expect, test, vi } from "vitest";
import { makeQueryClient } from "../app/queryClient";
import * as hooks from "../api/hooks";
import { SetDetail } from "./SetDetail";

afterEach(() => vi.restoreAllMocks());

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/p/:project/s/:set" element={<SetDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("renders the set title and three tabs", () => {
  vi.spyOn(hooks, "useSet").mockReturnValue({
    data: { id: "s1", slug: "jr", title: "Judicial Review", project_slug: "con-law", recordings: [], stages: {} },
    isLoading: false, isError: false,
  } as unknown as ReturnType<typeof hooks.useSet>);
  renderAt("/p/con-law/s/jr");
  expect(screen.getByText("Judicial Review")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /recordings/i })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /run/i })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /artifacts/i })).toBeInTheDocument();
});
