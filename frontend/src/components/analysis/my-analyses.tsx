"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { FormMessage } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import type { AnalysisStatus } from "@/lib/analysis";
import { useAuth } from "@/lib/auth";
import { platformLabel } from "@/lib/riot";

type AnalysisSummary = {
  id: string;
  status: AnalysisStatus;
  game_name: string;
  tag_line: string;
  platform: string;
  champion_name: string | null;
  enemy_champions: string[];
  created_at: string;
};

const STATUS_LABEL: Record<AnalysisStatus, string> = {
  pending: "V čakalni vrsti",
  capturing: "Zajem tekme",
  profiling: "Profiliranje",
  recommending: "Priporočila",
  completed: "Končana",
  not_in_game: "Ni v tekmi",
  failed: "Neuspešna",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("sl-SI", { dateStyle: "medium", timeStyle: "short" });
}

/** Seznam analiz prijavljenega uporabnika, najnovejše najprej. */
export function MyAnalyses() {
  const { user, loading, authRequest } = useAuth();
  const [items, setItems] = useState<AnalysisSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let active = true;
    authRequest<AnalysisSummary[]>("/analyses")
      .then((list) => {
        if (active) setItems(list);
      })
      .catch((e: unknown) => {
        if (active) setError(e instanceof Error ? e.message : "Analiz ni bilo mogoče naložiti.");
      });
    return () => {
      active = false;
    };
  }, [user, authRequest]);

  if (loading) return <p className="text-on-surface-variant">Nalagam ...</p>;

  if (!user) {
    return (
      <div className="mx-auto w-full max-w-md">
        <Panel title="Moje analize">
          <p className="text-sm text-on-surface-variant">
            Za pregled analiz se{" "}
            <Link href="/prijava" className="text-primary hover:underline">
              prijavi
            </Link>
            .
          </p>
        </Panel>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-1">
        <p className="font-label text-xs tracking-widest text-secondary uppercase">Zgodovina</p>
        <h1 className="font-headline text-2xl font-bold tracking-wide text-primary">Moje analize</h1>
      </section>

      <Panel title="Analize aktivnih tekem">
        {error && <FormMessage tone="error">{error}</FormMessage>}
        {items?.length === 0 && (
          <p className="text-sm text-on-surface-variant">
            Še nimaš analiz.{" "}
            <Link href="/" className="text-primary hover:underline">
              Zaženi prvo
            </Link>
            .
          </p>
        )}
        <ul className="flex flex-col gap-2">
          {items?.map((item) => (
            <li key={item.id}>
              <Link
                href={`/analiza/${item.id}`}
                className="flex flex-col gap-1 rounded-sm border border-outline/50 bg-surface-container px-3 py-2 transition-colors hover:border-primary sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="flex flex-col">
                  <span className="font-headline text-on-surface">
                    {item.champion_name ?? "?"} · {item.game_name}#{item.tag_line}
                  </span>
                  {item.enemy_champions.length > 0 && (
                    <span className="text-xs text-on-surface-variant">
                      proti {item.enemy_champions.join(", ")}
                    </span>
                  )}
                </span>
                <span className="flex items-center gap-3 font-label text-xs text-secondary uppercase">
                  <span>{platformLabel(item.platform)}</span>
                  <span>{STATUS_LABEL[item.status]}</span>
                  <span className="text-muted">{formatDate(item.created_at)}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
