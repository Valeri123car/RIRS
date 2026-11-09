import type { Metadata } from "next";

import { AdminModels } from "@/components/admin/admin-models";

export const metadata: Metadata = { title: "Modeli · RIFT_HELP" };

export default function AdminModelsPage() {
  return <AdminModels />;
}
