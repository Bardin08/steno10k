import { type ReactNode } from "react";
import { cn } from "../lib/cn";

export type Status = "run" | "done" | "queued";

const styles: Record<Status, string> = {
  run: "bg-accent-wash text-accent-ink",
  done: "bg-sink text-ink-soft",
  queued: "border border-hairline-strong text-ink-faint",
};

export function StatusPill({
  status,
  children,
}: {
  status: Status;
  children: ReactNode;
}) {
  return (
    <span
      data-status={status}
      className={cn(
        "rounded-pill px-2.5 py-1 font-mono text-[10.5px] font-medium uppercase tracking-[0.06em]",
        styles[status],
      )}
    >
      {children}
    </span>
  );
}
