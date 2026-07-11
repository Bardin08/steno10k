import { WarningCircle } from "@phosphor-icons/react";
import { Button } from "./Button";

export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-md border border-hairline bg-surface p-6">
      <WarningCircle size={22} className="text-accent-ink" weight="duotone" />
      <p className="text-sm text-ink-soft">{message}</p>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
