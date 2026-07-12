import { useState } from "react";
import { WaveSine } from "@phosphor-icons/react";
import { EmptyState, ErrorState, Skeleton, toast } from "../../components";
import { ApiError } from "../../api/client";
import {
  useCancelRun,
  useConfig,
  useDeleteRecording,
  useEnqueueRun,
  useRecordings,
  useRuns,
  useUploadRecordings,
} from "../../api/hooks";
import { STAGE_NAMES } from "../../api/types";
import { UploadZone } from "./UploadZone";
import { RecordingList } from "./RecordingList";
import { SplitButton } from "./SplitButton";
import { RunSettingsModal } from "./RunSettingsModal";
import { PipelinePanel } from "./PipelinePanel";

export function RecordingsTab({
  project,
  set,
}: {
  project: string;
  set: string;
}) {
  const { data, isLoading, isError, refetch } = useRecordings(project, set);
  const upload = useUploadRecordings(project, set);
  const del = useDeleteRecording(project, set);
  const enqueue = useEnqueueRun();
  const cancel = useCancelRun();
  const { data: runs } = useRuns();
  const { data: config } = useConfig();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Runs list is insertion order (oldest first); the last match for this set is the newest.
  const latest = runs
    ?.filter((r) => r.project === project && r.set_ === set)
    .at(-1);
  const runId = activeId ?? latest?.id ?? null;

  const stagesEnabled =
    ((config?.stages as Record<string, unknown> | undefined)?.enabled as
      Record<string, boolean> | undefined) ?? {};
  const enabledStages = STAGE_NAMES.filter((s) => stagesEnabled[s] !== false);

  const onError = (e: unknown) =>
    toast.error(e instanceof ApiError ? e.message : "Upload failed");

  function runEnqueue(opts?: { force?: boolean }) {
    enqueue.mutate(
      { project, set, ...opts },
      {
        onSuccess: (run) => {
          setActiveId(run.id);
          toast.success("Run queued");
        },
        onError: (e) =>
          toast.error(e instanceof ApiError ? e.message : "Couldn't start run"),
      },
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <UploadZone
        disabled={upload.isPending}
        onFiles={(files) => upload.mutate(files, { onError })}
      />

      <div className="flex items-center gap-4">
        <SplitButton
          label="Transcribe"
          disabled={enqueue.isPending}
          onPrimary={() => runEnqueue()}
          onGear={() => setSettingsOpen(true)}
        />
        <span className="font-mono text-[11px] text-ink-faint">
          Runs {enabledStages.length} configured stage
          {enabledStages.length === 1 ? "" : "s"}.
        </span>
      </div>

      {isLoading && <Skeleton className="h-24 w-full" />}
      {isError && (
        <ErrorState
          message="Couldn't load recordings."
          onRetry={() => refetch()}
        />
      )}
      {data && data.length === 0 && (
        <EmptyState
          title="No recordings yet"
          description="Drop audio above to start the pipeline."
          icon={<WaveSine size={24} weight="duotone" />}
        />
      )}
      {data && data.length > 0 && (
        <RecordingList
          recordings={data}
          onDelete={(name) => del.mutate(name, { onError })}
        />
      )}

      <PipelinePanel
        project={project}
        set={set}
        runId={runId}
        onCancel={() =>
          runId &&
          cancel.mutate(runId, {
            onError: (e) =>
              toast.error(e instanceof ApiError ? e.message : "Cancel failed"),
          })
        }
      />

      <RunSettingsModal
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        enabledStages={enabledStages}
        onConfirm={({ force }) => {
          setSettingsOpen(false);
          runEnqueue({ force });
        }}
      />
    </div>
  );
}
