export const STAGE_NAMES = [
  "normalize",
  "chunk",
  "transcribe",
  "clean",
  "merge",
  "summarize",
  "bundle",
  "notify",
] as const;
export type StageName = (typeof STAGE_NAMES)[number];

export type RunStatus =
  "queued" | "running" | "completed" | "failed" | "cancelled";

export interface RecordingDTO {
  source_name: string;
  normalized_name: string;
  duration_seconds: number | null;
  chunks: string[];
}
export interface SetDTO {
  id: string;
  slug: string;
  title: string;
  project_slug: string;
  recordings: RecordingDTO[];
  stages: Record<string, string>;
}
export interface ProjectDTO {
  id: string;
  slug: string;
  title: string;
  sets: SetDTO[];
}
export interface RunDTO {
  id: string;
  project: string;
  set_: string;
  status: RunStatus;
  position: number;
  stats: Record<string, unknown>;
}
export interface ArtifactDTO {
  name: string;
  kind: "text" | "docx" | "binary";
  size: number;
  stage: string | null;
}
export interface SystemInfoDTO {
  whisper_models: string[];
  current_model: string;
  max_workers: number;
  data_root: string;
}
