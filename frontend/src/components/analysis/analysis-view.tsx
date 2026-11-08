"use client";

import Image from "next/image";
import Link from "next/link";

import { BuildPanel } from "@/components/analysis/build-panel";
import { EnemyCompPanel } from "@/components/analysis/enemy-comp-panel";
import { StartError } from "@/components/analysis/start-error";
import { useStartAnalysis } from "@/components/analysis/use-start-analysis";
import { Button } from "@/components/ui/button";
import { FormMessage } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import {
  ANALYSIS_STEPS,
  championIconUrl,
  stepState,
  useAnalysisProgress,
  type Analysis,
  type Participant,
  type StepState,
} from "@/lib/analysis";
import { useDdragonVersion } from "@/lib/ddragon";
import { platformLabel } from "@/lib/riot";

const STEP_STYLE: Record<StepState, { mark: string; text: string; note?: string }> = {
  done: { mark: "border-secondary bg-secondary/20 text-secondary", text: "text-on-surface" },
  active: {
    mark: "border-primary bg-primary/20 text-primary animate-pulse",
    text: "text-primary",
    note: "poteka ...",
  },
  waiting: { mark: "border-outline/70 text-muted", text: "text-muted" },
  stopped: { mark: "border-error bg-error/20 text-error", text: "text-error", note: "ustavljeno" },
  unavailable: {
    mark: "border-outline/40 text-muted/60",
    text: "text-muted/70",
    note: "v pripravi",
  },
};

function Steps({ analysis }: { analysis: Analysis }) {
  return (
    <ol className="grid gap-3 sm:grid-cols-3" aria-label="Napredek analize">
      {ANALYSIS_STEPS.map((step, index) => {
        const state = stepState(step, analysis.status);
        const style = STEP_STYLE[state];
        return (
          <li key={step.status} className="flex items-center gap-3" aria-current={state === "active" ? "step" : undefined}>
            <span
              className={`flex size-8 shrink-0 rotate-45 items-center justify-center border ${style.mark}`}
            >
              <span className="-rotate-45 font-mono text-xs">{state === "done" ? "✓" : index + 1}</span>
            </span>
            <span className="flex flex-col">
              <span className={`font-label text-sm tracking-wide ${style.text}`}>{step.label}</span>
              {style.note && <span className="text-xs text-muted">{style.note}</span>}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function ParticipantRow({ participant, version }: { participant: Participant; version: string }) {
  const name = participant.champion_name ?? `Šampion #${participant.champion_id}`;
  return (
    <li
      className={`flex items-center gap-3 rounded-sm border px-3 py-2 ${
        participant.is_target
          ? "hex-glow-gold border-primary bg-primary/10"
          : "border-outline/40 bg-surface-container-low"
      }`}
    >
      {participant.champion_slug ? (
        <Image
          src={championIconUrl(version, participant.champion_slug)}
          alt={name}
          width={44}
          height={44}
          className="border border-outline/60"
        />
      ) : (
        <span className="flex size-11 items-center justify-center border border-outline/60 bg-surface-container font-mono text-xs text-muted">
          ?
        </span>
      )}
      <span className="flex min-w-0 flex-col">
        <span className="font-headline text-sm font-bold tracking-wide text-on-surface">{name}</span>
        <span className="truncate font-mono text-xs text-on-surface-variant">
          {participant.riot_id ?? "Skrit igralec"}
        </span>
      </span>
      {participant.is_target && (
        <span className="ml-auto font-label text-[10px] tracking-widest text-primary uppercase">
          Analiziran
        </span>
      )}
    </li>
  );
}

function Teams({ analysis, version }: { analysis: Analysis; version: string }) {
  const target = analysis.participants.find((p) => p.is_target);
  const allyTeam = target?.team_id ?? 100;
  const teams = [
    {
      title: "Nasprotna ekipa",
      accent: "error" as const,
      players: analysis.participants.filter((p) => p.team_id !== allyTeam),
    },
    {
      title: `Ekipa igralca ${analysis.game_name}`,
      accent: "secondary" as const,
      players: analysis.participants.filter((p) => p.team_id === allyTeam),
    },
  ];

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      {teams.map((team) => (
        <Panel key={team.title} title={team.title} accent={team.accent}>
          <ul className="flex flex-col gap-2">
            {team.players.map((participant) => (
              <ParticipantRow key={participant.puuid} participant={participant} version={version} />
            ))}
          </ul>
        </Panel>
      ))}
    </div>
  );
}

function RetryButton({ analysis }: { analysis: Analysis }) {
  const { start, pending, error } = useStartAnalysis();
  return (
    <div className="flex flex-col gap-3">
      <StartError error={error} />
      <Button
        className="self-start"
        disabled={pending}
        onClick={() => void start(`${analysis.game_name}#${analysis.tag_line}`, analysis.platform)}
      >
        {pending ? "Zaganjam ..." : "Poskusi znova"}
      </Button>
    </div>
  );
}

/** US-02: napredek analize v živo (SSE) in 10 udeležencev aktivne tekme. */
export function AnalysisView({ id }: { id: string }) {
  const { analysis, error } = useAnalysisProgress(id);
  const version = useDdragonVersion();

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <FormMessage tone="error">{error}</FormMessage>
        <Link href="/" className="text-sm text-primary underline underline-offset-2">
          Nova analiza
        </Link>
      </div>
    );
  }

  if (!analysis) {
    return <p className="text-on-surface-variant">Povezujem se z analizo ...</p>;
  }

  const stopped = analysis.status === "not_in_game" || analysis.status === "failed";

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="font-label text-xs tracking-widest text-secondary uppercase">
          Analiza aktivne tekme · {platformLabel(analysis.platform)}
        </p>
        <h1 className="font-headline text-2xl font-bold tracking-wide text-primary sm:text-3xl">
          {analysis.game_name}
          <span className="text-on-surface-variant">#{analysis.tag_line}</span>
        </h1>
      </header>

      <Panel title="Napredek">
        <div aria-live="polite">
          <Steps analysis={analysis} />
        </div>
      </Panel>

      {stopped && (
        <div className="flex flex-col gap-3">
          <FormMessage tone="error">{analysis.error ?? "Analiza ni uspela."}</FormMessage>
          <RetryButton analysis={analysis} />
        </div>
      )}

      {analysis.enemy_comp && <EnemyCompPanel comp={analysis.enemy_comp} />}

      {analysis.status === "completed" && (
        <BuildPanel recommendation={analysis.recommendation ?? null} version={version} />
      )}

      {analysis.participants.length > 0 && <Teams analysis={analysis} version={version} />}

      {analysis.status === "completed" && (
        <p className="text-sm text-muted">
          <Link href="/" className="text-primary underline underline-offset-2">
            Nova analiza
          </Link>
        </p>
      )}
    </div>
  );
}
