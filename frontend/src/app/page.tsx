const FEATURES = [
  {
    title: "Profil nasprotne sestave",
    description: "Delež fizične in magične škode ter glavne grožnje nasprotne ekipe.",
  },
  {
    title: "Build in rune",
    description: "Dve do tri variante builda, prilagojene nasprotnikom, z razlogom za vsak predmet.",
  },
  {
    title: "Matchup kartica",
    description: "Na katerih levelih je tvoj linijski nasprotnik močnejši in česa se izogibati.",
  },
] as const;

export default function HomePage() {
  return (
    <div className="flex flex-col gap-10">
      <section className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Analiziraj svojo tekmo, preden se začne.
        </h1>
        <p className="max-w-2xl text-muted">
          RIFT_HELP iz aktivne tekme in zgodovine nasprotnikov pripravi build, rune in načrt za
          linijsko fazo.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {FEATURES.map((feature) => (
          <article key={feature.title} className="rounded-lg border border-border bg-surface p-5">
            <h2 className="font-medium">{feature.title}</h2>
            <p className="mt-2 text-sm text-muted">{feature.description}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
