import { expect, test } from "vitest";
import { resolveEnabledStages, STAGE_DEPS } from "./stageDeps";

test("transcribe disabled cascades to clean/merge/summarize/bundle/notify", () => {
  const flags = Object.fromEntries(
    Object.keys(STAGE_DEPS).map((s) => [s, s !== "transcribe"]),
  );
  const { enabled, cascaded } = resolveEnabledStages(flags);

  expect(enabled.has("transcribe")).toBe(false);
  expect(enabled.has("clean")).toBe(false);
  expect(enabled.has("merge")).toBe(false);
  expect(enabled.has("summarize")).toBe(false);
  expect(enabled.has("bundle")).toBe(false);
  expect(enabled.has("notify")).toBe(false);

  expect(enabled.has("normalize")).toBe(true);
  expect(enabled.has("chunk")).toBe(true);

  expect(cascaded.clean).toBe("transcribe");
});

test("all stages enabled yields all 8 enabled and no cascading", () => {
  const flags = Object.fromEntries(
    Object.keys(STAGE_DEPS).map((s) => [s, true]),
  );
  const { enabled, cascaded } = resolveEnabledStages(flags);

  expect(enabled.size).toBe(8);
  expect(cascaded).toEqual({});
});
