import js from "@eslint/js";
import tseslint from "typescript-eslint";
import steno10k from "./eslint-rules/index.js";

export default tseslint.config(
  { ignores: ["dist", "eslint-rules/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { steno10k },
    rules: {
      "steno10k/no-raw-hex": "error",
      "steno10k/no-emoji": "error",
    },
  },
);
