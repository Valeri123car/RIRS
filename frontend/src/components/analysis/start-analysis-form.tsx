"use client";

import { useState, type FormEvent } from "react";

import { StartError } from "@/components/analysis/start-error";
import { useStartAnalysis } from "@/components/analysis/use-start-analysis";
import { Button } from "@/components/ui/button";
import { Field, Select, TextInput } from "@/components/ui/field";
import { PLATFORMS } from "@/lib/riot";

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
      <StartError error={error} />
      <Button type="submit" disabled={pending} className="self-start">
        {pending ? "Zaganjam ..." : "Analiziraj tekmo"}
      </Button>
    </form>
  );
}
