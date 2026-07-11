/* eslint-disable steno10k/no-raw-hex -- this test guards the frozen hex token values verbatim */
import { readFileSync } from "node:fs";
import { fileURLToPath, URL as NodeURL } from "node:url";
import { expect, test } from "vitest";

const css = readFileSync(
  fileURLToPath(new NodeURL("./tokens.css", import.meta.url)),
  "utf8",
);

test("light canvas + accent tokens match the approved preview", () => {
  expect(css).toContain("--color-paper: #f6f5f2;");
  expect(css).toContain("--color-ink: #1a1917;");
  expect(css).toContain("--color-accent: #3f6b52;");
  expect(css).toContain("--color-accent-wash: #eef4ef;");
});

test("dark theme overrides the same vars (never pure black)", () => {
  expect(css).toContain('[data-theme="dark"]');
  expect(css).toContain("--color-paper: #171614;");
  expect(css).toContain("--color-accent: #6fa585;");
  expect(css).not.toContain("#000000");
});

test("motion + shape tokens exist", () => {
  expect(css).toContain("--ease-editorial: cubic-bezier(0.22, 1, 0.36, 1);");
  expect(css).toContain("--dur-micro: 140ms;");
  expect(css).toContain("--radius-md: 12px;");
});
