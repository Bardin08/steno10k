export interface NavItem {
  title: string;
  slug: string; // "" = docs home
}

export const nav: NavItem[] = [
  { title: "Overview", slug: "" },
  { title: "Getting started", slug: "getting-started" },
  { title: "Configuration", slug: "configuration" },
  { title: "Configuration reference", slug: "configuration-reference" },
  { title: "Pipeline & artifacts", slug: "pipeline" },
  { title: "CLI", slug: "cli" },
  { title: "API reference", slug: "api" },
  { title: "Self-hosting", slug: "self-hosting" },
  { title: "Troubleshooting & FAQ", slug: "troubleshooting" },
];
