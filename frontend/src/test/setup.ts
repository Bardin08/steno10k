import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { setReducedMotion } from "./matchMedia";
import { installLocalStorage } from "./localStorage";

installLocalStorage(); // jsdom's default origin ships a non-functional stub
setReducedMotion(false); // default: motion enabled
afterEach(() => {
  cleanup();
  setReducedMotion(false);
});
