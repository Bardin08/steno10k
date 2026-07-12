import { useId } from "react";
import * as RadixSelect from "@radix-ui/react-select";
import { CaretDown, Check } from "@phosphor-icons/react";
import { cn } from "../lib/cn";
import { FieldShell, controlBase, type FieldChrome } from "./Field";

export interface SelectOption {
  value: string;
  label?: string;
}

export interface SelectProps extends FieldChrome {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  id?: string;
  disabled?: boolean;
}

/** A styled dropdown built on Radix Select — no native OS popup. Pass a
 *  controlled `value` + `onValueChange`; the trigger renders the selected
 *  option's label (or the placeholder when empty). */
export function Select({
  label,
  error,
  value,
  defaultValue,
  onValueChange,
  options,
  placeholder = "Select…",
  id,
  disabled,
}: SelectProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const selected = value ?? defaultValue;
  const selectedLabel =
    selected != null
      ? (options.find((o) => o.value === selected)?.label ?? selected)
      : undefined;

  return (
    <FieldShell id={fieldId} label={label} error={error}>
      <RadixSelect.Root
        value={value}
        defaultValue={defaultValue}
        onValueChange={onValueChange}
        disabled={disabled}
      >
        <RadixSelect.Trigger
          id={fieldId}
          aria-label={label}
          aria-invalid={error ? true : undefined}
          className={cn(
            controlBase,
            "flex items-center justify-between gap-2 disabled:opacity-50",
          )}
        >
          <RadixSelect.Value placeholder={placeholder}>
            {selectedLabel}
          </RadixSelect.Value>
          <RadixSelect.Icon className="text-ink-faint">
            <CaretDown size={14} />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content
            position="popper"
            sideOffset={4}
            className="z-50 max-h-64 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-sm border border-hairline bg-surface shadow-[var(--shadow-soft)] [animation:modal-in_var(--dur)_var(--ease-editorial)]"
          >
            <RadixSelect.Viewport className="p-1">
              {options.map((o) => (
                <RadixSelect.Item
                  key={o.value}
                  value={o.value}
                  className="flex cursor-pointer select-none items-center justify-between gap-3 rounded-sm px-2.5 py-1.5 text-sm text-ink outline-none data-[highlighted]:bg-ink data-[highlighted]:text-paper"
                >
                  <RadixSelect.ItemText>
                    {o.label ?? o.value}
                  </RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator>
                    <Check size={13} />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    </FieldShell>
  );
}
