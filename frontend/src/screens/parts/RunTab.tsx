import { useState } from "react";
import { Button, toast } from "../../components";
import { ApiError } from "../../api/client";
import { useCancelRun, useEnqueueRun, useRuns } from "../../api/hooks";
import { useRunEvents } from "../../api/sse";
import { RunMonitor } from "./RunMonitor";

export function RunTab({ project, set }: { project: string; set: string }) {
  const enqueue = useEnqueueRun();
  const cancel = useCancelRun();
  const { data: runs } = useRuns();
  const [activeId, setActiveId] = useState<string | null>(null);

  // Runs list is insertion order (oldest first); the last match for this set is the newest.
  const latest = runs?.filter((r) => r.project === project && r.set_ === set).at(-1);
  const runId = activeId ?? latest?.id ?? null;
  const view = useRunEvents(runId, project, set);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center gap-4">
        <Button
          disabled={enqueue.isPending}
          onClick={() =>
            enqueue.mutate(
              { project, set },
              {
                onSuccess: (run) => { setActiveId(run.id); toast.success("Run queued"); },
                onError: (e) => toast.error(e instanceof ApiError ? e.message : "Couldn't start run"),
              },
            )
          }
        >
          Run set
        </Button>
        <span className="font-mono text-[11px] text-ink-faint">
          Which stages run is configured globally in Config.
        </span>
      </div>

      {runId && (
        <RunMonitor
          view={view}
          onCancel={() =>
            cancel.mutate(runId, {
              onError: (e) => toast.error(e instanceof ApiError ? e.message : "Cancel failed"),
            })
          }
        />
      )}
    </div>
  );
}
