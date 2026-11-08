import type { Metadata } from "next";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "Prijava · RIFT_HELP" };

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
