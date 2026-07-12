import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { setReducedMotion } from "./matchMedia";
import { installLocalStorage } from "./localStorage";

installLocalStorage(); // jsdom's default origin ships a non-functional stub
setReducedMotion(false); // default: motion enabled

// jsdom lacks these DOM APIs that Radix (Select/Dialog) touches on mount/interaction.
if (!("ResizeObserver" in globalThis)) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
if (!Element.prototype.scrollIntoView)
  Element.prototype.scrollIntoView = () => {};
if (!Element.prototype.hasPointerCapture)
  Element.prototype.hasPointerCapture = () => false;
if (!Element.prototype.releasePointerCapture)
  Element.prototype.releasePointerCapture = () => {};
afterEach(() => {
  cleanup();
  setReducedMotion(false);
});
