import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../lib/cn";

type Variant = "primary" | "ghost";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const base =
  "inline-flex items-center gap-2 rounded-pill px-5 py-2.5 text-sm font-medium " +
  "border transition-[transform,background-color,border-color] " +
  "duration-[var(--dur-micro)] ease-editorial active:scale-[0.97] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent " +
  "disabled:opacity-50 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-paper border-transparent hover:opacity-90",
  ghost: "bg-transparent text-ink border-hairline-strong hover:border-ink",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ variant = "primary", className, ...props }, ref) {
    return (
      <button
        ref={ref}
        data-variant={variant}
        className={cn(base, variants[variant], className)}
        {...props}
      />
    );
  },
);
