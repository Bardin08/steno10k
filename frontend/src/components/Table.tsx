import { type HTMLAttributes, type TdHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export function Table({
  className,
  ...props
}: HTMLAttributes<HTMLTableElement>) {
  return (
    <table
      className={cn("w-full border-collapse text-sm", className)}
      {...props}
    />
  );
}

export function THead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />;
}

export function TBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />;
}

export function TR({
  className,
  ...props
}: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("hover:[&>td]:bg-paper", className)} {...props} />;
}

export function TH({
  className,
  ...props
}: HTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        "border-b border-hairline-strong px-4 pb-3 text-left font-mono",
        "text-xs font-medium uppercase tracking-[0.08em] text-ink-faint",
        className,
      )}
      {...props}
    />
  );
}

interface TDProps extends TdHTMLAttributes<HTMLTableCellElement> {
  mono?: boolean;
  num?: boolean;
}

export function TD({ mono, num, className, ...props }: TDProps) {
  return (
    <td
      className={cn(
        "border-b border-hairline px-4 py-3.5",
        mono && "font-mono",
        num && "text-ink-soft",
        className,
      )}
      {...props}
    />
  );
}
