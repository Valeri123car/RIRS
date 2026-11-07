"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

type Status = "preverjam" | "povezan" | "nedosegljiv";

const STATUS_STYLE: Record<Status, string> = {
  preverjam: "bg-muted",
  povezan: "bg-emerald-500",
  nedosegljiv: "bg-red-500",
};

/** Majhen indikator v glavi, ki pokaže, ali je backend dosegljiv. */
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
    <span className="flex items-center gap-2 text-xs text-muted" title="Stanje backend API">
      <span className={`size-2 rounded-full ${STATUS_STYLE[status]}`} />
      API {status}
    </span>
  );
}
