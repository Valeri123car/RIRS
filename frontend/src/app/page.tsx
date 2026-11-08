import { StartAnalysisForm } from "@/components/analysis/start-analysis-form";
import { Panel } from "@/components/ui/panel";

const FEATURES = [
  {
    title: "Profil nasprotne sestave",
    accent: "error",
    description: "Delež fizične in magične škode ter glavne grožnje nasprotne ekipe.",
  },
  {
    title: "Build in rune",
    accent: "primary",
    description: "Dve do tri variante builda, prilagojene nasprotnikom, z razlogom za vsak predmet.",
  },
  {
    title: "Matchup kartica",
    accent: "secondary",
    description: "Na katerih levelih je tvoj linijski nasprotnik močnejši in česa se izogibati.",
  },
] as const;

export default function HomePage() {
  return (
    <div className="flex flex-col gap-10">
      <section className="flex flex-col gap-3">
        <p className="font-label text-xs tracking-widest text-secondary uppercase">
          Analiza aktivne tekme
        </p>
        <h1 className="font-headline text-3xl font-bold tracking-wide text-primary sm:text-4xl">
          Analiziraj svojo tekmo, preden se začne.
        </h1>
        <p className="max-w-2xl text-on-surface-variant">
          RIFT_HELP iz aktivne tekme in zgodovine nasprotnikov pripravi build, rune in načrt za
          linijsko fazo.
        </p>
      </section>

      <Panel title="Nova analiza" className="max-w-2xl">
        <StartAnalysisForm />
        <p className="text-xs text-muted">
          Brez prijave lahko na dan zaženeš 3 analize. Igralec mora biti v aktivni tekmi.
        </p>
      </Panel>

      <div className="grid gap-5 md:grid-cols-3">
        {FEATURES.map((feature) => (
          <Panel key={feature.title} title={feature.title} accent={feature.accent}>
            <p className="text-sm text-on-surface-variant">{feature.description}</p>
          </Panel>
        ))}
      </div>
    </div>
  );
}
