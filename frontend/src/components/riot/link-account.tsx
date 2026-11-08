"use client";

import Image from "next/image";
import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormMessage, Select, TextInput } from "@/components/ui/field";
import { useAuth } from "@/lib/auth";
import { profileIconUrl, useDdragonVersion } from "@/lib/ddragon";
import { PLATFORMS, platformLabel, type RiotAccount, type Verification } from "@/lib/riot";

const VERIFICATIONS = "/riot-accounts/verifications";

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Prišlo je do napake.";
}

/** Preostale sekunde do roka; osveži se vsako sekundo. */
function useSecondsLeft(expiresAt: string | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!expiresAt) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [expiresAt]);

  if (!expiresAt) return 0;
  return Math.max(0, Math.ceil((new Date(expiresAt).getTime() - now) / 1000));
}

function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

type Props = { onLinked: (account: RiotAccount) => void };

/** US-01: vnos Riot ID, prikaz naključne ikone z odštevanjem in preverjanje. */
export function LinkRiotAccount({ onLinked }: Props) {
  const { authRequest } = useAuth();
  const version = useDdragonVersion();
  const [riotId, setRiotId] = useState("");
  const [platform, setPlatform] = useState<string>("eun1");
  const [verification, setVerification] = useState<Verification | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const secondsLeft = useSecondsLeft(verification?.expires_at ?? null);
  const expired = verification !== null && secondsLeft === 0;

  async function run(action: () => Promise<void>) {
    setError(null);
    setNotice(null);
    setPending(true);
    try {
      await action();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setPending(false);
    }
  }

  function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(async () => {
      setVerification(
        await authRequest<Verification>(VERIFICATIONS, {
          method: "POST",
          body: { riot_id: riotId, platform },
        }),
      );
    });
  }

  function check() {
    if (!verification) return;
    void run(async () => {
      const account = await authRequest<RiotAccount>(`${VERIFICATIONS}/${verification.id}/check`, {
        method: "POST",
      });
      setVerification(null);
      setRiotId("");
      onLinked(account);
    });
  }

  function simulate() {
    if (!verification) return;
    void run(async () => {
      await authRequest<void>(`${VERIFICATIONS}/${verification.id}/simulate-icon`, {
        method: "POST",
      });
      setNotice("Ikona je nastavljena (simulacija). Zdaj klikni Preveri.");
    });
  }

  if (!verification) {
    return (
      <form onSubmit={start} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-[1fr_8rem]">
          <Field label="Riot ID" hint="Oblika ime#oznaka, npr. Luka#EUNE.">
            <TextInput
              required
              maxLength={32}
              placeholder="ime#oznaka"
              value={riotId}
              onChange={(event) => setRiotId(event.target.value)}
            />
          </Field>
          <Field label="Regija">
            <Select value={platform} onChange={(event) => setPlatform(event.target.value)}>
              {PLATFORMS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        {error && <FormMessage tone="error">{error}</FormMessage>}
        <Button type="submit" disabled={pending} className="self-start">
          {pending ? "Iščem igralca ..." : "Začni verifikacijo"}
        </Button>
      </form>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
        <div className="hex-border hex-glow-gold shrink-0 p-1">
          <Image
            src={profileIconUrl(version, verification.icon_id)}
            alt={`Profilna ikona ${verification.icon_id}`}
            width={112}
            height={112}
          />
        </div>
        <div className="flex flex-col gap-2 text-sm text-on-surface-variant">
          <p className="font-headline text-lg text-primary">
            {verification.game_name}#{verification.tag_line}{" "}
            <span className="font-label text-xs text-muted">{platformLabel(verification.platform)}</span>
          </p>
          <p>
            V odjemalcu League of Legends nastavi to profilno ikono (privzeta ikona št.{" "}
            {verification.icon_id}), nato klikni <strong className="text-on-surface">Preveri</strong>.
          </p>
          <p className="font-mono text-2xl text-secondary" aria-live="polite">
            {expired ? "0:00" : formatTime(secondsLeft)}
          </p>
        </div>
      </div>

      {expired && (
        <FormMessage tone="error">Čas za verifikacijo je potekel. Začni znova.</FormMessage>
      )}
      {error && !expired && <FormMessage tone="error">{error}</FormMessage>}
      {notice && !expired && <FormMessage tone="success">{notice}</FormMessage>}

      <div className="flex flex-wrap gap-3">
        {!expired && (
          <Button onClick={check} disabled={pending}>
            {pending ? "Preverjam ..." : "Preveri"}
          </Button>
        )}
        {verification.simulation_available && !expired && (
          <Button variant="secondary" onClick={simulate} disabled={pending}>
            Simuliraj zamenjavo ikone
          </Button>
        )}
        <Button
          variant="secondary"
          onClick={() => {
            setVerification(null);
            setError(null);
            setNotice(null);
          }}
        >
          {expired ? "Začni znova" : "Prekliči"}
        </Button>
      </div>
      {verification.simulation_available && (
        <p className="text-xs text-muted">
          Način brez Riot ključa (fixtures): zamenjavo ikone lahko simuliraš.
        </p>
      )}
    </div>
  );
}
