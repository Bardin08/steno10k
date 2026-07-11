import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Modal } from "./Modal";
import { Drawer } from "./Drawer";

test("Modal renders its content when open", () => {
  render(
    <Modal open title="Delete set?" onOpenChange={() => {}}>
      <p>This cannot be undone.</p>
    </Modal>,
  );
  expect(screen.getByRole("dialog")).toHaveTextContent("Delete set?");
  expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
});

test("Drawer renders its content when open", () => {
  render(
    <Drawer open title="Configuration" onOpenChange={() => {}}>
      <p>stage flags</p>
    </Drawer>,
  );
  expect(screen.getByRole("dialog")).toHaveTextContent("Configuration");
});
