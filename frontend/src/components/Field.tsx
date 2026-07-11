import { type ReactNode } from "react";

export interface FieldChrome {
  label?: string;
  error?: string;
}

export function FieldShell({
  id,
  label,
  error,
  children,
}: FieldChrome & { id: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
        </label>
      )}
      {children}
      {error && (
        <p id={`${id}-error`} className="font-mono text-xs text-accent-ink">
          {error}
        </p>
      )}
    </div>
  );
}

export const controlBase =
  "rounded-sm border border-hairline-strong bg-surface px-3 py-2 text-sm " +
  "text-ink placeholder:text-ink-faint transition-colors " +
  "duration-[var(--dur-micro)] ease-editorial " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent " +
  "aria-[invalid=true]:border-accent-ink";
