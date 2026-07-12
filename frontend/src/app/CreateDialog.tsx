import { useEffect, useState, type FormEvent } from "react";
import { Button, Input, Modal } from "../components";
import {
  DEFAULT_PROJECT_ICON,
  PROJECT_ICON_KEYS,
  ProjectIcon,
} from "./projectIcons";

interface CreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  label: string;
  submitLabel: string;
  pending?: boolean;
  /** Existing sibling names; a case-insensitive match is rejected inline. */
  existingNames?: string[];
  /** Renders a curated icon picker (used by the New Project dialog). */
  withIconPicker?: boolean;
  onSubmit: (value: string, icon?: string) => void;
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
  existingNames,
  withIconPicker,
  onSubmit,
}: CreateDialogProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [icon, setIcon] = useState(DEFAULT_PROJECT_ICON);

  // Start every open blank + error-free. This runs on open regardless of how
  // the previous instance closed — including the parent closing via onSuccess,
  // where Radix's onOpenChange never fires.
  useEffect(() => {
    if (open) {
      setValue("");
      setError(undefined);
      setIcon(DEFAULT_PROJECT_ICON);
    }
  }, [open]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || pending) return;
    const clash = existingNames?.some(
      (n) => n.toLowerCase() === trimmed.toLowerCase(),
    );
    if (clash) {
      setError(`"${trimmed}" already exists.`);
      return;
    }
    onSubmit(trimmed, withIconPicker ? icon : undefined);
  }

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={title}>
      <form onSubmit={handleSubmit} className="mt-2 flex flex-col gap-5">
        <Input
          label={label}
          value={value}
          error={error}
          autoFocus
          onChange={(e) => {
            setValue(e.target.value);
            if (error) setError(undefined);
          }}
        />
        {withIconPicker && (
          <div className="flex flex-wrap gap-1.5">
            {PROJECT_ICON_KEYS.map((key) => (
              <button
                key={key}
                type="button"
                aria-label={`icon ${key}`}
                aria-pressed={icon === key}
                onClick={() => setIcon(key)}
                className={`grid h-8 w-8 place-items-center rounded-sm border transition-colors duration-[var(--dur-micro)] ease-editorial ${
                  icon === key
                    ? "border-ink bg-ink text-paper"
                    : "border-hairline text-ink-faint hover:text-ink"
                }`}
              >
                <ProjectIcon icon={key} />
              </button>
            ))}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
          >
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
