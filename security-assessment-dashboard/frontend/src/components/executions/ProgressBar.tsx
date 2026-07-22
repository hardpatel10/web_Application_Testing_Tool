export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="h-2 w-full overflow-hidden rounded-full border border-border/50 bg-background/40">
      <div
        className="h-full rounded-full bg-primary shadow-[0_0_18px_-8px_hsl(var(--primary))] transition-[width] duration-500"
        style={{ width: `${clamped}%` }}
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  );
}
