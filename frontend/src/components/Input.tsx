import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { cn } from "../lib/cn";
import { FieldShell, controlBase, type FieldChrome } from "./Field";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & FieldChrome;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, className, id, ...props },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell id={fieldId} label={label} error={error}>
      <input
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${fieldId}-error` : undefined}
        className={cn(controlBase, className)}
        {...props}
      />
    </FieldShell>
  );
});
