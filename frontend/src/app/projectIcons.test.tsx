import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import {
  DEFAULT_PROJECT_ICON,
  PROJECT_ICON_KEYS,
  ProjectIcon,
} from "./projectIcons";

test("exposes a curated set of icon keys including the default", () => {
  expect(PROJECT_ICON_KEYS).toContain("folder");
  expect(DEFAULT_PROJECT_ICON).toBe("folder");
});

test("renders an svg for a known icon key", () => {
  const { container } = render(<ProjectIcon icon="scales" />);
  expect(container.querySelector("svg")).toBeInTheDocument();
});

test("falls back to the default icon without throwing when icon is null", () => {
  const { container } = render(<ProjectIcon icon={null} />);
  expect(container.querySelector("svg")).toBeInTheDocument();
});

test("falls back to the default icon without throwing when icon is unknown", () => {
  const { container } = render(<ProjectIcon icon="not-a-real-key" />);
  expect(container.querySelector("svg")).toBeInTheDocument();
});
