import { WaveSine } from "@phosphor-icons/react";
import {
  Card,
  EmptyState,
  ErrorState,
  ProgressBar,
  QueueRow,
  Skeleton,
  type Status,
} from "../components";
import { useReducedMotion } from "../theme/useReducedMotion";

export interface QueueItem {
  id: string;
  title: string;
  sub: string;
  status: Status;
  statusLabel: string;
  progress?: number;
}

export type QueueState = "loading" | "empty" | "error" | "ready";

export interface QueueMonitorProps {
  state: QueueState;
  items: QueueItem[];
  onRetry?: () => void;
}

export function QueueMonitor({ state, items, onRetry }: QueueMonitorProps) {
  const reduced = useReducedMotion();
  const reveal = reduced ? {} : { "data-reveal": true };

  return (
    <main className="mx-auto max-w-[var(--maxw)] px-8 py-16">
      <header className="mb-10" {...reveal}>
        <p className="mb-3 inline-flex items-center gap-2 font-mono text-[11.5px] font-medium uppercase tracking-[0.14em] text-ink-faint">
          Pipeline · monitor
        </p>
        <h1 className="text-5xl leading-[0.98] text-ink">
          The machine keeps the{" "}
          <em className="not-italic text-accent-ink italic">record</em>.
        </h1>
      </header>

      <Card className="p-4">
        {state === "loading" && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        )}

        {state === "empty" && (
          <EmptyState
            title="No recordings yet"
            description="Drop audio into a set to start the pipeline."
            icon={<WaveSine size={28} weight="duotone" />}
          />
        )}

        {state === "error" && (
          <ErrorState message="Couldn't load the queue." onRetry={onRetry} />
        )}

        {state === "ready" && (
          <div className="flex flex-col gap-3">
            {items.map((item) => (
              <div key={item.id} className="flex flex-col gap-2">
                <QueueRow
                  title={item.title}
                  sub={item.sub}
                  status={item.status}
                  statusLabel={item.statusLabel}
                  icon={<WaveSine size={15} />}
                />
                {item.progress !== undefined && (
                  <ProgressBar value={item.progress} />
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </main>
  );
}
