import { useState, type FormEvent } from "react";
import { Button, Input, Modal } from "../components";

interface CreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  label: string;
  submitLabel: string;
  pending?: boolean;
  onSubmit: (value: string) => void;
}

/** A small titled form modal: one text field + Cancel/Submit. Submits the
 *  trimmed value on Enter or click; the parent closes it (e.g. onSuccess). */
export function CreateDialog({
  open,
  onOpenChange,
  title,
  label,
  submitLabel,
  pending,
  onSubmit,
}: CreateDialogProps) {
  const [value, setValue] = useState("");

  function change(next: boolean) {
    if (!next) setValue(""); // reset when closing so the next open starts blank
    onOpenChange(next);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || pending) return;
    onSubmit(trimmed);
  }

  return (
    <Modal open={open} onOpenChange={change} title={title}>
      <form onSubmit={handleSubmit} className="mt-2 flex flex-col gap-5">
        <Input
          label={label}
          value={value}
          autoFocus
          onChange={(e) => setValue(e.target.value)}
        />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={() => change(false)}>
            Cancel
          </Button>
          <Button type="submit" disabled={pending || !value.trim()}>
            {submitLabel}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
