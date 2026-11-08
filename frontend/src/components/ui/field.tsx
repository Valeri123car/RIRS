import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

const CONTROL =
  "w-full rounded-sm border border-outline/70 bg-surface-container px-3 py-2 text-sm text-on-surface shadow-[inset_0_1px_4px_rgb(0_0_0/0.6)] outline-none transition-colors placeholder:text-muted/70 focus:border-primary";

type FieldProps = { label: string; hint?: ReactNode; children: ReactNode };

/** Oznaka nad vnosnim poljem z neobvezno pomočjo pod njim. */
export function Field({ label, hint, children }: FieldProps) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
        {label}
      </span>
      {children}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function TextInput({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${CONTROL} ${className}`} {...props} />;
}

export function Select({ className = "", ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`${CONTROL} ${className}`} {...props} />;
}

type MessageProps = { tone: "error" | "success"; children: ReactNode };

/** Sporočilo o napaki ali uspehu (aria-live, da ga bralniki zaslona preberejo). */
export function FormMessage({ tone, children }: MessageProps) {
  const style =
    tone === "error"
      ? "border-error/60 bg-error/10 text-error"
      : "border-secondary/60 bg-secondary/10 text-secondary";
  return (
    <p role={tone === "error" ? "alert" : "status"} className={`rounded-sm border px-3 py-2 text-sm ${style}`}>
      {children}
    </p>
  );
}
