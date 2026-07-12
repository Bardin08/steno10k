import { useState } from "react";
import { CaretRight } from "@phosphor-icons/react";
import { Button, ProgressBar } from "../../components";
import { STAGE_NAMES } from "../../api/types";
import type { RunView } from "../../api/sse";

// Single-accent palette (no success/error tokens exist); map each status to a
// mutually-distinct existing token.
const DOT: Record<string, string> = {
  queued: "bg-sink", // faint
  running: "bg-accent", // green = the only live color
  done: "bg-ink-faint", // muted grey = settled
  skipped: "bg-sink", // faint = never ran
  failed: "bg-ink", // stark = draws the eye
};

export function RunMonitor({
  view,
  onCancel,
}: {
  view: RunView;
  onCancel: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          {view.status}
        </span>
        {!view.terminal && (
          <Button
            variant="ghost"
            className="px-3 py-1 text-xs"
            onClick={onCancel}
          >
            Cancel
          </Button>
        )}
      </div>

      <ol className="flex flex-col gap-1.5">
        {STAGE_NAMES.map((name) => {
          const st = view.stages[name];
          return (
            <li
              key={name}
              className="rounded-sm border border-hairline bg-paper px-3 py-2"
            >
              <div className="flex items-center gap-2.5">
                <span className={`h-2 w-2 rounded-full ${DOT[st.status]}`} />
                <span className="flex-1 text-sm text-ink">{name}</span>
                <span className="font-mono text-[11px] text-ink-faint">
                  {st.status}
                </span>
              </div>
              {st.status === "running" && st.progress != null && (
                <div className="mt-2">
                  <ProgressBar value={Math.round(st.progress * 100)} />
                </div>
              )}
            </li>
          );
        })}
      </ol>

      <div>
        <button
          className="flex items-center gap-1 font-mono text-[11px] text-ink-faint hover:text-ink"
          onClick={() => setOpen((o) => !o)}
        >
          <CaretRight size={12} className={open ? "rotate-90" : ""} /> event log
          ({view.log.length})
        </button>
        {open && (
          <pre className="mt-2 max-h-56 overflow-auto rounded-sm bg-ink p-3 font-mono text-[11px] leading-6 text-paper">
            {view.log
              .map((e) => `${e.kind} ${JSON.stringify(e.payload)}`)
              .join("\n")}
          </pre>
        )}
      </div>
    </div>
  );
}
