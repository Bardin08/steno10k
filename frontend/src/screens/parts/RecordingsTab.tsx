import { WaveSine } from "@phosphor-icons/react";
import { EmptyState, ErrorState, Skeleton, toast } from "../../components";
import { ApiError } from "../../api/client";
import { useDeleteRecording, useRecordings, useUploadRecordings } from "../../api/hooks";
import { UploadZone } from "./UploadZone";
import { RecordingList } from "./RecordingList";

export function RecordingsTab({ project, set }: { project: string; set: string }) {
  const { data, isLoading, isError, refetch } = useRecordings(project, set);
  const upload = useUploadRecordings(project, set);
  const del = useDeleteRecording(project, set);

  const onError = (e: unknown) => toast.error(e instanceof ApiError ? e.message : "Upload failed");

  return (
    <div className="flex flex-col gap-6">
      <UploadZone
        disabled={upload.isPending}
        onFiles={(files) => upload.mutate(files, { onError })}
      />
      {isLoading && <Skeleton className="h-24 w-full" />}
      {isError && <ErrorState message="Couldn't load recordings." onRetry={() => refetch()} />}
      {data && data.length === 0 && (
        <EmptyState title="No recordings yet" description="Drop audio above to start the pipeline." icon={<WaveSine size={24} weight="duotone" />} />
      )}
      {data && data.length > 0 && (
        <RecordingList recordings={data} onDelete={(name) => del.mutate(name, { onError })} />
      )}
    </div>
  );
}
