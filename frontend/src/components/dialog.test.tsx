import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { Modal } from "./Modal";
import { Drawer } from "./Drawer";
import { CreateDialog } from "../app/CreateDialog";

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

test("CreateDialog with an icon picker submits the chosen icon", () => {
  const onSubmit = vi.fn();
  render(
    <CreateDialog
      open
      onOpenChange={() => {}}
      title="New project"
      label="Project title"
      submitLabel="Create project"
      withIconPicker
      onSubmit={onSubmit}
    />,
  );
  fireEvent.change(screen.getByLabelText(/project title/i), {
    target: { value: "Law" },
  });
  fireEvent.click(screen.getByRole("button", { name: "icon scales" }));
  fireEvent.click(screen.getByRole("button", { name: /create project/i }));

  expect(onSubmit).toHaveBeenCalledWith("Law", "scales");
});

test("CreateDialog without an icon picker submits no icon", () => {
  const onSubmit = vi.fn();
  render(
    <CreateDialog
      open
      onOpenChange={() => {}}
      title="New set"
      label="Set title"
      submitLabel="Create set"
      onSubmit={onSubmit}
    />,
  );
  fireEvent.change(screen.getByLabelText(/set title/i), {
    target: { value: "Judicial Review" },
  });
  fireEvent.click(screen.getByRole("button", { name: /create set/i }));

  expect(onSubmit).toHaveBeenCalledWith("Judicial Review", undefined);
});
