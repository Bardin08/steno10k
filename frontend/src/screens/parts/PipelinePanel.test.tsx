import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { makeQueryClient } from "../../app/queryClient";
import { STAGE_NAMES } from "../../api/types";
import { PipelinePanel } from "./PipelinePanel";

function renderPanel(runId: string | null) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <PipelinePanel
        project="con-law"
        set="jr"
        runId={runId}
        onCancel={() => {}}
      />
    </QueryClientProvider>,
  );
}

test("idle skeleton lists every stage and has no event log", () => {
  renderPanel(null);
  expect(screen.getByText(/pipeline/i)).toHaveTextContent("Pipeline · idle");
  STAGE_NAMES.forEach((name) => {
    expect(screen.getByText(name)).toBeInTheDocument();
  });
  expect(screen.queryByText(/event log/i)).toBeNull();
});
