import { RuleTester } from "eslint";
import { expect, test } from "vitest";
import plugin from "./index.js";

const tester = new RuleTester({
  languageOptions: { ecmaVersion: 2022, sourceType: "module" },
});

test("no-raw-hex flags a hardcoded color, allows token references", () => {
  tester.run("no-raw-hex", plugin.rules["no-raw-hex"], {
    valid: [
      { code: 'const c = "var(--color-ink)";' },
      { code: 'const path = "#/queue";' }, // route hash, not a color
    ],
    invalid: [
      {
        code: 'const c = "#ffffff";',
        errors: [{ messageId: "rawHex" }],
      },
      {
        code: 'const x = <div className="bg-[#3f6b52]" />;',
        errors: [{ messageId: "rawHex" }],
        languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } },
      },
    ],
  });
});

test("no-emoji flags an emoji in a string or JSX text", () => {
  tester.run("no-emoji", plugin.rules["no-emoji"], {
    valid: [{ code: 'const s = "done";' }],
    invalid: [
      { code: 'const s = "done ✅";', errors: [{ messageId: "emoji" }] },
    ],
  });
});
