import { useState } from "react";
import { NavLink } from "react-router";
import { Button, Modal, Switch } from "../../components";

export interface RunSettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  enabledStages: string[];
  onConfirm: (opts: { force: boolean }) => void;
}

export function RunSettingsModal({
  open,
  onOpenChange,
  enabledStages,
  onConfirm,
}: RunSettingsModalProps) {
  const [force, setForce] = useState(false);

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Run settings">
      <div className="flex flex-col gap-5">
        <Switch
          label="Re-run from scratch"
          description="Overwrite existing outputs."
          checked={force}
          onCheckedChange={setForce}
        />

        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
            Enabled stages
          </p>
          <ul className="flex flex-wrap gap-1.5">
            {enabledStages.map((stage) => (
              <li
                key={stage}
                className="rounded-pill border border-hairline bg-paper px-2.5 py-1 font-mono text-[11px] text-ink-soft"
              >
                {stage}
              </li>
            ))}
          </ul>
        </div>

        <NavLink
          to="/config"
          className="w-fit text-sm text-ink-soft underline decoration-hairline-strong underline-offset-4 hover:text-ink"
        >
          edit in Config →
        </NavLink>

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => onConfirm({ force })}>Transcribe</Button>
        </div>
      </div>
    </Modal>
  );
}
