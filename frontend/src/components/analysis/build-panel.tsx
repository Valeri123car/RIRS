"use client";

import Image from "next/image";
import { useState } from "react";

import { Panel } from "@/components/ui/panel";
import {
  fetchRecommendation,
  itemIconUrl,
  type BuildVariant,
  type GameState,
  type Recommendation,
} from "@/lib/analysis";

const SKILLS = ["Q", "W", "E", "R"] as const;

const GAME_STATES: { key: GameState; label: string }[] = [
  { key: "ahead", label: "Gre mi dobro" },
  { key: "even", label: "Izenačeno" },
  { key: "behind", label: "Gre mi slabo" },
];

function SectionTitle({ children }: { children: string }) {
  return (
    <h3 className="font-label text-xs tracking-widest text-on-surface-variant uppercase">{children}</h3>
  );
}

function Items({ variant, version }: { variant: BuildVariant; version: string }) {
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>Predmeti po vrstnem redu</SectionTitle>
      <ol className="flex flex-col gap-2">
        {variant.items.map((item, index) => (
          <li
            key={`${item.id}-${index}`}
            className="flex items-start gap-3 rounded-sm border border-outline/40 bg-surface-container-low px-3 py-2"
          >
            <span className="mt-1 w-5 shrink-0 font-mono text-sm text-primary">{index + 1}.</span>
            <Image
              src={itemIconUrl(version, item.id)}
              alt=""
              width={40}
              height={40}
              className="shrink-0 border border-outline/60"
            />
            <span className="flex min-w-0 flex-col">
              <span className="font-headline text-sm font-bold tracking-wide text-on-surface">
                {item.name}
              </span>
              <span className="text-sm text-on-surface-variant">{item.reason}</span>
              {item.typical_minute !== undefined && (
                <span className="font-mono text-xs text-muted">
                  Običajno kupljen okoli {item.typical_minute}. minute
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Runes({ variant }: { variant: BuildVariant }) {
  const { runes } = variant;
  const minor = runes.primary_perks?.slice(1);
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>Rune</SectionTitle>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted">Primarno drevo</dt>
        <dd className="text-on-surface">{runes.primary_tree}</dd>
        <dt className="text-muted">Ključna runa</dt>
        <dd className="font-bold text-primary">{runes.keystone}</dd>
        {minor && minor.length > 0 && (
          <>
            <dt className="text-muted">Manjše rune</dt>
            <dd className="text-on-surface">{minor.join(", ")}</dd>
          </>
        )}
        <dt className="text-muted">Sekundarno drevo</dt>
        <dd className="text-on-surface">{runes.secondary_tree}</dd>
        {runes.secondary_perks && runes.secondary_perks.length > 0 && (
          <>
            <dt className="text-muted">Sekundarne rune</dt>
            <dd className="text-on-surface">{runes.secondary_perks.join(", ")}</dd>
          </>
        )}
        {runes.shards && runes.shards.length > 0 && (
          <>
            <dt className="text-muted">Statistične rune</dt>
            <dd className="text-on-surface">{runes.shards.join(", ")}</dd>
          </>
        )}
      </dl>
      {runes.pick_rate !== undefined && runes.win_rate !== undefined && (
        <p className="text-xs text-on-surface-variant">
          Ta stran run: {runes.pick_rate} % iger tega šampiona, {runes.win_rate} % zmag.
        </p>
      )}
    </section>
  );
}

function StartItems({ variant, version }: { variant: BuildVariant; version: string }) {
  const start = variant.start_items;
  if (!start || start.items.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>Začetni predmeti</SectionTitle>
      <ul className="flex flex-wrap gap-2">
        {start.items.map((item, index) => (
          <li key={`${item.id}-${index}`} title={item.name}>
            <Image
              src={itemIconUrl(version, item.id)}
              alt={item.name}
              width={32}
              height={32}
              className="border border-outline/60"
            />
          </li>
        ))}
      </ul>
      <p className="text-xs text-on-surface-variant">
        Najpogostejši začetni nakup ({start.games} iger, {Math.round((100 * start.wins) / start.games)} %
        zmag).
      </p>
    </section>
  );
}

function SkillOrder({ variant }: { variant: BuildVariant }) {
  const { priority, levels } = variant.skill_order;
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>Vrstni red sposobnosti</SectionTitle>
      <p className="font-mono text-sm text-on-surface">Prioriteta: {priority.join(" > ")}</p>
      <div className="overflow-x-auto pb-1">
        <table className="border-separate border-spacing-0.5 font-mono text-xs">
          <thead>
            <tr>
              <th className="sr-only">Sposobnost</th>
              {levels.map((_, level) => (
                <th key={level} scope="col" className="w-6 min-w-6 font-normal text-muted">
                  {level + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SKILLS.map((skill) => (
              <tr key={skill}>
                <th scope="row" className="pr-1 text-left font-bold text-primary">
                  {skill}
                </th>
                {levels.map((chosen, level) => (
                  <td
                    key={level}
                    className={`h-6 min-w-6 border text-center ${
                      chosen === skill
                        ? "border-primary bg-primary/25 text-primary"
                        : "border-outline/30 bg-surface-container-low text-transparent"
                    }`}
                  >
                    {chosen === skill ? skill : "·"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/** US-04: variante builda in run z oznako vira (pravila ali model). */
export function BuildPanel({
  analysisId,
  recommendation: initial,
  version,
}: {
  analysisId: string;
  recommendation: Recommendation | null;
  version: string;
}) {
  const [selected, setSelected] = useState(0);
  const [recommendation, setRecommendation] = useState(initial);
  const [state, setState] = useState<GameState>("even");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function chooseState(next: GameState) {
    if (next === state || pending) return;
    setPending(true);
    setError(null);
    try {
      setRecommendation(await fetchRecommendation(analysisId, next));
      setState(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Priporočila ni bilo mogoče naložiti.");
    } finally {
      setPending(false);
    }
  }

  if (!recommendation || recommendation.variants.length === 0) {
    return (
      <Panel title="Priporočilo builda" accent="secondary">
        <p className="text-sm text-muted">
          Za tega šampiona priporočila builda in run trenutno ni (šampiona še ni v bazi znanja).
        </p>
      </Panel>
    );
  }

  const variants = recommendation.variants;
  const variant = variants[Math.min(selected, variants.length - 1)];

  return (
    <Panel title={`Priporočilo builda · ${recommendation.champion.name}`} accent="secondary">
      <p className="self-start rounded-sm border border-secondary/60 bg-secondary/10 px-2 py-0.5 font-label text-[11px] tracking-widest text-secondary uppercase">
        {recommendation.label}
      </p>

      <div className="flex flex-col gap-2">
        <SectionTitle>Kako ti gre v igri?</SectionTitle>
        <div role="group" aria-label="Stanje igre" className="flex flex-wrap gap-2">
          {GAME_STATES.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              aria-pressed={state === key}
              disabled={pending}
              onClick={() => chooseState(key)}
              className={`rounded-sm border px-4 py-1.5 font-label text-sm tracking-wide transition-colors disabled:opacity-60 ${
                state === key
                  ? "border-secondary bg-secondary/15 text-secondary"
                  : "border-outline/50 text-on-surface-variant hover:border-secondary/60"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {error && (
          <p role="alert" className="text-sm text-error">
            {error}
          </p>
        )}
      </div>

      <div role="tablist" aria-label="Variante builda" className="flex flex-wrap gap-2">
        {variants.map((v, index) => (
          <button
            key={v.key}
            type="button"
            role="tab"
            id={`variant-tab-${v.key}`}
            aria-selected={variant.key === v.key}
            aria-controls="variant-panel"
            onClick={() => setSelected(index)}
            className={`rounded-sm border px-4 py-1.5 font-label text-sm tracking-wide transition-colors ${
              variant.key === v.key
                ? "hex-glow-gold border-primary bg-primary/15 text-primary"
                : "border-outline/50 text-on-surface-variant hover:border-primary/60"
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      <div
        id="variant-panel"
        role="tabpanel"
        aria-labelledby={`variant-tab-${variant.key}`}
        className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]"
      >
        <Items variant={variant} version={version} />
        <div className="flex min-w-0 flex-col gap-6">
          <StartItems variant={variant} version={version} />
          <Runes variant={variant} />
          <SkillOrder variant={variant} />
        </div>
      </div>
    </Panel>
  );
}
