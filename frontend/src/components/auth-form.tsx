"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormMessage, TextInput } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import { useAuth } from "@/lib/auth";

type Mode = "login" | "register";

const COPY = {
  login: {
    title: "Prijava",
    submit: "Prijava",
    switchText: "Še nimaš računa?",
    switchLink: { href: "/registracija", label: "Registracija" },
  },
  register: {
    title: "Registracija",
    submit: "Ustvari račun",
    switchText: "Že imaš račun?",
    switchLink: { href: "/prijava", label: "Prijava" },
  },
} as const;

export function AuthForm({ mode }: { mode: Mode }) {
  const { login, register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const copy = COPY[mode];

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await (mode === "login" ? login(email, password) : register(email, password));
      router.push("/profil");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prišlo je do napake.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-md">
      <Panel title={copy.title}>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <Field label="E-pošta">
            <TextInput
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </Field>
          <Field label="Geslo" hint={mode === "register" ? "Vsaj 8 znakov." : undefined}>
            <TextInput
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "register" ? 8 : 1}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          {error && <FormMessage tone="error">{error}</FormMessage>}
          <Button type="submit" disabled={pending}>
            {pending ? "Počakaj ..." : copy.submit}
          </Button>
          <p className="text-center text-sm text-on-surface-variant">
            {copy.switchText}{" "}
            <Link href={copy.switchLink.href} className="text-primary hover:underline">
              {copy.switchLink.label}
            </Link>
          </p>
        </form>
      </Panel>
    </div>
  );
}
