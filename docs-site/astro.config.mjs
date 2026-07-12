import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

export default defineConfig({
  site: "https://bardin08.github.io",
  base: "/steno10k/docs",
  trailingSlash: "always",
  integrations: [mdx()],
});
