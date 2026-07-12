import { Gear } from "@phosphor-icons/react";

export interface SplitButtonProps {
  label: string;
  onPrimary: () => void;
  onGear: () => void;
  disabled?: boolean;
}

const shared =
  "inline-flex items-center justify-center bg-ink text-paper " +
  "transition-[transform,background-color] duration-[var(--dur-micro)] ease-editorial " +
  "hover:opacity-90 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-accent disabled:opacity-50 disabled:pointer-events-none";

export function SplitButton({
  label,
  onPrimary,
  onGear,
  disabled,
}: SplitButtonProps) {
  return (
    <div className="inline-flex">
      <button
        type="button"
        disabled={disabled}
        onClick={onPrimary}
        className={`${shared} rounded-l-pill border border-transparent px-5 py-2.5 text-sm font-medium`}
      >
        {label}
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={onGear}
        aria-label="Run settings"
        className={`${shared} rounded-r-pill border-l border-hairline px-3 py-2.5`}
      >
        <Gear size={16} weight="bold" />
      </button>
    </div>
  );
}
