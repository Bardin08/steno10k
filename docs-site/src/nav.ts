export interface NavItem {
  title: string;
  slug: string; // "" = docs home
}

export const nav: NavItem[] = [
  { title: "Overview", slug: "" },
  { title: "Getting started", slug: "getting-started" },
  { title: "Configuration", slug: "configuration" },
  { title: "CLI", slug: "cli" },
  { title: "Self-hosting", slug: "self-hosting" },
];
