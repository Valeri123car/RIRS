import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary";

const VARIANT_STYLE: Record<Variant, string> = {
  primary:
    "hex-glow-gold bg-gradient-to-r from-primary via-[#e0b04b] to-[#b38528] font-headline font-bold uppercase tracking-wider text-on-primary hover:brightness-110",
  secondary:
    "border border-outline/70 bg-surface-container font-label tracking-wide text-on-surface-variant hover:border-primary hover:text-on-surface",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

export function Button({ variant = "primary", className = "", type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-1.5 rounded-sm px-4 py-2 text-xs transition-all disabled:cursor-not-allowed disabled:opacity-50 ${VARIANT_STYLE[variant]} ${className}`}
      {...props}
    />
  );
}
