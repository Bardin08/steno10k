import { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
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

const SECTIONS = [
  { key: "transcription", label: "Transcription" },
  { key: "llm", label: "LLM" },
  { key: "audio", label: "Audio & Output" },
  { key: "stages", label: "Stages" },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

const HELP: Record<SectionKey, string> = {
  transcription:
    "Pick the Whisper model used to transcribe audio. Larger models are more accurate but slower and use more memory.",
  llm: "Configure the LLM used for the clean & summarize stages. Point it at any OpenAI-compatible endpoint.",
  audio:
    "Controls how source audio is chunked before transcription, and where the generated summary and bundle files land.",
  stages:
    "Turn individual pipeline stages on or off. Disabling a stage skips it for every run.",
};

export function ConfigScreen() {
  const { data, isLoading, isError, refetch } = useConfig();
  const system = useSystem();
  const put = usePutConfig();
  const [draft, setDraft] = useState<Cfg | null>(null);
  const [section, setSection] = useState<SectionKey>("transcription");

  useEffect(() => {
    if (data) setDraft(structuredClone(data) as Cfg);
  }, [data]);

  if (isLoading || !draft) return <Skeleton className="h-64 w-full" />;
  if (isError)
    return (
      <ErrorState message="Couldn't load config." onRetry={() => refetch()} />
    );

  const sectionValue = (name: string) =>
    (draft[name] ?? {}) as Record<string, unknown>;
  function patch(sectionName: string, key: string, value: unknown) {
    setDraft((d) => ({
      ...d!,
      [sectionName]: { ...(d![sectionName] ?? {}), [key]: value },
    }));
  }
  const stagesEnabled = (sectionValue("stages").enabled ?? {}) as Record<
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

  const tr = sectionValue("transcription");
  const llm = sectionValue("llm");
  const audio = sectionValue("audio");
  const output = sectionValue("output");
  const models = system.data?.whisper_models ?? [String(tr.model ?? "")];

  return (
    <section className="flex max-w-[960px] flex-col gap-8">
      <header>
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
          Settings
        </p>
        <h1 className="text-4xl text-ink">Config</h1>
      </header>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-[auto_2fr_1fr]">
        <aside className="order-2 md:order-1">
          <ul className="flex gap-1 overflow-x-auto md:flex-col md:overflow-visible">
            {SECTIONS.map((s) => (
              <li key={s.key}>
                <button
                  type="button"
                  aria-current={section === s.key}
                  onClick={() => setSection(s.key)}
                  className={`block whitespace-nowrap rounded-sm px-3 py-1.5 text-left text-sm font-medium transition-colors duration-[var(--dur-micro)] ease-editorial ${
                    section === s.key
                      ? "bg-ink text-paper"
                      : "text-ink-soft hover:text-ink"
                  }`}
                >
                  {s.label}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <div
          role="region"
          aria-label={`${SECTIONS.find((s) => s.key === section)?.label} help`}
          className="order-1 flex flex-col gap-2 rounded-md border border-hairline bg-surface p-4 md:order-3"
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
            Help
          </p>
          <p className="text-sm text-ink-soft">{HELP[section]}</p>
        </div>

        <div className="order-3 md:order-2">
          {section === "transcription" && (
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
                onChange={(e) =>
                  patch("transcription", "device", e.target.value)
                }
              />
              <Input
                label="Compute type"
                value={String(tr.compute_type ?? "")}
                onChange={(e) =>
                  patch("transcription", "compute_type", e.target.value)
                }
              />
            </div>
          )}

          {section === "llm" && (
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
          )}

          {section === "audio" && (
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
          )}

          {section === "stages" && (
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
          )}
        </div>
      </div>

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
