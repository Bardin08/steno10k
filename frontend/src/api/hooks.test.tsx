import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { ReactNode } from "react";
import { makeQueryClient } from "../app/queryClient";
import * as client from "./client";
import { useProjects } from "./hooks";

afterEach(() => vi.restoreAllMocks());

function wrap(ui: ReactNode) {
  return <QueryClientProvider client={makeQueryClient()}>{ui}</QueryClientProvider>;
}

function Probe() {
  const q = useProjects();
  return <div>{q.isLoading ? "loading" : q.data?.map((p) => p.title).join(",")}</div>;
}

test("useProjects fetches and returns projects", async () => {
  vi.spyOn(client, "request").mockResolvedValue([
    { id: "1", slug: "con-law", title: "Con Law", sets: [] },
  ]);
  render(wrap(<Probe />));
  await waitFor(() => expect(screen.getByText("Con Law")).toBeInTheDocument());
  expect(client.request).toHaveBeenCalledWith("/projects");
});
