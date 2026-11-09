"use client";

import Image from "next/image";
import { useState } from "react";

import { Panel } from "@/components/ui/panel";
import { FormMessage } from "@/components/ui/field";
import {
  championIconUrl,
  fetchMatchup,
  type Matchup,
  type Participant,
  type PowerPoint,
  type PowerWindow,
} from "@/lib/analysis";

const ROLE_LABEL: Record<NonNullable<Matchup["role"]>, string> = {
  TOP: "Zgornja linija",
  JUNGLE: "Džungla",
  MIDDLE: "Srednja linija",
  BOTTOM: "Spodnja linija",
  UTILITY: "Podpora",
};

const WINDOW_STYLE: Record<PowerWindow["state"], { label: string; chip: string }> = {
  advantage: { label: "Prednost", chip: "border-secondary/70 text-secondary" },
  disadvantage: { label: "Zaostanek", chip: "border-error/70 text-error" },
};

// Graf: delež moči 30–70 % (zunaj se odreže), leveli 1–18.
const CHART = { width: 720, height: 240, left: 36, right: 12, top: 14, bottom: 30, min: 30, max: 70 };
const R_LEVELS = [6, 11, 16];

function x(level: number): number {
  const span = CHART.width - CHART.left - CHART.right;
  return CHART.left + ((level - 1) / 17) * span;
}

function y(share: number): number {
  const clamped = Math.min(CHART.max, Math.max(CHART.min, share));
  const span = CHART.height - CHART.top - CHART.bottom;
  return CHART.top + ((CHART.max - clamped) / (CHART.max - CHART.min)) * span;
}

function path(levels: PowerPoint[], key: "you" | "enemy"): string {
  return levels.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.level).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ");
}

function levelRange(window: PowerWindow): string {
  return window.from === window.to ? `Level ${window.from}` : `Level ${window.from}–${window.to}`;
}

function PowerChart({ card }: { card: Matchup }) {
  const half = (x(2) - x(1)) / 2;
  const summary = card.windows.length
    ? card.windows
        .map((w) => `${levelRange(w)}: ${WINDOW_STYLE[w.state].label.toLowerCase()}`)
        .join("; ")
    : "Šampiona sta izenačena na vseh levelih.";

  return (
    <figure className="flex flex-col gap-2">
      <svg
        viewBox={`0 0 ${CHART.width} ${CHART.height}`}
        className="h-auto w-full"
        role="img"
        aria-label={`Časovnica moči od levela 1 do 18. ${summary}`}
      >
        {card.levels.map((p) =>
          p.state === "even" ? null : (
            <rect
              key={p.level}
              x={x(p.level) - half}
              y={CHART.top}
              width={half * 2}
              height={CHART.height - CHART.top - CHART.bottom}
              className={p.state === "advantage" ? "fill-secondary/15" : "fill-error/15"}
            />
          ),
        )}
        {[40, 50, 60].map((share) => (
          <g key={share}>
            <line
              x1={CHART.left}
              x2={CHART.width - CHART.right}
              y1={y(share)}
              y2={y(share)}
              className={share === 50 ? "stroke-outline" : "stroke-outline/30"}
              strokeDasharray={share === 50 ? undefined : "4 6"}
            />
            <text x={CHART.left - 6} y={y(share) + 4} textAnchor="end" className="fill-muted font-mono text-[11px]">
              {share}
            </text>
          </g>
        ))}
        {R_LEVELS.map((level) => (
          <text key={level} x={x(level)} y={CHART.top - 3} textAnchor="middle" className="fill-primary/80 font-mono text-[10px]">
            R
          </text>
        ))}
        <path d={path(card.levels, "enemy")} fill="none" strokeWidth={2} strokeDasharray="6 5" className="stroke-error" />
        <path d={path(card.levels, "you")} fill="none" strokeWidth={2.5} className="stroke-primary" />
        {card.levels.map((p) => (
          <text
            key={p.level}
            x={x(p.level)}
            y={CHART.height - 10}
            textAnchor="middle"
            className="fill-on-surface-variant font-mono text-[11px]"
          >
            {p.level}
          </text>
        ))}
      </svg>
      <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-on-surface-variant">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-5 bg-primary" /> {card.champion.name}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-5 border-t-2 border-dashed border-error" /> {card.opponent?.name}
        </span>
        <span>Delež moči v % (50 = izenačeno), R = rang ultimata</span>
      </figcaption>
    </figure>
  );
}

type IconProps = { slug?: string | null; name: string; version: string; size?: number };

function ChampionIcon({ slug, name, version, size = 40 }: IconProps) {
  return slug && version ? (
    <Image src={championIconUrl(version, slug)} alt={name} width={size} height={size} className="border border-outline/60" />
  ) : (
    <span className="flex items-center justify-center border border-outline/60 bg-surface-container font-mono text-xs text-muted" style={{ width: size, height: size }}>
      ?
    </span>
  );
}

type MatchupPanelProps = {
  analysisId: string;
  matchup: Matchup;
  participants: Participant[];
  version: string;
};

/** US-05: časovnica moči proti linijskemu nasprotniku, nevarne sposobnosti in nasveti. */
export function MatchupPanel({ analysisId, matchup, participants, version }: MatchupPanelProps) {
  const [card, setCard] = useState(matchup);
  const [pending, setPending] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const slug = (id: number) => participants.find((p) => p.champion_id === id)?.champion_slug;

  async function choose(opponentId: number) {
    setPending(opponentId);
    setError(null);
    try {
      setCard(await fetchMatchup(analysisId, opponentId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Matchupa ni bilo mogoče naložiti.");
    } finally {
      setPending(null);
    }
  }

  const role = card.role ? ROLE_LABEL[card.role] : null;

  return (
    <Panel
      title="Matchup kartica"
      action={
        role && (
          <span className="rounded-sm border border-outline/60 px-2 py-0.5 font-label text-[10px] tracking-widest text-on-surface-variant uppercase">
            {role}
          </span>
        )
      }
    >
      <div className="flex flex-wrap items-center gap-3">
        <ChampionIcon slug={slug(card.champion.id)} name={card.champion.name} version={version} />
        <span className="font-headline text-base font-bold tracking-wide text-primary">{card.champion.name}</span>
        <span className="font-label text-xs tracking-widest text-muted uppercase">proti</span>
        {card.opponent ? (
          <>
            <ChampionIcon slug={slug(card.opponent.id)} name={card.opponent.name} version={version} />
            <span className="font-headline text-base font-bold tracking-wide text-error">{card.opponent.name}</span>
            <span className="text-xs text-muted">
              {card.opponent_source === "auto"
                ? `samodejno določen${card.confidence ? ` (zaupanje ${Math.round(card.confidence * 100)} %)` : ""}`
                : "izbral si sam"}
            </span>
          </>
        ) : (
          <span className="text-sm text-on-surface-variant">?</span>
        )}
      </div>

      <section className="flex flex-col gap-2">
        <h3 className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
          {card.opponent ? "Zamenjaj nasprotnika" : "Izberi linijskega nasprotnika"}
        </h3>
        {!card.opponent && (
          <p className="text-sm text-on-surface-variant">
            Linijskega nasprotnika ni bilo mogoče zanesljivo določiti. Izberi ga med nasprotnimi šampioni.
          </p>
        )}
        <div className="flex flex-wrap gap-2" role="group" aria-label="Nasprotni šampioni">
          {card.candidates.map((candidate) => {
            const active = candidate.id === card.opponent?.id;
            return (
              <button
                key={candidate.id}
                type="button"
                disabled={pending !== null}
                aria-pressed={active}
                onClick={() => void choose(candidate.id)}
                className={`flex items-center gap-2 rounded-sm border px-2 py-1.5 text-sm transition-colors disabled:opacity-60 ${
                  active
                    ? "border-error bg-error/10 text-on-surface"
                    : "border-outline/50 bg-surface-container-low text-on-surface-variant hover:border-primary hover:text-on-surface"
                }`}
              >
                <ChampionIcon slug={slug(candidate.id)} name={candidate.name} version={version} size={28} />
                {pending === candidate.id ? "Nalagam ..." : candidate.name}
              </button>
            );
          })}
        </div>
        {error && <FormMessage tone="error">{error}</FormMessage>}
      </section>

      {card.opponent && card.levels.length === 0 && (
        <p className="text-sm text-muted">Za ta par šampionov še ni podatkov o statistikah (uvoz Data Dragon).</p>
      )}

      {card.levels.length > 0 && (
        <>
          <PowerChart card={card} />

          {card.windows.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {card.windows.map((w) => (
                <li
                  key={`${w.from}-${w.state}`}
                  className={`rounded-sm border px-2 py-1 text-xs ${WINDOW_STYLE[w.state].chip}`}
                >
                  <span className="font-mono">{levelRange(w)}</span> · {WINDOW_STYLE[w.state].label}
                  <span className="text-on-surface-variant"> – {w.reason}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            <section className="flex flex-col gap-2">
              <h3 className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
                Nevarne sposobnosti – {card.opponent?.name}
              </h3>
              <ul className="flex flex-col gap-2">
                {card.dangerous_abilities.map((ability) => (
                  <li
                    key={ability.key}
                    className="flex items-start gap-3 rounded-sm border border-outline/40 bg-surface-container-low px-3 py-2"
                  >
                    <span className="flex size-7 shrink-0 items-center justify-center border border-error/70 font-mono text-sm text-error">
                      {ability.key}
                    </span>
                    <span className="flex min-w-0 flex-col">
                      <span className="font-headline text-sm font-bold tracking-wide text-on-surface">
                        {ability.name}
                      </span>
                      <span className="text-xs text-on-surface-variant">
                        {ability.reason}
                        {ability.cooldown ? ` · obnova ${ability.cooldown} s` : ""}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="flex flex-col gap-2">
              <h3 className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
                Nasveti za linijsko fazo
              </h3>
              <ol className="flex flex-col gap-2">
                {card.tips.map((tip, index) => (
                  <li key={tip} className="flex gap-2 text-sm text-on-surface">
                    <span className="font-mono text-primary">{index + 1}.</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ol>
            </section>
          </div>
        </>
      )}
    </Panel>
  );
}
