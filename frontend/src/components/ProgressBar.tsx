export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={clamped}
      className="h-1 w-full overflow-hidden rounded-sm bg-sink"
    >
      <div
        className="h-full origin-left rounded-sm bg-accent transition-transform duration-[var(--dur)] ease-editorial"
        style={{ transform: `scaleX(${clamped / 100})` }}
      />
    </div>
  );
}
