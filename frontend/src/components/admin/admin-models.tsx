"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ModelsTable } from "@/components/admin/models-table";
import { FormMessage } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import { KIND_LABEL, type ModelVersion } from "@/lib/admin";
import { useAuth } from "@/lib/auth";

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

/** Seznam verzij modelov z gumbom za aktivacijo; dostop imajo samo administratorji. */
export function AdminModels() {
  const { user, loading, authRequest } = useAuth();
  const [models, setModels] = useState<ModelVersion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  // Povečanje sproži ponovno nalaganje seznama (npr. po aktivaciji).
  const [reloadKey, setReloadKey] = useState(0);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (!isAdmin) return;
    let active = true;
    authRequest<ModelVersion[]>("/admin/models")
      .then((list) => {
        if (!active) return;
        setModels(list);
        setError(null);
      })
      .catch((e: unknown) => {
        if (active) setError(errorText(e, "Verzij ni bilo mogoče naložiti."));
      });
    return () => {
      active = false;
    };
  }, [isAdmin, authRequest, reloadKey]);

  async function activate(model: ModelVersion) {
    setBusyId(model.id);
    setNotice(null);
    try {
      await authRequest<ModelVersion>(`/admin/models/${model.id}/activate`, { method: "POST" });
      setNotice(`${KIND_LABEL[model.kind]} v${model.version} je aktivna.`);
      setError(null);
      setReloadKey((key) => key + 1);
    } catch (e) {
      // 409: model ni boljši od izhodiščnega (ali je že aktiven); sporočilo pride iz API-ja.
      setError(errorText(e, "Aktivacija ni uspela."));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <p className="text-on-surface-variant">Nalagam ...</p>;

  if (!user || !isAdmin) {
    return (
      <div className="mx-auto w-full max-w-md">
        <Panel title="Modeli" accent="error">
          <p className="text-sm text-on-surface-variant">
            {user ? (
              "Ta stran je samo za administratorje."
            ) : (
              <>
                Za dostop se{" "}
                <Link href="/prijava" className="text-primary hover:underline">
                  prijavi
                </Link>{" "}
                kot administrator.
              </>
            )}
          </p>
        </Panel>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-1">
        <p className="font-label text-xs tracking-widest text-secondary uppercase">Administracija</p>
        <h1 className="font-headline text-2xl font-bold tracking-wide text-primary">
          Verzije modelov
        </h1>
        <p className="text-sm text-on-surface-variant">
          Model buildov je mogoče aktivirati samo, če je boljši od izhodiščnega. Ob aktivaciji
          prejšnja verzija istega tipa postane umaknjena.
        </p>
      </section>

      {error && <FormMessage tone="error">{error}</FormMessage>}
      {notice && <FormMessage tone="success">{notice}</FormMessage>}

      <ModelsTable
        models={models}
        loadFailed={error !== null && models === null}
        busyId={busyId}
        onActivate={(model) => void activate(model)}
      />
    </div>
  );
}
