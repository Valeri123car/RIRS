"use client";

import { useEffect, useState } from "react";

const DDRAGON = "https://ddragon.leagueoflegends.com";
/** Uporabi se, dokler zadnja verzija ni prenesena (ali če Data Dragon ni dosegljiv). */
const FALLBACK_VERSION = "16.22.1";

/** Zadnja verzija Data Dragon (za URL-je slik). */
export function useDdragonVersion(): string {
  const [version, setVersion] = useState(FALLBACK_VERSION);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${DDRAGON}/api/versions.json`, { signal: controller.signal })
      .then((response) => response.json() as Promise<string[]>)
      .then((versions) => {
        if (/^\d+\.\d+\.\d+$/.test(versions[0] ?? "")) setVersion(versions[0]);
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  return version;
}

export function profileIconUrl(version: string, iconId: number): string {
  return `${DDRAGON}/cdn/${version}/img/profileicon/${iconId}.png`;
}
