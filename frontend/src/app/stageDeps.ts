// Frontend mirror of the backend stage dependency graph.
// SOURCE OF TRUTH: backend/src/steno10k/api/stages.py (STAGE_DEPS) and
// backend/src/steno10k/contracts/stage.py (resolve_enabled). Keep in sync.
export const STAGE_DEPS: Record<string, string[]> = {
  normalize: [],
  chunk: ["normalize"],
  transcribe: ["chunk"],
  clean: ["transcribe"],
  merge: ["transcribe"],
  summarize: ["merge", "clean"],
  bundle: ["merge"],
  notify: ["bundle"],
};

/** Effective enabled stages after cascade-disabling to a fixed point.
 *  Mirrors backend `resolve_enabled`. `flags` maps stage -> user on/off. */
export function resolveEnabledStages(flags: Record<string, boolean>): {
  enabled: Set<string>;
  cascaded: Record<string, string>;
} {
  const enabled = new Set(Object.keys(flags).filter((k) => flags[k]));
  const cascaded: Record<string, string> = {};
  let changed = true;
  while (changed) {
    changed = false;
    for (const name of [...enabled]) {
      for (const dep of STAGE_DEPS[name] ?? []) {
        if (!enabled.has(dep)) {
          enabled.delete(name);
          if (!(name in cascaded)) cascaded[name] = dep;
          changed = true;
          break;
        }
      }
    }
  }
  return { enabled, cascaded };
}
