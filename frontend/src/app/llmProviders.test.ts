import { beforeEach, describe, expect, test } from "vitest";
import {
  addCustomProvider,
  allProviders,
  BUILTIN_PROVIDERS,
  loadCustomProviders,
  providerBaseUrl,
} from "./llmProviders";

beforeEach(() => {
  localStorage.clear();
});

describe("llmProviders", () => {
  test("BUILTIN_PROVIDERS includes OpenAI and Gemini", () => {
    const names = BUILTIN_PROVIDERS.map((p) => p.name);
    expect(names).toContain("OpenAI");
    expect(names).toContain("Gemini");
  });

  test("providerBaseUrl resolves the OpenAI base URL", () => {
    expect(providerBaseUrl("OpenAI")).toMatch(/openai/);
  });

  test("addCustomProvider persists to localStorage and allProviders", () => {
    expect(loadCustomProviders()).toEqual([]);

    const custom = { name: "MyProxy", baseUrl: "https://proxy.example.com/v1" };
    addCustomProvider(custom);

    expect(loadCustomProviders()).toEqual([custom]);
    expect(allProviders()).toContainEqual(custom);
    expect(providerBaseUrl("MyProxy")).toBe(custom.baseUrl);

    const stored = JSON.parse(
      localStorage.getItem("steno10k.llm.customProviders") ?? "[]",
    );
    expect(stored).toEqual([custom]);
  });

  test("addCustomProvider replaces an existing provider with the same name", () => {
    addCustomProvider({ name: "MyProxy", baseUrl: "https://a.example.com" });
    addCustomProvider({ name: "MyProxy", baseUrl: "https://b.example.com" });

    const stored = loadCustomProviders();
    expect(stored).toHaveLength(1);
    expect(stored[0].baseUrl).toBe("https://b.example.com");
  });
});
