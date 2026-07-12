import { useId } from "react";
import * as RadixSwitch from "@radix-ui/react-switch";

export interface SwitchProps {
  label: string;
  description?: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
}

export function Switch({
  label,
  description,
  checked,
  onCheckedChange,
  disabled,
  id,
}: SwitchProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <div className="flex items-start gap-3">
      <RadixSwitch.Root
        id={fieldId}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
        className="relative h-[22px] w-[38px] flex-none rounded-pill bg-hairline-strong transition-colors duration-[var(--dur-micro)] ease-editorial data-[state=checked]:bg-accent disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <RadixSwitch.Thumb className="block h-[18px] w-[18px] translate-x-0.5 rounded-full bg-paper transition-transform duration-[var(--dur-micro)] ease-editorial data-[state=checked]:translate-x-[18px]" />
      </RadixSwitch.Root>
      <label htmlFor={fieldId} className="cursor-pointer select-none">
        <span className="block text-sm font-medium text-ink">{label}</span>
        {description && (
          <span className="block text-[11px] text-ink-faint">
            {description}
          </span>
        )}
      </label>
    </div>
  );
}
