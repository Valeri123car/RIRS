"use client";

import { useEffect, useState } from "react";

import { API_URL, apiGet } from "@/lib/api";

export type AnalysisStatus =
  | "pending"
  | "capturing"
  | "profiling"
  | "recommending"
  | "completed"
  | "not_in_game"
  | "failed";

export type Participant = {
  puuid: string;
  riot_id: string | null;
  team_id: number;
  champion_id: number;
  champion_name: string | null;
  champion_slug: string | null;
  spell1_id: number;
  spell2_id: number;
  is_target: boolean;
};

export type ThreatLevel = "medium" | "high" | "very_high";

export type Threat = {
  key: "healing" | "engage" | "burst" | "cc" | "poke" | "tank";
  label: string;
  score: number;
  level: ThreatLevel;
  /** Šampioni, ki grožnjo povzročajo (najmočnejši najprej). */
  champions: string[];
};

/** Profil nasprotne sestave (US-03). */
export type EnemyComp = {
  damage: { physical: number; magic: number };
  /** Največ 5, razvrščene po moči. */
  threats: Threat[];
  champion_count: number;
  missing_champions: number;
};

export type BuildItem = { id: number; name: string; reason: string };

export type BuildVariant = {
  key: "standard" | "safe" | "aggressive";
  label: string;
  runes: { primary_tree: string; keystone: string; secondary_tree: string };
  /** Dokončani predmeti po vrstnem redu nakupa. */
  items: BuildItem[];
  skill_order: { priority: string[]; levels: string[] };
  /** Neobvezno (model); prikaz od njega ne sme biti odvisen. */
  score?: number;
};

/** Priporočilo builda in run (US-04), iz pravil ali modela. */
export type Recommendation = {
  source: "rules" | "model";
  label: string;
  model_id: number | null;
  champion: { id: number; name: string };
  variants: BuildVariant[];
};

export type Analysis = {
  id: string;
  status: AnalysisStatus;
  error: string | null;
  game_name: string;
  tag_line: string;
  platform: string;
  participants: Participant[];
  enemy_comp: EnemyComp | null;
  recommendation?: Recommendation | null;
  created_at: string;
};

export const FINAL_STATUSES: AnalysisStatus[] = ["completed", "not_in_game", "failed"];

/** Koraki analize v vrstnem redu, kot jih prikazuje stran (US-02). */
export const ANALYSIS_STEPS = [
  { status: "capturing", label: "Zajem tekme", available: true },
  { status: "profiling", label: "Profiliranje nasprotnikov", available: true },
  { status: "recommending", label: "Priporočila", available: true },
] as const satisfies readonly { status: AnalysisStatus; label: string; available: boolean }[];

export type StepState = "done" | "active" | "waiting" | "unavailable" | "stopped";

const ORDER: AnalysisStatus[] = ["pending", "capturing", "profiling", "recommending", "completed"];

/** Stanje posameznega koraka glede na trenutno stanje analize. */
export function stepState(step: (typeof ANALYSIS_STEPS)[number], status: AnalysisStatus): StepState {
  if (!step.available) return "unavailable";
  if (status === "not_in_game" || status === "failed") {
    // Analiza se je ustavila pri zajemu.
    return step.status === "capturing" ? "stopped" : "waiting";
  }
  const current = ORDER.indexOf(status);
  const own = ORDER.indexOf(step.status);
  if (current > own) return "done";
  if (current === own) return "active";
  return "waiting";
}

type ProgressState = { analysis: Analysis | null; error: string | null };

/**
 * Napredek analize v živo prek SSE (GET /analyses/{id}/events). Tok se zapre ob končnem stanju;
 * če se prekine prej, se EventSource sam ponovno poveže.
 */
export function useAnalysisProgress(id: string): ProgressState {
  const [state, setState] = useState<ProgressState>({ analysis: null, error: null });

  useEffect(() => {
    const source = new EventSource(`${API_URL}/analyses/${encodeURIComponent(id)}/events`);

    source.addEventListener("progress", (event) => {
      const analysis = JSON.parse((event as MessageEvent<string>).data) as Analysis;
      setState({ analysis, error: null });
      if (FINAL_STATUSES.includes(analysis.status)) source.close();
    });

    source.onerror = () => {
      // Napaka ob prvi povezavi (npr. 404): EventSource se ne poveže znova, razlog preberemo z GET.
      if (source.readyState !== EventSource.CLOSED) return;
      apiGet<Analysis>(`/analyses/${encodeURIComponent(id)}`)
        .then((analysis) => setState({ analysis, error: null }))
        .catch((error: unknown) =>
          setState((previous) => ({
            ...previous,
            error: error instanceof Error ? error.message : "Analize ni bilo mogoče naložiti.",
          })),
        );
    };

    return () => source.close();
  }, [id]);

  return state;
}

export function itemIconUrl(version: string, itemId: number): string {
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/item/${itemId}.png`;
}

export function championIconUrl(version: string, slug: string): string {
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${slug}.png`;
}
