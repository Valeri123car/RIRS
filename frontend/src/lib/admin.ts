export type ModelKind = "build_ranker" | "playstyle_clusters";
export type ModelStatus = "trained" | "active" | "retired";

export type ModelVersion = {
  id: number;
  kind: ModelKind;
  version: number;
  patch: string;
  status: ModelStatus;
  metrics: Record<string, unknown>;
  created_at: string;
};

export const KIND_LABEL: Record<ModelKind, string> = {
  build_ranker: "Ocena buildov",
  playstyle_clusters: "Arhetipi sloga",
};

export const STATUS_LABEL: Record<ModelStatus, string> = {
  trained: "Naučen",
  active: "Aktiven",
  retired: "Umaknjen",
};

// Metrike, ki jih prikažemo v tabeli (ključ → oznaka); ostale ostanejo samo v API-ju.
const METRIC_LABEL: [string, string][] = [
  ["auc", "AUC"],
  ["baseline_auc", "Izhodišče"],
  ["contribution", "Prispevek sestave"],
  ["log_loss", "Log loss"],
  ["matches", "Tekem"],
  ["players", "Igralcev"],
  ["components", "Gruč"],
];

export function mainMetrics(metrics: Record<string, unknown>): { label: string; value: string }[] {
  return METRIC_LABEL.flatMap(([key, label]) => {
    const value = metrics[key];
    if (typeof value !== "number") return [];
    return [{ label, value: Number.isInteger(value) ? String(value) : value.toFixed(4) }];
  });
}
