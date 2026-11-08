import type { ReactNode } from "react";

type Accent = "primary" | "secondary" | "error";

const ACCENT_DOT: Record<Accent, string> = {
  primary: "bg-primary shadow-[0_0_8px_var(--color-primary)]",
  secondary: "bg-secondary shadow-[0_0_8px_var(--color-secondary)]",
  error: "bg-error shadow-[0_0_8px_var(--color-error)]",
};

type PanelProps = {
  title?: string;
  accent?: Accent;
  /** Dodatna vsebina desno od naslova (npr. značka ali gumb). */
  action?: ReactNode;
  className?: string;
  children: ReactNode;
};

/** Osnovni vsebinski blok z zlatim robom in kotnima okraskoma. */
export function Panel({ title, accent = "primary", action, className = "", children }: PanelProps) {
  return (
    <section className={`hex-border hex-corner flex flex-col gap-3 bg-surface/95 p-4 ${className}`}>
      {title && (
        <header className="flex items-center justify-between border-b border-outline/40 pb-2">
          <div className="flex items-center gap-2">
            <span className={`size-2 rotate-45 ${ACCENT_DOT[accent]}`} />
            <h2 className="font-headline text-sm font-bold tracking-widest text-primary uppercase">
              {title}
            </h2>
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
