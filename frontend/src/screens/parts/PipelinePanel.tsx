import { STAGE_NAMES } from "../../api/types";
import { useRunEvents } from "../../api/sse";
import { RunMonitor } from "./RunMonitor";

export interface PipelinePanelProps {
  project: string;
  set: string;
  runId: string | null;
  onCancel: () => void;
}

export function PipelinePanel({
  project,
  set,
  runId,
  onCancel,
}: PipelinePanelProps) {
  // Hooks must run unconditionally; useRunEvents itself no-ops until runId
  // is set, so it's safe to call before the runId != null branch below.
  const view = useRunEvents(runId, project, set);

  if (runId == null) {
    return (
      <div className="flex flex-col gap-4">
        <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          Pipeline · idle
        </span>
        <ol className="flex flex-col gap-1.5">
          {STAGE_NAMES.map((name) => (
            <li
              key={name}
              className="rounded-sm border border-dashed border-hairline px-3 py-2 text-sm text-ink-faint"
            >
              {name}
            </li>
          ))}
        </ol>
      </div>
    );
  }

  return <RunMonitor view={view} onCancel={onCancel} />;
}
