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

export type Analysis = {
  id: string;
  status: AnalysisStatus;
  error: string | null;
  game_name: string;
  tag_line: string;
  platform: string;
  participants: Participant[];
  created_at: string;
};

export const FINAL_STATUSES: AnalysisStatus[] = ["completed", "not_in_game", "failed"];

/** Koraki analize v vrstnem redu, kot jih prikazuje stran (US-02). */
export const ANALYSIS_STEPS = [
  { status: "capturing", label: "Zajem tekme", available: true },
  // Profiliranje (US-03) in priporočila (US-04) delavec še ne izvaja.
  { status: "profiling", label: "Profiliranje nasprotnikov", available: false },
  { status: "recommending", label: "Priporočila", available: false },
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

export function championIconUrl(version: string, slug: string): string {
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${slug}.png`;
}
