"use client";

import Image from "next/image";

import { Panel } from "@/components/ui/panel";
import {
  championIconUrl,
  type Participant,
  type StyleIndicatorKey,
  type StyleProfile,
} from "@/lib/analysis";

const INDICATORS: { key: StyleIndicatorKey; label: string; hint: string }[] = [
  { key: "aggression", label: "Agresivnost", hint: "samostojni kili in zgodnji takedowni" },
  { key: "roaming", label: "Roaming", hint: "kili in takedowni v drugih linijah" },
  { key: "farming", label: "Farmanje", hint: "CS na minuto" },
  { key: "early_deaths", label: "Zgodnje smrti", hint: "smrti pred 14. minuto" },
  { key: "vision", label: "Vizija", hint: "vision score na minuto" },
];

const ROLE_LABEL: Record<NonNullable<StyleProfile["role"]>, string> = {
  TOP: "Zgornja linija",
  JUNGLE: "Džungla",
  MIDDLE: "Srednja linija",
  BOTTOM: "Spodnja linija",
  UTILITY: "Podpora",
};

// Odstopanje je prikazano do ±100 % mediane; več se odreže, številka pa ostane točna.
const BAR_LIMIT = 1;
// Pod tem odstopanjem je igralec »povprečen« za to vlogo.
const NEUTRAL = 0.1;

function percent(value: number): string {
  const rounded = Math.round(value * 100);
  return `${rounded > 0 ? "+" : ""}${rounded} %`;
}

function Indicator({
  label,
  hint,
  value,
  deviation,
}: {
  label: string;
  hint: string;
  value: number;
  deviation: number;
}) {
  const width = (Math.min(BAR_LIMIT, Math.abs(deviation)) / BAR_LIMIT) * 50;
  const positive = deviation >= 0;
  const neutral = Math.abs(deviation) < NEUTRAL;
  return (
    <li className="flex flex-col gap-1" title={hint}>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="text-on-surface">{label}</span>
        <span className="font-mono text-xs">
          <span className="text-on-surface-variant">{value.toFixed(1)} · </span>
          <span className={neutral ? "text-on-surface-variant" : "text-primary"}>
            {percent(deviation)}
          </span>
        </span>
      </div>
      <span
        className="relative h-1.5 rounded-sm bg-surface-container-highest"
        role="img"
        aria-label={`${label}: ${percent(deviation)} glede na mediano vloge`}
      >
        <span className="absolute inset-y-0 left-1/2 w-px bg-outline" />
        <span
          className={`absolute inset-y-0 ${positive ? "left-1/2" : "right-1/2"} ${
            neutral ? "bg-muted" : positive ? "bg-primary" : "bg-tertiary"
          }`}
          style={{ width: `${width}%` }}
        />
      </span>
    </li>
  );
}

function OpponentCard({
  participant,
  profile,
  version,
}: {
  participant: Participant;
  profile: StyleProfile;
  version: string;
}) {
  const name = participant.champion_name ?? `Šampion #${participant.champion_id}`;
  const shown = INDICATORS.filter(({ key }) => profile.indicators[key]);
  return (
    <li className="flex flex-col gap-3 rounded-sm border border-outline/40 bg-surface-container-low p-3">
      <div className="flex items-center gap-3">
        {participant.champion_slug ? (
          <Image
            src={championIconUrl(version, participant.champion_slug)}
            alt={name}
            width={40}
            height={40}
            className="border border-outline/60"
          />
        ) : (
          <span className="flex size-10 items-center justify-center border border-outline/60 bg-surface-container font-mono text-xs text-muted">
            ?
          </span>
        )}
        <span className="flex min-w-0 flex-col">
          <span className="font-headline text-sm font-bold tracking-wide text-on-surface">
            {name}
          </span>
          <span className="truncate font-mono text-xs text-on-surface-variant">
            {participant.riot_id ?? "Skrit igralec"}
          </span>
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {profile.archetype && (
          <span className="rounded-sm border border-primary/70 px-2 py-0.5 font-headline text-xs font-bold tracking-wide text-primary">
            {profile.archetype.name}
            <span className="ml-1 font-mono font-normal text-on-surface-variant">
              {Math.round(profile.archetype.probability * 100)} %
            </span>
          </span>
        )}
        {profile.low_confidence && (
          <span
            className="rounded-sm border border-error/70 px-2 py-0.5 font-label text-[10px] tracking-widest text-error uppercase"
            title="Premalo tekem za zanesljiv profil"
          >
            Nizko zaupanje
          </span>
        )}
        <span className="font-label text-[10px] tracking-widest text-on-surface-variant uppercase">
          {profile.matches} / 20 tekem
          {profile.role && ` · ${ROLE_LABEL[profile.role]}`}
        </span>
      </div>

      {shown.length === 0 ? (
        <p className="text-sm text-muted">
          Za tega igralca ni bilo mogoče pridobiti rangiranih tekem.
        </p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {shown.map(({ key, label, hint }) => {
            const indicator = profile.indicators[key]!;
            return (
              <Indicator
                key={key}
                label={label}
                hint={hint}
                value={indicator.value}
                deviation={indicator.vs_median}
              />
            );
          })}
        </ul>
      )}
    </li>
  );
}

type StylePanelProps = {
  style: Record<string, StyleProfile>;
  participants: Participant[];
  version: string;
};

/** US-06: profil igralnega sloga nasprotnikov (arhetip, število tekem, kazalniki proti mediani vloge). */
export function StylePanel({ style, participants, version }: StylePanelProps) {
  const targetTeam = participants.find((p) => p.is_target)?.team_id;
  const opponents = participants.filter(
    (p) => p.team_id !== targetTeam && style[p.puuid] !== undefined,
  );
  if (opponents.length === 0) return null;

  return (
    <Panel title="Slog igre nasprotnikov" accent="secondary">
      <p className="text-xs text-muted">
        Povprečje zadnjih rangiranih tekem igralca v primerjavi z mediano iste vloge (0 % =
        povprečen igralec te vloge).
      </p>
      <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {opponents.map((participant) => (
          <OpponentCard
            key={participant.puuid}
            participant={participant}
            profile={style[participant.puuid]}
            version={version}
          />
        ))}
      </ul>
    </Panel>
  );
}
