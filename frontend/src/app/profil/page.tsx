import type { Metadata } from "next";

import { ProfileView } from "@/components/profile-view";

export const metadata: Metadata = { title: "Profil · RIFT_HELP" };

export default function ProfilePage() {
  return <ProfileView />;
}
