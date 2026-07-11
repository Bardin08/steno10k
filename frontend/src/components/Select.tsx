import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import { cn } from "../lib/cn";
import { FieldShell, controlBase, type FieldChrome } from "./Field";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & FieldChrome;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  function Select({ label, error, className, id, children, ...props }, ref) {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldShell id={fieldId} label={label} error={error}>
        <select
          ref={ref}
          id={fieldId}
          aria-invalid={error ? true : undefined}
          className={cn(controlBase, "appearance-none pr-8", className)}
          {...props}
        >
          {children}
        </select>
      </FieldShell>
    );
  },
);
