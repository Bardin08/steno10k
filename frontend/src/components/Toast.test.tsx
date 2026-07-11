import { render } from "@testing-library/react";
import { expect, test } from "vitest";
import { Toaster, toast } from "./Toast";

test("Toaster mounts and toast() is callable", () => {
  const { container } = render(<Toaster />);
  expect(container).toBeInTheDocument();
  expect(typeof toast).toBe("function");
});
