import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
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

test("renders transcription, llm, and per-stage toggles from config", () => {
  vi.spyOn(hooks, "usePutConfig").mockReturnValue({ mutate: vi.fn(), isPending: false } as unknown as ReturnType<typeof hooks.usePutConfig>);
  vi.spyOn(hooks, "useSystem").mockReturnValue({
    data: { whisper_models: ["small", "large-v3"], current_model: "small", max_workers: 4, data_root: "/data" },
    isLoading: false,
  } as unknown as ReturnType<typeof hooks.useSystem>);
  vi.spyOn(hooks, "useConfig").mockReturnValue({
    data: {
      transcription: { model: "small", device: "cpu", compute_type: "int8" },
      llm: { model: "gpt-4o", base_url: "", api_key_env: "OPENAI_API_KEY", enabled: true },
      audio: { chunk_seconds: 600, overlap_seconds: 15 },
      output: { save_bundle_docx: true, summary_filename: "summary.md" },
      stages: { enabled: { transcribe: true, notify: false } },
    },
    isLoading: false, isError: false,
  } as unknown as ReturnType<typeof hooks.useConfig>);

  renderConfig();
  expect(screen.getByLabelText(/whisper model/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/llm model/i)).toBeInTheDocument();
  expect(screen.getByLabelText("transcribe")).toBeChecked();
  expect(screen.getByLabelText("notify")).not.toBeChecked();
});
