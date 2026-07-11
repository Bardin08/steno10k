import { forwardRef, useId, type TextareaHTMLAttributes } from "react";
import { cn } from "../lib/cn";
import { FieldShell, controlBase, type FieldChrome } from "./Field";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> &
  FieldChrome;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ label, error, className, id, ...props }, ref) {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldShell id={fieldId} label={label} error={error}>
        <textarea
          ref={ref}
          id={fieldId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${fieldId}-error` : undefined}
          className={cn(controlBase, "min-h-24 resize-y", className)}
          {...props}
        />
      </FieldShell>
    );
  },
);
