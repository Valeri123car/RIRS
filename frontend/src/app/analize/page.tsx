import type { Metadata } from "next";

import { MyAnalyses } from "@/components/analysis/my-analyses";

export const metadata: Metadata = { title: "Moje analize · RIFT_HELP" };

export default function MyAnalysesPage() {
  return <MyAnalyses />;
}
