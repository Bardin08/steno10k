import { QueryClientProvider } from "@tanstack/react-query";
import { render, renderHook, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";
import type { ReactNode } from "react";
import { makeQueryClient } from "../app/queryClient";
import * as client from "./client";
import {
  useCreateProject,
  useDeleteProject,
  useDeleteSet,
  useEnqueueRun,
  useProjects,
} from "./hooks";

afterEach(() => vi.restoreAllMocks());

function wrap(ui: ReactNode) {
  return (
    <QueryClientProvider client={makeQueryClient()}>{ui}</QueryClientProvider>
  );
}

function Probe() {
  const q = useProjects();
  return (
    <div>{q.isLoading ? "loading" : q.data?.map((p) => p.title).join(",")}</div>
  );
}

test("useProjects fetches and returns projects", async () => {
  vi.spyOn(client, "request").mockResolvedValue([
    { id: "1", slug: "con-law", title: "Con Law", sets: [] },
  ]);
  render(wrap(<Probe />));
  await waitFor(() => expect(screen.getByText("Con Law")).toBeInTheDocument());
  expect(client.request).toHaveBeenCalledWith("/projects");
});

test("useDeleteProject DELETEs the project and invalidates the projects list", async () => {
  vi.spyOn(client, "request").mockResolvedValue(null);
  const qc = makeQueryClient();
  const invalidateSpy = vi.spyOn(qc, "invalidateQueries");
  const { result } = renderHook(() => useDeleteProject(), {
    wrapper: ({ children }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    ),
  });
  await act(async () => {
    await result.current.mutateAsync("con-law");
  });
  expect(client.request).toHaveBeenCalledWith("/projects/con-law", {
    method: "DELETE",
  });
  expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["projects"] });
});

test("useDeleteSet DELETEs the set and invalidates the projects list", async () => {
  vi.spyOn(client, "request").mockResolvedValue(null);
  const qc = makeQueryClient();
  const invalidateSpy = vi.spyOn(qc, "invalidateQueries");
  const { result } = renderHook(() => useDeleteSet("con-law"), {
    wrapper: ({ children }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    ),
  });
  await act(async () => {
    await result.current.mutateAsync("week-1");
  });
  expect(client.request).toHaveBeenCalledWith(
    "/projects/con-law/sets/week-1",
    { method: "DELETE" },
  );
  expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["projects"] });
});

test("useEnqueueRun posts a body containing force:true", async () => {
  vi.spyOn(client, "request").mockResolvedValue({
    id: "r1",
    project: "con-law",
    set_: "week-1",
    status: "queued",
    position: 0,
    stats: {},
  });
  const { result } = renderHook(() => useEnqueueRun(), {
    wrapper: ({ children }) => wrap(children),
  });
  await act(async () => {
    await result.current.mutateAsync({
      project: "con-law",
      set: "week-1",
      force: true,
    });
  });
  expect(client.request).toHaveBeenCalledWith("/runs", {
    method: "POST",
    body: JSON.stringify({ project: "con-law", set: "week-1", force: true }),
  });
});

test("useCreateProject posts title + icon", async () => {
  vi.spyOn(client, "request").mockResolvedValue({
    id: "1",
    slug: "con-law",
    title: "Con Law",
    icon: "book",
    sets: [],
  });
  const { result } = renderHook(() => useCreateProject(), {
    wrapper: ({ children }) => wrap(children),
  });
  await act(async () => {
    await result.current.mutateAsync({ title: "Con Law", icon: "book" });
  });
  expect(client.request).toHaveBeenCalledWith("/projects", {
    method: "POST",
    body: JSON.stringify({ title: "Con Law", icon: "book" }),
  });
});
