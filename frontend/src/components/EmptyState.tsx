import { type ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-hairline-strong bg-surface px-6 py-14 text-center">
      {icon && <div className="text-ink-faint">{icon}</div>}
      <h3 className="text-lg text-ink">{title}</h3>
      {description && (
        <p className="max-w-[40ch] text-sm text-ink-soft">{description}</p>
      )}
      {action}
    </div>
  );
}
