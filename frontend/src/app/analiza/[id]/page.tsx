import type { Metadata } from "next";
import { Suspense } from "react";

import { AnalysisView } from "@/components/analysis/analysis-view";

export const metadata: Metadata = { title: "Analiza tekme · RIFT_HELP" };

type Props = { params: Promise<{ id: string }> };

export default function AnalysisPage({ params }: Props) {
  // Cache Components: parametri so podatki ob zahtevi, zato je dostop do njih v Suspense.
  return (
    <Suspense fallback={<p className="text-on-surface-variant">Nalagam analizo ...</p>}>
      {params.then(({ id }) => (
        <AnalysisView id={id} />
      ))}
    </Suspense>
  );
}
