import { type ReactNode } from "react";
import { StatusPill, type Status } from "./StatusPill";

export interface QueueRowProps {
  title: string;
  sub: string;
  status: Status;
  statusLabel: string;
  icon?: ReactNode;
}

export function QueueRow({
  title,
  sub,
  status,
  statusLabel,
  icon,
}: QueueRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-sm border border-hairline bg-paper px-3 py-2.5">
      {icon && (
        <div className="grid h-8 w-8 place-items-center rounded-sm border border-hairline bg-surface text-ink-soft">
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-ink">{title}</div>
        <div className="truncate font-mono text-[11px] text-ink-faint">
          {sub}
        </div>
      </div>
      <div className="flex-1" />
      <StatusPill status={status}>{statusLabel}</StatusPill>
    </div>
  );
}
