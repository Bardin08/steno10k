import { useEffect } from "react";
import { useParams, useSearchParams } from "react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components";
import { ErrorState, Skeleton } from "../components";
import { useSet } from "../api/hooks";
import { RecordingsTab } from "./parts/RecordingsTab";
import { ArtifactsTab } from "./parts/ArtifactsTab";

const TABS = ["recordings", "artifacts"] as const;
type TabKey = (typeof TABS)[number];

export function SetDetail() {
  const { project = "", set = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const raw = params.get("tab");
  const tab: TabKey = (TABS as readonly string[]).includes(raw ?? "")
    ? (raw as TabKey)
    : "recordings";

  // Legacy `?tab=run` links (the Run tab was folded into Recordings) —
  // normalize the URL rather than silently rendering Recordings under a
  // stale query string.
  useEffect(() => {
    if (raw === "run") setParams({ tab: "recordings" }, { replace: true });
  }, [raw, setParams]);

  const { data, isLoading, isError, refetch } = useSet(project, set);

  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (isError || !data)
    return (
      <ErrorState message="Couldn't load this set." onRetry={() => refetch()} />
    );

  return (
    <section>
      <header className="mb-8">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          {data.project_slug}
        </p>
        <h1 className="text-4xl text-ink">{data.title}</h1>
      </header>

      <Tabs
        value={tab}
        onValueChange={(v) => setParams({ tab: v }, { replace: true })}
      >
        <TabsList>
          <TabsTrigger value="recordings">Recordings</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
        </TabsList>
        <TabsContent value="recordings">
          <RecordingsTab
            key={`${project}/${set}`}
            project={project}
            set={set}
          />
        </TabsContent>
        <TabsContent value="artifacts">
          <ArtifactsTab key={`${project}/${set}`} project={project} set={set} />
        </TabsContent>
      </Tabs>
    </section>
  );
}
