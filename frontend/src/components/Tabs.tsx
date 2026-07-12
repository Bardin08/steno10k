import * as RadixTabs from "@radix-ui/react-tabs";
import { type ComponentProps } from "react";
import { cn } from "../lib/cn";

export const Tabs = RadixTabs.Root;

export function TabsList({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.List>) {
  return (
    <RadixTabs.List
      className={cn("flex gap-6 border-b border-hairline", className)}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.Trigger>) {
  return (
    <RadixTabs.Trigger
      className={cn(
        "-mb-px border-b-2 border-transparent py-2 text-sm text-ink-soft",
        "transition-colors duration-[var(--dur-micro)] ease-editorial hover:text-ink",
        "data-[state=active]:border-accent data-[state=active]:text-ink",
        "focus-visible:outline-none focus-visible:text-ink focus-visible:border-accent",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.Content>) {
  return <RadixTabs.Content className={cn("pt-5", className)} {...props} />;
}
