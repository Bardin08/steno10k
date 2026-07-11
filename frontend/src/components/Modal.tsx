import * as Dialog from "@radix-ui/react-dialog";
import { type ReactNode } from "react";

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
}

export function Modal({ open, onOpenChange, title, children }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-ink/40 [animation:overlay-in_var(--dur)_var(--ease-editorial)]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-[min(92vw,480px)] -translate-x-1/2 -translate-y-1/2 rounded-md border border-hairline bg-surface p-6 shadow-[var(--shadow-soft)] [animation:modal-in_var(--dur-lg)_var(--ease-editorial)]">
          <Dialog.Title className="text-xl text-ink">{title}</Dialog.Title>
          <div className="mt-3 text-sm text-ink-soft">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
