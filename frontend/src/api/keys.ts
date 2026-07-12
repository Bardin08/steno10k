export const keys = {
  projects: () => ["projects"] as const,
  project: (p: string) => ["projects", p] as const,
  set: (p: string, s: string) => ["projects", p, "sets", s] as const,
  recordings: (p: string, s: string) =>
    ["projects", p, "sets", s, "recordings"] as const,
  artifacts: (p: string, s: string) =>
    ["projects", p, "sets", s, "artifacts"] as const,
  runs: () => ["runs"] as const,
  config: () => ["config"] as const,
  system: () => ["system"] as const,
};
