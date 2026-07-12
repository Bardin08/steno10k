import { useEffect, useState } from "react";
import {
  Button,
  ErrorState,
  Input,
  Select,
  Skeleton,
  Switch,
  toast,
} from "../components";
import { ApiError } from "../api/client";
import { useConfig, usePutConfig, useSystem } from "../api/hooks";
import { STAGE_NAMES } from "../api/types";
import {
  addCustomProvider,
  allProviders,
  providerBaseUrl,
} from "../app/llmProviders";

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
  const [providers, setProviders] = useState(() => allProviders());
  const [addingProvider, setAddingProvider] = useState(false);
  const [newProviderName, setNewProviderName] = useState("");
  const [newProviderUrl, setNewProviderUrl] = useState("");

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
            </div>
          )}

          {section === "llm" && (
            <div className="flex flex-col gap-4">
              <Switch
                label="Summarize with an LLM"
                description="Runs the clean & summarize stages. Off = transcript only."
                checked={Boolean(llm.enabled)}
                onCheckedChange={(v) => patch("llm", "enabled", v)}
              />

              <fieldset
                disabled={!llm.enabled}
                className="flex flex-col gap-4 disabled:opacity-50"
              >
                <Select
                  label="Provider"
                  value={
                    providers.find((p) => p.baseUrl === llm.base_url)?.name ??
                    ""
                  }
                  onValueChange={(name) =>
                    patch("llm", "base_url", providerBaseUrl(name) ?? "")
                  }
                  options={providers.map((p) => ({ value: p.name }))}
                />
                {!addingProvider && (
                  <button
                    type="button"
                    onClick={() => setAddingProvider(true)}
                    className="self-start text-[13px] text-ink-faint hover:text-ink"
                  >
                    + Add custom endpoint…
                  </button>
                )}
                {addingProvider && (
                  <div className="flex flex-col gap-2 rounded-sm border border-hairline p-3">
                    <Input
                      label="Name"
                      value={newProviderName}
                      onChange={(e) => setNewProviderName(e.target.value)}
                    />
                    <Input
                      label="URL"
                      value={newProviderUrl}
                      onChange={(e) => setNewProviderUrl(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        disabled={
                          !newProviderName.trim() || !newProviderUrl.trim()
                        }
                        onClick={() => {
                          const name = newProviderName.trim();
                          const baseUrl = newProviderUrl.trim();
                          if (!name || !baseUrl) return;
                          const next = addCustomProvider({ name, baseUrl });
                          setProviders([...next]);
                          patch("llm", "base_url", baseUrl);
                          setNewProviderName("");
                          setNewProviderUrl("");
                          setAddingProvider(false);
                        }}
                      >
                        Add
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => setAddingProvider(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                <Input
                  label="Model"
                  value={String(llm.model ?? "")}
                  onChange={(e) => patch("llm", "model", e.target.value)}
                />
                <Input
                  label="Base URL"
                  value={String(llm.base_url ?? "")}
                  onChange={(e) => patch("llm", "base_url", e.target.value)}
                />
                <p className="text-[13px] text-ink-faint">
                  API key read from{" "}
                  <code className="font-mono">
                    {String(llm.api_key_env ?? "")}
                  </code>{" "}
                  · {system.data?.llm_key_present ? "detected ✓" : "missing"}
                </p>
              </fieldset>
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
              <div>
                <label
                  htmlFor="summary-filename-stem"
                  className="mb-1.5 block text-sm font-medium text-ink"
                >
                  Summary filename
                </label>
                <div className="flex items-center gap-1.5">
                  <Input
                    id="summary-filename-stem"
                    value={String(output.summary_filename ?? "").replace(
                      /\.md$/i,
                      "",
                    )}
                    onChange={(e) => {
                      const stem =
                        e.target.value.replace(/\.md$/i, "").trim() ||
                        "summary";
                      patch("output", "summary_filename", `${stem}.md`);
                    }}
                  />
                  <span className="font-mono text-sm text-ink-faint">.md</span>
                </div>
              </div>
              <Switch
                label="Save bundle .docx"
                checked={Boolean(output.save_bundle_docx)}
                onCheckedChange={(v) => patch("output", "save_bundle_docx", v)}
              />
            </div>
          )}

          {section === "stages" && (
            <div className="grid grid-cols-2 gap-3">
              {STAGE_NAMES.map((s) => (
                <Switch
                  key={s}
                  label={s}
                  checked={stagesEnabled[s] !== false}
                  onCheckedChange={(v) => toggleStage(s, v)}
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
