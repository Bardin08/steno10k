import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./Tabs";

test("shows the active tab's panel and switches on click", () => {
  render(
    <Tabs defaultValue="raw">
      <TabsList>
        <TabsTrigger value="raw">Raw</TabsTrigger>
        <TabsTrigger value="summary">Summary</TabsTrigger>
      </TabsList>
      <TabsContent value="raw">raw body</TabsContent>
      <TabsContent value="summary">summary body</TabsContent>
    </Tabs>,
  );
  expect(screen.getByText("raw body")).toBeInTheDocument();
  // Radix Tabs activates on mousedown/focus (automatic mode), not a bare
  // click — jsdom's Element.click() dispatches neither, so drive the real
  // activation event.
  fireEvent.mouseDown(screen.getByRole("tab", { name: "Summary" }));
  expect(screen.getByText("summary body")).toBeInTheDocument();
});

test("trigger has no focus ring class", () => {
  render(
    <Tabs defaultValue="a">
      <TabsList>
        <TabsTrigger value="a">A</TabsTrigger>
      </TabsList>
      <TabsContent value="a">b</TabsContent>
    </Tabs>,
  );
  const t = screen.getByRole("tab", { name: "A" });
  expect(t.className).not.toMatch(/ring-2/);
  expect(t.className).not.toMatch(/ring-accent/);
});
