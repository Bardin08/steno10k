import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiUrl, postForm, request, requestText } from "./client";
import { keys } from "./keys";
import type {
  ArtifactDTO, ProjectDTO, RecordingDTO, RunDTO, SetDTO, SystemInfoDTO,
} from "./types";

// ---- Queries ----
export function useProjects() {
  return useQuery({ queryKey: keys.projects(), queryFn: () => request<ProjectDTO[]>("/projects") });
}
export function useSet(project: string, set: string) {
  return useQuery({
    queryKey: keys.set(project, set),
    queryFn: () => request<SetDTO>(`/projects/${project}/sets/${set}`),
    enabled: Boolean(project && set),
  });
}
export function useRecordings(project: string, set: string) {
  return useQuery({
    queryKey: keys.recordings(project, set),
    queryFn: () => request<RecordingDTO[]>(`/projects/${project}/sets/${set}/recordings`),
    enabled: Boolean(project && set),
  });
}
export function useArtifacts(project: string, set: string) {
  return useQuery({
    queryKey: keys.artifacts(project, set),
    queryFn: () => request<ArtifactDTO[]>(`/projects/${project}/sets/${set}/artifacts`),
    enabled: Boolean(project && set),
  });
}
export function useRuns() {
  return useQuery({ queryKey: keys.runs(), queryFn: () => request<RunDTO[]>("/runs") });
}
export function useSystem() {
  return useQuery({ queryKey: keys.system(), queryFn: () => request<SystemInfoDTO>("/system") });
}

// ---- Project / set mutations ----
export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title: string) =>
      request<ProjectDTO>("/projects", { method: "POST", body: JSON.stringify({ title }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.projects() }),
  });
}
export function useCreateSet(project: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title: string) =>
      request<SetDTO>(`/projects/${project}/sets`, { method: "POST", body: JSON.stringify({ title }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.projects() }),
  });
}

// ---- Recordings mutations ----
export function useUploadRecordings(project: string, set: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      return postForm<RecordingDTO[]>(`/projects/${project}/sets/${set}/recordings`, form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.recordings(project, set) });
      qc.invalidateQueries({ queryKey: keys.set(project, set) });
    },
  });
}
export function useDeleteRecording(project: string, set: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      request<null>(`/projects/${project}/sets/${set}/recordings/${encodeURIComponent(name)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.recordings(project, set) });
      qc.invalidateQueries({ queryKey: keys.set(project, set) });
    },
  });
}

// ---- Runs mutations ----
export function useEnqueueRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { project: string; set: string }) =>
      request<RunDTO>("/runs", { method: "POST", body: JSON.stringify(v) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.runs() }),
  });
}
export function useCancelRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => request<{ cancelled: boolean }>(`/runs/${runId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.runs() }),
  });
}

// ---- Config mutations/queries ----
export function useConfig() {
  return useQuery({ queryKey: keys.config(), queryFn: () => request<Record<string, unknown>>("/config") });
}
export function usePutConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: Record<string, unknown>) =>
      request<Record<string, unknown>>("/config", { method: "PUT", body: JSON.stringify(config) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.config() }),
  });
}

// ---- Non-JSON helpers ----
export function previewArtifact(project: string, set: string, name: string) {
  return requestText(`/projects/${project}/sets/${set}/artifacts/${name}/preview`);
}
export function downloadUrl(project: string, set: string, name: string) {
  return apiUrl(`/projects/${project}/sets/${set}/artifacts/${name}/download`);
}
