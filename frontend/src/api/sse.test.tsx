import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, act } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import type { ReactNode } from "react";
import { makeQueryClient } from "../app/queryClient";
import {
  FakeEventSource,
  installFakeEventSource,
} from "../test/fakeEventSource";
import { useRunEvents } from "./sse";

afterEach(() => FakeEventSource.reset());

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={makeQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

test("reduces stage events into per-stage state", () => {
  installFakeEventSource();
  const { result } = renderHook(() => useRunEvents("run-1"), { wrapper });
  const es = FakeEventSource.instances[0];

  act(() => es.emit("stage_started", { stage: "transcribe" }));
  act(() => es.emit("stage_progress", { stage: "transcribe", progress: 0.5 }));
  expect(result.current.stages.transcribe).toEqual({
    status: "running",
    progress: 0.5,
  });

  act(() => es.emit("stage_completed", { stage: "transcribe" }));
  expect(result.current.stages.transcribe.status).toBe("done");
});

test("closes the source on a terminal event", () => {
  installFakeEventSource();
  const { result } = renderHook(() => useRunEvents("run-1"), { wrapper });
  const es = FakeEventSource.instances[0];
  act(() => es.emit("run_completed", {}));
  expect(result.current.status).toBe("completed");
  expect(es.closed).toBe(true);
});

test("ignores native transport-error events (auto-reconnect, not terminal)", () => {
  installFakeEventSource();
  const { result } = renderHook(() => useRunEvents("run-1"), { wrapper });
  const es = FakeEventSource.instances[0];
  expect(() => act(() => es.emitNativeError())).not.toThrow();
  expect(result.current.status).toBe("queued");
  expect(result.current.terminal).toBe(false);
  expect(es.closed).toBe(false);
});

test("treats a backend error event with data as terminal", () => {
  installFakeEventSource();
  const { result } = renderHook(() => useRunEvents("run-1"), { wrapper });
  const es = FakeEventSource.instances[0];
  act(() => es.emit("error", { message: "boom" }));
  expect(result.current.status).toBe("failed");
  expect(result.current.terminal).toBe(true);
  expect(es.closed).toBe(true);
});

test("no-op when runId is null", () => {
  installFakeEventSource();
  renderHook(() => useRunEvents(null), { wrapper });
  expect(FakeEventSource.instances.length).toBe(0);
});
