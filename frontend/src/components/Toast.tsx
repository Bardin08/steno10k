import { Toaster as SonnerToaster, toast } from "sonner";

export { toast };

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "rounded-md border border-hairline bg-surface text-sm text-ink shadow-[var(--shadow-soft)]",
          description: "text-ink-soft",
        },
      }}
    />
  );
}
