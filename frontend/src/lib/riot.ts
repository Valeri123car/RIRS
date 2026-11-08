/** Podprte platforme (strežniki) in imena, kot jih poznajo igralci. */
export const PLATFORMS = [
  { id: "eun1", label: "EUNE" },
  { id: "euw1", label: "EUW" },
  { id: "na1", label: "NA" },
  { id: "kr", label: "KR" },
  { id: "tr1", label: "TR" },
  { id: "ru", label: "RU" },
  { id: "br1", label: "BR" },
  { id: "la1", label: "LAN" },
  { id: "la2", label: "LAS" },
  { id: "jp1", label: "JP" },
] as const;

export type PlatformId = (typeof PLATFORMS)[number]["id"];

export function platformLabel(id: string): string {
  return PLATFORMS.find((platform) => platform.id === id)?.label ?? id.toUpperCase();
}

export type RiotAccount = {
  puuid: string;
  game_name: string;
  tag_line: string;
  platform: string;
  verified_at: string | null;
};

export type Verification = {
  id: number;
  puuid: string;
  game_name: string;
  tag_line: string;
  platform: string;
  icon_id: number;
  expires_at: string;
  simulation_available: boolean;
};
