import { Link } from "react-router";
import { WaveSine } from "@phosphor-icons/react";
import {
  Card,
  EmptyState,
  ErrorState,
  QueueRow,
  Skeleton,
  type Status,
} from "../components";
import { useProjects, useRuns } from "../api/hooks";
import type { RunStatus } from "../api/types";

const STATUS_MAP: Record<RunStatus, Status> = {
  queued: "queued",
  running: "run",
  completed: "done",
  failed: "done",
  cancelled: "done",
};

export function QueueScreen() {
  const { data: runs, isLoading, isError, refetch } = useRuns();
  const { data: projects } = useProjects();

  function titleFor(project: string, set: string): string {
    const p = projects?.find((p) => p.slug === project);
    return p?.sets.find((s) => s.slug === set)?.title ?? set;
  }

  return (
    <section>
      <header className="mb-8">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          Pipeline · queue
        </p>
        <h1 className="text-4xl text-ink">The machine keeps the record.</h1>
      </header>

      <Card className="p-4">
        {isLoading && <Skeleton className="h-14 w-full" />}
        {isError && (
          <ErrorState
            message="Couldn't load the queue."
            onRetry={() => refetch()}
          />
        )}
        {runs && runs.length === 0 && (
          <EmptyState
            title="Nothing queued"
            description="Enqueue a run from a set."
            icon={<WaveSine size={28} weight="duotone" />}
          />
        )}
        {runs && runs.length > 0 && (
          <ul className="flex flex-col gap-3">
            {runs.map((r) => (
              <li key={r.id}>
                <Link
                  to={`/p/${r.project}/s/${r.set_}?tab=run`}
                  className="block"
                >
                  <QueueRow
                    title={titleFor(r.project, r.set_)}
                    sub={`${r.status} · #${r.position}`}
                    status={STATUS_MAP[r.status]}
                    statusLabel={r.status}
                    icon={<WaveSine size={15} />}
                  />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </section>
  );
}
