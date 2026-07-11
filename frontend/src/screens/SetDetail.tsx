import { useParams, useSearchParams } from "react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components";
import { ErrorState, Skeleton } from "../components";
import { useSet } from "../api/hooks";
import { RecordingsTab } from "./parts/RecordingsTab";
import { RunTab } from "./parts/RunTab";
import { ArtifactsTab } from "./parts/ArtifactsTab";

const TABS = ["recordings", "run", "artifacts"] as const;
type TabKey = (typeof TABS)[number];

export function SetDetail() {
  const { project = "", set = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const raw = params.get("tab");
  const tab: TabKey = (TABS as readonly string[]).includes(raw ?? "") ? (raw as TabKey) : "recordings";
  const { data, isLoading, isError, refetch } = useSet(project, set);

  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (isError || !data) return <ErrorState message="Couldn't load this set." onRetry={() => refetch()} />;

  return (
    <section>
      <header className="mb-8">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          {data.project_slug}
        </p>
        <h1 className="text-4xl text-ink">{data.title}</h1>
      </header>

      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList>
          <TabsTrigger value="recordings">Recordings</TabsTrigger>
          <TabsTrigger value="run">Run</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
        </TabsList>
        <TabsContent value="recordings"><RecordingsTab project={project} set={set} /></TabsContent>
        <TabsContent value="run"><RunTab project={project} set={set} /></TabsContent>
        <TabsContent value="artifacts"><ArtifactsTab project={project} set={set} /></TabsContent>
      </Tabs>
    </section>
  );
}
