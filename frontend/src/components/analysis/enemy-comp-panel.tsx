import { Panel } from "@/components/ui/panel";
import type { EnemyComp, ThreatLevel } from "@/lib/analysis";

const LEVEL: Record<ThreatLevel, { label: string; style: string; bar: string }> = {
  very_high: { label: "Zelo visoko", style: "border-error/70 text-error", bar: "bg-error" },
  high: { label: "Visoko", style: "border-primary/70 text-primary", bar: "bg-primary" },
  medium: { label: "Zmerno", style: "border-outline/70 text-on-surface-variant", bar: "bg-muted" },
};

// Največja možna moč grožnje: 5 šampionov × ocena 3.
const MAX_SCORE = 15;

function DamageSplit({ damage }: { damage: EnemyComp["damage"] }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between font-mono text-sm">
        <span className="text-primary">Fizična {damage.physical} %</span>
        <span className="text-tertiary">Magična {damage.magic} %</span>
      </div>
      <div
        className="flex h-3 overflow-hidden rounded-sm border border-outline/60"
        role="img"
        aria-label={`Fizična škoda ${damage.physical} %, magična škoda ${damage.magic} %`}
      >
        <span className="bg-primary/80" style={{ width: `${damage.physical}%` }} />
        <span className="bg-tertiary/80" style={{ width: `${damage.magic}%` }} />
      </div>
    </div>
  );
}

/** US-03: delež škode nasprotne ekipe in največ 5 groženj, razvrščenih po moči. */
export function EnemyCompPanel({ comp }: { comp: EnemyComp }) {
  return (
    <Panel title="Profil nasprotne sestave" accent="error">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        <section className="flex flex-col gap-2">
          <h3 className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
            Delež škode
          </h3>
          <DamageSplit damage={comp.damage} />
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
            Glavne grožnje
          </h3>
          {comp.threats.length === 0 ? (
            <p className="text-sm text-muted">Nasprotna ekipa nima izrazitih groženj.</p>
          ) : (
            <ol className="flex flex-col gap-2">
              {comp.threats.map((threat) => {
                const level = LEVEL[threat.level];
                return (
                  <li
                    key={threat.key}
                    className="flex flex-col gap-1.5 rounded-sm border border-outline/40 bg-surface-container-low px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm text-on-surface">
                        <span className="font-headline font-bold tracking-wide">{threat.label}</span>
                        <span className="text-on-surface-variant">: {threat.champions.join(", ")}</span>
                      </span>
                      <span
                        className={`shrink-0 rounded-sm border px-2 py-0.5 font-label text-[10px] tracking-widest uppercase ${level.style}`}
                      >
                        {level.label}
                      </span>
                    </div>
                    <span className="h-1 overflow-hidden rounded-sm bg-surface-container-highest">
                      <span
                        className={`block h-full ${level.bar}`}
                        style={{ width: `${Math.min(100, (threat.score / MAX_SCORE) * 100)}%` }}
                      />
                    </span>
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      </div>
      {comp.missing_champions > 0 && (
        <p className="text-xs text-muted">
          {comp.missing_champions} od {comp.champion_count + comp.missing_champions} nasprotnikov ni v
          bazi znanja šampionov in ni upoštevanih.
        </p>
      )}
    </Panel>
  );
}
