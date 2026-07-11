import { useState } from "react";
import { DownloadSimple, FileText } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { Card, ErrorState, Skeleton } from "../../components";
import { downloadUrl, previewArtifact, useArtifacts } from "../../api/hooks";
import { MarkdownView } from "./MarkdownView";
import type { ArtifactDTO } from "../../api/types";

function PendingSkeletons() {
  // Placeholders for the artifacts a completed run will produce.
  return (
    <div className="flex flex-col gap-3">
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">Awaiting outputs</p>
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
    </div>
  );
}

function Preview({ project, set, artifact }: { project: string; set: string; artifact: ArtifactDTO }) {
  const q = useQuery({
    queryKey: ["preview", project, set, artifact.name],
    queryFn: () => previewArtifact(project, set, artifact.name),
  });
  if (q.isLoading) return <Skeleton className="h-40 w-full" />;
  if (q.isError || q.data == null) return <ErrorState message="Couldn't load preview." onRetry={() => q.refetch()} />;
  return <MarkdownView source={q.data} />;
}

export function ArtifactsTab({ project, set }: { project: string; set: string }) {
  const { data, isLoading, isError, refetch } = useArtifacts(project, set);
  const [selected, setSelected] = useState<ArtifactDTO | null>(null);

  if (isLoading) return <Skeleton className="h-24 w-full" />;
  if (isError) return <ErrorState message="Couldn't load artifacts." onRetry={() => refetch()} />;
  if (data && data.length === 0) return <PendingSkeletons />;

  return (
    <div className="grid grid-cols-[minmax(0,340px)_1fr] gap-6">
      <ul className="flex flex-col gap-2">
        {data?.map((a) => (
          <li key={a.name} className="flex items-center gap-2 rounded-sm border border-hairline bg-paper px-3 py-2.5">
            <FileText size={16} className="text-ink-faint" />
            <button
              className="min-w-0 flex-1 truncate text-left text-sm text-ink hover:text-accent-ink disabled:text-ink-faint"
              disabled={a.kind !== "text"}
              onClick={() => setSelected(a)}
            >
              {a.name}
            </button>
            <a href={downloadUrl(project, set, a.name)} aria-label={`Download ${a.name}`} className="text-ink-faint hover:text-ink">
              <DownloadSimple size={16} />
            </a>
          </li>
        ))}
      </ul>
      <Card className="p-6">
        {selected ? <Preview project={project} set={set} artifact={selected} /> : (
          <p className="text-sm text-ink-soft">Select a text artifact to preview.</p>
        )}
      </Card>
    </div>
  );
}
