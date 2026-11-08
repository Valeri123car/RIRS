"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type Status = "preverjam" | "povezan" | "nedosegljiv";

const DOT_STYLE: Record<Status, string> = {
  preverjam: "bg-muted",
  povezan: "bg-secondary shadow-[0_0_8px_var(--color-secondary)] animate-pulse",
  nedosegljiv: "bg-error shadow-[0_0_8px_var(--color-error)]",
};

/** Indikator v glavi, ki pokaže, ali je backend dosegljiv. */
export function ApiStatus() {
  const [status, setStatus] = useState<Status>("preverjam");

  useEffect(() => {
    const controller = new AbortController();

    apiGet<{ status: string }>("/health", { signal: controller.signal })
      .then((data) => setStatus(data.status === "ok" ? "povezan" : "nedosegljiv"))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          console.error(error);
          setStatus("nedosegljiv");
        }
      });

    return () => controller.abort();
  }, []);

  return (
    <span
      title="Stanje backend API"
      className="flex items-center gap-2 rounded-sm border border-outline/60 bg-surface-container px-3.5 py-1.5 shadow-[inset_0_1px_4px_rgb(0_0_0/0.6)]"
    >
      <span className={`size-2 rounded-full ${DOT_STYLE[status]}`} />
      <span className="font-label text-xs tracking-wider text-primary uppercase">API {status}</span>
    </span>
  );
}
