import { EmptyState } from "../components";
import { WaveSine } from "@phosphor-icons/react";

export function Library() {
  return (
    <EmptyState
      title="Pick a set"
      description="Choose a set from the library, or create one to start the pipeline."
      icon={<WaveSine size={28} weight="duotone" />}
    />
  );
}
