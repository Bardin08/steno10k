import { useId, type InputHTMLAttributes } from "react";
import { Check } from "@phosphor-icons/react";
import { cn } from "../lib/cn";

export type CheckboxProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "type"
> & {
  label: string;
};

/** A design-system checkbox: a styled box (accent fill when checked) over a
 *  real native input, so it stays keyboard- and label-accessible. */
export function Checkbox({ label, className, id, ...props }: CheckboxProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <label
      htmlFor={fieldId}
      className="inline-flex cursor-pointer select-none items-center gap-2.5 text-sm text-ink"
    >
      <span className="relative inline-grid h-4 w-4 place-items-center">
        <input
          id={fieldId}
          type="checkbox"
          className={cn(
            "peer h-4 w-4 appearance-none rounded-[4px] border border-hairline-strong bg-surface",
            "transition-colors duration-[var(--dur-micro)] ease-editorial",
            "checked:border-accent checked:bg-accent",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
            className,
          )}
          {...props}
        />
        <Check
          size={11}
          weight="bold"
          className="pointer-events-none absolute text-paper opacity-0 peer-checked:opacity-100"
        />
      </span>
      {label}
    </label>
  );
}
