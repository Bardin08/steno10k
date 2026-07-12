export interface Provider {
  name: string;
  baseUrl: string;
}

export const BUILTIN_PROVIDERS: Provider[] = [
  { name: "OpenAI", baseUrl: "https://api.openai.com/v1" },
  {
    name: "Gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
  },
  { name: "Ollama (local)", baseUrl: "http://localhost:11434/v1" },
];

const KEY = "steno10k.llm.customProviders";

export function loadCustomProviders(): Provider[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]") as Provider[];
  } catch {
    return [];
  }
}

export function addCustomProvider(p: Provider): Provider[] {
  const next = [...loadCustomProviders().filter((x) => x.name !== p.name), p];
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}

export function allProviders(): Provider[] {
  return [...BUILTIN_PROVIDERS, ...loadCustomProviders()];
}

export function providerBaseUrl(name: string): string | undefined {
  return allProviders().find((p) => p.name === name)?.baseUrl;
}
