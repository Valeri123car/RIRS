"use client";

import { useState, type FormEvent } from "react";

import { StartError } from "@/components/analysis/start-error";
import { useStartAnalysis } from "@/components/analysis/use-start-analysis";
import { Button } from "@/components/ui/button";
import { Field, Select, TextInput } from "@/components/ui/field";
import { PLATFORMS } from "@/lib/riot";

/** Izmišljene aktivne tekme za predstavitev (backend: app/riot/demo_client.py). */
const DEMO_RIOT_IDS = ["DemoPyke#DEMO", "DemoJinx#DEMO", "DemoAmbessa#DEMO"];

/** US-02: vnos Riot ID igralca v aktivni tekmi (deluje tudi za goste). */
export function StartAnalysisForm() {
  const { start, pending, error } = useStartAnalysis();
  const [riotId, setRiotId] = useState("");
  const [platform, setPlatform] = useState<string>("eun1");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void start(riotId.trim(), platform);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-[1fr_8rem]">
        <Field label="Riot ID igralca" hint="Oblika ime#oznaka, npr. Luka#EUNE.">
          <TextInput
            required
            maxLength={32}
            placeholder="ime#oznaka"
            autoComplete="off"
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
      <div className="flex flex-wrap items-center gap-2 text-xs text-on-surface-variant">
        <span className="font-label tracking-widest uppercase">Demo igra:</span>
        {DEMO_RIOT_IDS.map((id) => (
          <button
            key={id}
            type="button"
            onClick={() => setRiotId(id)}
            className="rounded-sm border border-outline/50 px-2 py-1 text-primary transition-colors hover:border-primary"
          >
            {id}
          </button>
        ))}
      </div>
      <StartError error={error} />
      <Button type="submit" disabled={pending} className="self-start">
        {pending ? "Zaganjam ..." : "Analiziraj tekmo"}
      </Button>
    </form>
  );
}
