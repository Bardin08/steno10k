import { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
  ErrorState,
  Input,
  Select,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
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
  const [tab, setTab] = useState("transcription");

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
  const models = system.data?.whisper_models ?? [String(tr.model ?? "")];

  return (
    <section className="flex max-w-[640px] flex-col gap-8">
      <header>
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          Settings
        </p>
        <h1 className="text-4xl text-ink">Config</h1>
      </header>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="transcription">Transcription</TabsTrigger>
          <TabsTrigger value="llm">LLM</TabsTrigger>
          <TabsTrigger value="audio">Audio &amp; Output</TabsTrigger>
          <TabsTrigger value="stages">Stages</TabsTrigger>
        </TabsList>

        <TabsContent value="transcription">
          <div className="flex flex-col gap-4">
            <Select
              label="Whisper model"
              value={String(tr.model ?? "")}
              onValueChange={(v) => patch("transcription", "model", v)}
              options={models.map((m) => ({ value: m }))}
            />
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
          </div>
        </TabsContent>

        <TabsContent value="llm">
          <div className="flex flex-col gap-4">
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
            <Checkbox
              label="Enabled"
              checked={Boolean(llm.enabled)}
              onChange={(e) => patch("llm", "enabled", e.target.checked)}
            />
          </div>
        </TabsContent>

        <TabsContent value="audio">
          <div className="flex flex-col gap-4">
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
              onChange={(e) =>
                patch("output", "summary_filename", e.target.value)
              }
            />
            <Checkbox
              label="Save bundle .docx"
              checked={Boolean(output.save_bundle_docx)}
              onChange={(e) =>
                patch("output", "save_bundle_docx", e.target.checked)
              }
            />
          </div>
        </TabsContent>

        <TabsContent value="stages">
          <div className="grid grid-cols-2 gap-3">
            {STAGE_NAMES.map((s) => (
              <Checkbox
                key={s}
                label={s}
                checked={stagesEnabled[s] !== false}
                onChange={(e) => toggleStage(s, e.target.checked)}
              />
            ))}
          </div>
        </TabsContent>
      </Tabs>

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
