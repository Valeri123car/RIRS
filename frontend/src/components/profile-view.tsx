"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LinkRiotAccount } from "@/components/riot/link-account";
import { FormMessage } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import { useAuth } from "@/lib/auth";
import { platformLabel, type RiotAccount } from "@/lib/riot";

export function ProfileView() {
  const { user, loading, authRequest } = useAuth();
  const [accounts, setAccounts] = useState<RiotAccount[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [linked, setLinked] = useState<string | null>(null);

  // Povečanje sproži ponovno nalaganje seznama (npr. po uspešni povezavi).
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!user) return;
    let active = true;
    authRequest<RiotAccount[]>("/riot-accounts")
      .then((list) => {
        if (!active) return;
        setAccounts(list);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(error instanceof Error ? error.message : "Računov ni bilo mogoče naložiti.");
        }
      });
    return () => {
      active = false;
    };
  }, [user, authRequest, reloadKey]);

  if (loading) return <p className="text-on-surface-variant">Nalagam ...</p>;

  if (!user) {
    return (
      <div className="mx-auto w-full max-w-md">
        <Panel title="Profil">
          <p className="text-sm text-on-surface-variant">
            Za povezavo Riot računa se{" "}
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
        <p className="font-label text-xs tracking-widest text-secondary uppercase">Profil</p>
        <h1 className="font-headline text-2xl font-bold tracking-wide text-primary">{user.email}</h1>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Povezani Riot računi" accent="secondary">
          {loadError && <FormMessage tone="error">{loadError}</FormMessage>}
          {linked && <FormMessage tone="success">Račun {linked} je verificiran.</FormMessage>}
          {accounts?.length === 0 && (
            <p className="text-sm text-on-surface-variant">Še nimaš povezanega Riot računa.</p>
          )}
          <ul className="flex flex-col gap-2">
            {accounts?.map((account) => (
              <li
                key={account.puuid}
                className="flex items-center justify-between rounded-sm border border-outline/50 bg-surface-container px-3 py-2"
              >
                <span className="font-headline text-on-surface">
                  {account.game_name}#{account.tag_line}
                </span>
                <span className="flex items-center gap-2 font-label text-xs text-secondary uppercase">
                  {platformLabel(account.platform)} · verificiran
                </span>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Poveži Riot račun">
          <LinkRiotAccount
            onLinked={(account) => {
              setLinked(`${account.game_name}#${account.tag_line}`);
              setReloadKey((key) => key + 1);
            }}
          />
        </Panel>
      </div>
    </div>
  );
}
