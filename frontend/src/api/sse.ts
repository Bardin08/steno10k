import { useEffect, useReducer } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiUrl } from "./client";
import { keys } from "./keys";
import { STAGE_NAMES, type RunStatus, type StageName } from "./types";

type StageStatus = "queued" | "running" | "done" | "failed" | "skipped";
export interface RunEvent {
  kind: string;
  payload: Record<string, unknown>;
}
export interface RunView {
  status: RunStatus;
  stages: Record<StageName, { status: StageStatus; progress?: number }>;
  log: RunEvent[];
  terminal: boolean;
}

const TERMINAL = new Set(["run_completed", "error"]);

function initialStages(): RunView["stages"] {
  return Object.fromEntries(
    STAGE_NAMES.map((s) => [s, { status: "queued" }]),
  ) as RunView["stages"];
}

function reduce(state: RunView, ev: RunEvent): RunView {
  const stage = ev.payload.stage as StageName | undefined;
  const progress =
    typeof ev.payload.progress === "number" ? ev.payload.progress : undefined;
  const next: RunView = {
    ...state,
    log: [...state.log, ev],
    stages: { ...state.stages },
  };

  switch (ev.kind) {
    case "run_started":
      next.status = "running";
      break;
    case "stage_started":
      if (stage) next.stages[stage] = { status: "running" };
      break;
    case "stage_progress":
      if (stage) next.stages[stage] = { status: "running", progress };
      break;
    case "stage_completed":
      if (stage) next.stages[stage] = { status: "done" };
      break;
    case "stage_skipped":
      if (stage) next.stages[stage] = { status: "skipped" };
      break;
    case "stage_failed":
      if (stage) next.stages[stage] = { status: "failed" };
      next.status = "failed";
      break;
    case "run_completed":
      next.status = "completed";
      next.terminal = true;
      break;
    case "error":
      next.status = "failed";
      next.terminal = true;
      break;
  }
  return next;
}

const EVENT_KINDS = [
  "run_started",
  "stage_started",
  "stage_progress",
  "stage_completed",
  "stage_skipped",
  "stage_failed",
  "run_completed",
  "error",
] as const;

export function useRunEvents(
  runId: string | null,
  project?: string,
  set?: string,
): RunView {
  const qc = useQueryClient();
  const [view, dispatch] = useReducer(reduce, null, () => ({
    status: "queued" as RunStatus,
    stages: initialStages(),
    log: [],
    terminal: false,
  }));

  useEffect(() => {
    if (!runId) return;
    const es = new EventSource(apiUrl(`/runs/${runId}/events`));
    const makeHandler =
      (kind: (typeof EVENT_KINDS)[number]) => (ev: MessageEvent) => {
        // Native transport-error events (connection drop/reconnect) have no data —
        // let EventSource auto-reconnect; don't treat as an app-level terminal.
        if (typeof ev.data !== "string") return;
        let payload: Record<string, unknown>;
        try {
          payload = JSON.parse(ev.data) as Record<string, unknown>;
        } catch {
          return; // ignore malformed frame
        }
        dispatch({ kind, payload });
        if (TERMINAL.has(kind)) {
          es.close();
          void qc.invalidateQueries({ queryKey: keys.runs() });
          if (project && set)
            void qc.invalidateQueries({
              queryKey: keys.artifacts(project, set),
            });
        }
      };
    EVENT_KINDS.forEach((kind) =>
      es.addEventListener(kind, makeHandler(kind) as EventListener),
    );
    return () => es.close();
  }, [runId, project, set, qc]);

  return view;
}
