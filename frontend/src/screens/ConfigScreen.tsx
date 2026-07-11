import { useEffect, useState } from "react";
import {
  Button,
  ErrorState,
  Input,
  Select,
  Skeleton,
  toast,
} from "../components";
import { ApiError } from "../api/client";
import { useConfig, usePutConfig, useSystem } from "../api/hooks";
import { STAGE_NAMES } from "../api/types";

type Cfg = Record<string, Record<string, unknown>>;

export function ConfigScreen() {
  const { data, isLoading, isError, refetch } = useConfig();
  const system = useSystem();
  const put = usePutConfig();
  const [draft, setDraft] = useState<Cfg | null>(null);

  useEffect(() => {
    if (data) setDraft(structuredClone(data) as Cfg);
  }, [data]);

  if (isLoading || !draft) return <Skeleton className="h-64 w-full" />;
  if (isError)
    return (
      <ErrorState message="Couldn't load config." onRetry={() => refetch()} />
    );

  const section = (name: string) =>
    (draft[name] ?? {}) as Record<string, unknown>;
  function patch(sectionName: string, key: string, value: unknown) {
    setDraft((d) => ({
      ...d!,
      [sectionName]: { ...(d![sectionName] ?? {}), [key]: value },
    }));
  }
  const stagesEnabled = (section("stages").enabled ?? {}) as Record<
    string,
    boolean
  >;
  function toggleStage(stage: string, on: boolean) {
    setDraft((d) => ({
      ...d!,
      stages: {
        ...(d!.stages ?? {}),
        enabled: { ...stagesEnabled, [stage]: on },
      },
    }));
  }

  const tr = section("transcription");
  const llm = section("llm");
  const audio = section("audio");
  const output = section("output");

  return (
    <section className="flex max-w-[640px] flex-col gap-10">
      <header>
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          Settings
        </p>
        <h1 className="text-4xl text-ink">Config</h1>
      </header>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 text-sm font-medium text-ink">
          Transcription
        </legend>
        <Select
          label="Whisper model"
          value={String(tr.model ?? "")}
          onChange={(e) => patch("transcription", "model", e.target.value)}
        >
          {(system.data?.whisper_models ?? [String(tr.model ?? "")]).map(
            (m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ),
          )}
        </Select>
        <Input
          label="Device"
          value={String(tr.device ?? "")}
          onChange={(e) => patch("transcription", "device", e.target.value)}
        />
        <Input
          label="Compute type"
          value={String(tr.compute_type ?? "")}
          onChange={(e) =>
            patch("transcription", "compute_type", e.target.value)
          }
        />
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 text-sm font-medium text-ink">LLM</legend>
        <Input
          label="LLM model"
          value={String(llm.model ?? "")}
          onChange={(e) => patch("llm", "model", e.target.value)}
        />
        <Input
          label="Base URL"
          value={String(llm.base_url ?? "")}
          onChange={(e) => patch("llm", "base_url", e.target.value)}
        />
        <Input
          label="API key env var"
          value={String(llm.api_key_env ?? "")}
          onChange={(e) => patch("llm", "api_key_env", e.target.value)}
        />
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={Boolean(llm.enabled)}
            onChange={(e) => patch("llm", "enabled", e.target.checked)}
          />{" "}
          Enabled
        </label>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 text-sm font-medium text-ink">
          Audio &amp; Output
        </legend>
        <Input
          label="Chunk seconds"
          type="number"
          value={String(audio.chunk_seconds ?? "")}
          onChange={(e) =>
            patch(
              "audio",
              "chunk_seconds",
              e.target.value === "" ? undefined : Number(e.target.value),
            )
          }
        />
        <Input
          label="Overlap seconds"
          type="number"
          value={String(audio.overlap_seconds ?? "")}
          onChange={(e) =>
            patch(
              "audio",
              "overlap_seconds",
              e.target.value === "" ? undefined : Number(e.target.value),
            )
          }
        />
        <Input
          label="Summary filename"
          value={String(output.summary_filename ?? "")}
          onChange={(e) => patch("output", "summary_filename", e.target.value)}
        />
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={Boolean(output.save_bundle_docx)}
            onChange={(e) =>
              patch("output", "save_bundle_docx", e.target.checked)
            }
          />{" "}
          Save bundle .docx
        </label>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium text-ink">Stages</legend>
        <div className="grid grid-cols-2 gap-2">
          {STAGE_NAMES.map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={stagesEnabled[s] !== false}
                onChange={(e) => toggleStage(s, e.target.checked)}
              />
              {s}
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <Button
          disabled={put.isPending}
          onClick={() =>
            put.mutate(draft, {
              onSuccess: () => toast.success("Config saved"),
              onError: (e) =>
                toast.error(e instanceof ApiError ? e.message : "Save failed"),
            })
          }
        >
          Save config
        </Button>
      </div>
    </section>
  );
}
