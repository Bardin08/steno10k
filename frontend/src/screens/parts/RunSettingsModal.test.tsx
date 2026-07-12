import { MemoryRouter } from "react-router";
import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { RunSettingsModal } from "./RunSettingsModal";

function renderModal(onConfirm = vi.fn()) {
  render(
    <MemoryRouter>
      <RunSettingsModal
        open
        onOpenChange={() => {}}
        enabledStages={["normalize", "chunk", "transcribe"]}
        onConfirm={onConfirm}
      />
    </MemoryRouter>,
  );
  return onConfirm;
}

test("toggling force and confirming calls onConfirm with force: true", () => {
  const onConfirm = renderModal();
  fireEvent.click(screen.getByRole("switch", { name: /re-run from scratch/i }));
  fireEvent.click(screen.getByRole("button", { name: /transcribe/i }));
  expect(onConfirm).toHaveBeenCalledWith({ force: true });
});

test("lists enabled stages", () => {
  renderModal();
  expect(screen.getByText("normalize")).toBeInTheDocument();
  expect(screen.getByText("chunk")).toBeInTheDocument();
  expect(screen.getByText("transcribe")).toBeInTheDocument();
});
