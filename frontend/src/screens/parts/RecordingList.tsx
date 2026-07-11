import { Trash } from "@phosphor-icons/react";
import type { RecordingDTO } from "../../api/types";

function fmtDuration(sec: number | null): string {
  if (sec == null) return "—";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

export function RecordingList({
  recordings, onDelete,
}: { recordings: RecordingDTO[]; onDelete: (name: string) => void }) {
  return (
    <ul className="flex flex-col gap-2">
      {recordings.map((r) => (
        <li key={r.normalized_name} className="flex items-center gap-3 rounded-sm border border-hairline bg-paper px-3 py-2.5">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-ink">{r.source_name}</div>
            <div className="truncate font-mono text-[11px] text-ink-faint">
              {fmtDuration(r.duration_seconds)} · {r.chunks.length} chunks
            </div>
          </div>
          <button
            aria-label={`Delete ${r.source_name}`}
            className="text-ink-faint hover:text-accent-ink"
            onClick={() => onDelete(r.normalized_name)}
          >
            <Trash size={16} />
          </button>
        </li>
      ))}
    </ul>
  );
}
