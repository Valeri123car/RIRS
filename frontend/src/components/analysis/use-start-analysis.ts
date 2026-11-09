"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import type { Analysis } from "@/lib/analysis";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type StartError = {
  message: string;
  /** true pri dnevni omejitvi za goste (429): prikaži povabilo k registraciji. */
  limited: boolean;
};

/** Zažene analizo (POST /analyses) in odpre njeno stran. Prijavljen uporabnik pošlje žeton. */
export function useStartAnalysis() {
  const router = useRouter();
  const { authRequest } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<StartError | null>(null);

  // Next ob vrnitvi (»nazaj«) ohrani stanje strani, zato bi gumb ostal v »Zaganjam ...«.
  // Ob vsaki spremembi poti (odhod na analizo in vrnitev) se zato ponastavi.
  const pathname = usePathname();
  const [seenPath, setSeenPath] = useState(pathname);
  if (seenPath !== pathname) {
    setSeenPath(pathname);
    setPending(false);
  }

  async function start(riotId: string, platform: string) {
    setPending(true);
    setError(null);
    try {
      const analysis = await authRequest<Analysis>("/analyses", {
        method: "POST",
        body: { riot_id: riotId, platform },
      });
      router.push(`/analiza/${analysis.id}`);
    } catch (err) {
      setError({
        message: err instanceof Error ? err.message : "Analize ni bilo mogoče zagnati.",
        limited: err instanceof ApiError && err.status === 429,
      });
      setPending(false);
    }
  }

  return { start, pending, error };
}
