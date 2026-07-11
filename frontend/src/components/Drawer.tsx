import * as Dialog from "@radix-ui/react-dialog";
import { type ReactNode } from "react";

export interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
}

export function Drawer({ open, onOpenChange, title, children }: DrawerProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-ink/40 [animation:overlay-in_var(--dur)_var(--ease-editorial)]" />
        <Dialog.Content className="fixed inset-y-0 right-0 w-[min(92vw,420px)] border-l border-hairline bg-surface p-6 shadow-[var(--shadow-soft)] [animation:drawer-in_var(--dur-lg)_var(--ease-editorial)]">
          <Dialog.Title className="text-xl text-ink">{title}</Dialog.Title>
          <div className="mt-4 text-sm text-ink-soft">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
