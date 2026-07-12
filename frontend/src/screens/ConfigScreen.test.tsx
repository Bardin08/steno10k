import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { makeQueryClient } from "../app/queryClient";
import * as hooks from "../api/hooks";
import { ConfigScreen } from "./ConfigScreen";

afterEach(() => vi.restoreAllMocks());

function renderConfig() {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <ConfigScreen />
    </QueryClientProvider>,
  );
}

test("renders transcription, llm, and per-stage toggles from config", async () => {
  vi.spyOn(hooks, "usePutConfig").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof hooks.usePutConfig>);
  vi.spyOn(hooks, "useSystem").mockReturnValue({
    data: {
      whisper_models: ["small", "large-v3"],
      current_model: "small",
      max_workers: 4,
      data_root: "/data",
    },
    isLoading: false,
  } as unknown as ReturnType<typeof hooks.useSystem>);
  vi.spyOn(hooks, "useConfig").mockReturnValue({
    data: {
      transcription: { model: "small", device: "cpu", compute_type: "int8" },
      llm: {
        model: "gpt-4o",
        base_url: "",
        api_key_env: "OPENAI_API_KEY",
        enabled: true,
      },
      audio: { chunk_seconds: 600, overlap_seconds: 15 },
      output: { save_bundle_docx: true, summary_filename: "summary.md" },
      stages: { enabled: { transcribe: true, notify: false } },
    },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useConfig>);

  const user = userEvent.setup();
  renderConfig();
  // Default section: Transcription.
  expect(screen.getByLabelText(/whisper model/i)).toBeInTheDocument();

  // LLM section.
  await user.click(screen.getByRole("button", { name: "LLM" }));
  expect(screen.getByLabelText(/model/i)).toBeInTheDocument();

  // Stages section: per-stage switches reflect config (absent key = enabled).
  await user.click(screen.getByRole("button", { name: "Stages" }));
  expect(screen.getByRole("switch", { name: "transcribe" })).toBeChecked();
  expect(screen.getByRole("switch", { name: "notify" })).not.toBeChecked();
});

test("vertical nav renders all four sections and a help region is present", () => {
  vi.spyOn(hooks, "usePutConfig").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof hooks.usePutConfig>);
  vi.spyOn(hooks, "useSystem").mockReturnValue({
    data: {
      whisper_models: ["small", "large-v3"],
      current_model: "small",
      max_workers: 4,
      data_root: "/data",
      llm_key_present: true,
    },
    isLoading: false,
  } as unknown as ReturnType<typeof hooks.useSystem>);
  vi.spyOn(hooks, "useConfig").mockReturnValue({
    data: {
      transcription: { model: "small" },
      llm: {
        model: "gpt-4o",
        base_url: "",
        api_key_env: "OPENAI_API_KEY",
        enabled: true,
      },
      audio: { chunk_seconds: 600, overlap_seconds: 15 },
      output: { save_bundle_docx: true, summary_filename: "summary.md" },
      stages: { enabled: { transcribe: true, notify: false } },
    },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useConfig>);

  renderConfig();

  for (const label of ["Transcription", "LLM", "Audio & Output", "Stages"]) {
    expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
  }
  expect(screen.getByRole("button", { name: "Transcription" })).toHaveAttribute(
    "aria-current",
    "true",
  );
  expect(screen.getByRole("region", { name: /help/i })).toBeInTheDocument();
});

test("transcription section drops Device/Compute type; filename stem locks .md; switches replace checkboxes", async () => {
  const mutate = vi.fn();
  vi.spyOn(hooks, "usePutConfig").mockReturnValue({
    mutate,
    isPending: false,
  } as unknown as ReturnType<typeof hooks.usePutConfig>);
  vi.spyOn(hooks, "useSystem").mockReturnValue({
    data: {
      whisper_models: ["small", "large-v3"],
      current_model: "small",
      max_workers: 4,
      data_root: "/data",
      llm_key_present: true,
    },
    isLoading: false,
  } as unknown as ReturnType<typeof hooks.useSystem>);
  vi.spyOn(hooks, "useConfig").mockReturnValue({
    data: {
      transcription: { model: "small" },
      llm: {
        model: "gpt-4o",
        base_url: "",
        api_key_env: "OPENAI_API_KEY",
        enabled: true,
      },
      audio: { chunk_seconds: 600, overlap_seconds: 15 },
      output: { save_bundle_docx: true, summary_filename: "summary.md" },
      stages: { enabled: { transcribe: true, notify: false } },
    },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useConfig>);

  const user = userEvent.setup();
  renderConfig();

  // Transcription: Device / Compute type inputs are gone.
  expect(screen.queryByLabelText(/^device$/i)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/compute type/i)).not.toBeInTheDocument();

  // Audio & Output: filename stem is editable, ".md" suffix is static.
  await user.click(screen.getByRole("button", { name: "Audio & Output" }));
  const stemInput = screen.getByLabelText(/summary filename/i);
  expect(stemInput).toHaveValue("summary");
  expect(screen.getByText(".md")).toBeInTheDocument();
  await user.clear(stemInput);
  await user.type(stemInput, "notes");

  const bundleSwitch = screen.getByRole("switch", {
    name: "Save bundle .docx",
  });
  expect(bundleSwitch).toBeChecked();
  await user.click(bundleSwitch);

  await user.click(screen.getByRole("button", { name: "Stages" }));
  const transcribeSwitch = screen.getByRole("switch", { name: "transcribe" });
  expect(transcribeSwitch).toBeChecked();
  await user.click(transcribeSwitch);

  await user.click(screen.getByRole("button", { name: "Save config" }));

  expect(mutate).toHaveBeenCalledTimes(1);
  const saved = mutate.mock.calls[0][0];
  expect(saved.output.summary_filename).toBe("notes.md");
  expect(saved.output.save_bundle_docx).toBe(false);
  expect(saved.stages.enabled.transcribe).toBe(false);
});

test("LLM section: master switch, provider dropdown auto-fills base URL, no api key env input, key status line", async () => {
  vi.spyOn(hooks, "usePutConfig").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof hooks.usePutConfig>);
  vi.spyOn(hooks, "useSystem").mockReturnValue({
    data: {
      whisper_models: ["small", "large-v3"],
      current_model: "small",
      max_workers: 4,
      data_root: "/data",
      llm_key_present: true,
    },
    isLoading: false,
  } as unknown as ReturnType<typeof hooks.useSystem>);
  vi.spyOn(hooks, "useConfig").mockReturnValue({
    data: {
      transcription: { model: "small" },
      llm: {
        model: "gpt-4o",
        base_url: "",
        api_key_env: "OPENAI_API_KEY",
        enabled: true,
      },
      audio: { chunk_seconds: 600, overlap_seconds: 15 },
      output: { save_bundle_docx: true, summary_filename: "summary.md" },
      stages: { enabled: { transcribe: true, notify: false } },
    },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useConfig>);

  const user = userEvent.setup();
  renderConfig();
  await user.click(screen.getByRole("button", { name: "LLM" }));

  const masterSwitch = screen.getByRole("switch", {
    name: /summarize with an llm/i,
  });
  expect(masterSwitch).toBeChecked();

  await user.click(screen.getByRole("combobox", { name: /provider/i }));
  await user.click(screen.getByRole("option", { name: "OpenAI" }));
  expect(screen.getByLabelText(/base url/i)).toHaveValue(
    "https://api.openai.com/v1",
  );

  expect(screen.queryByLabelText(/api key env var/i)).not.toBeInTheDocument();
  expect(screen.getByText(/OPENAI_API_KEY/)).toBeInTheDocument();
  expect(screen.getByText(/detected/i)).toBeInTheDocument();

  await user.click(masterSwitch);
  expect(masterSwitch).not.toBeChecked();
});
