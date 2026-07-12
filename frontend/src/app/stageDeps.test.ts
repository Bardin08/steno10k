import { expect, test } from "vitest";
import { resolveEnabledStages, STAGE_DEPS } from "./stageDeps";

const ALL_STAGES = Object.keys(STAGE_DEPS);

test("disabling transcribe cascades to clean, merge, summarize, bundle, notify", () => {
  const flags = Object.fromEntries(
    ALL_STAGES.map((s) => [s, s !== "transcribe"]),
  );

  const { enabled, cascaded } = resolveEnabledStages(flags);

  expect(enabled.has("normalize")).toBe(true);
  expect(enabled.has("chunk")).toBe(true);
  expect(enabled.has("transcribe")).toBe(false);
  expect(enabled.has("clean")).toBe(false);
  expect(enabled.has("merge")).toBe(false);
  expect(enabled.has("summarize")).toBe(false);
  expect(enabled.has("bundle")).toBe(false);
  expect(enabled.has("notify")).toBe(false);

  expect(cascaded.clean).toBe("transcribe");
  expect(cascaded.merge).toBe("transcribe");
  expect(cascaded.summarize).toBe("merge");
  expect(cascaded.bundle).toBe("merge");
  expect(cascaded.notify).toBe("bundle");
  expect(cascaded.transcribe).toBeUndefined();
});

test("all stages enabled yields all 8 enabled and no cascade", () => {
  const flags = Object.fromEntries(ALL_STAGES.map((s) => [s, true]));

  const { enabled, cascaded } = resolveEnabledStages(flags);

  expect(enabled.size).toBe(8);
  for (const s of ALL_STAGES) expect(enabled.has(s)).toBe(true);
  expect(cascaded).toEqual({});
});
