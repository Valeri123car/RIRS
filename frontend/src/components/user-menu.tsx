"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

/** Desni del glave: povezava za prijavo ali profil in odjava. */
export function UserMenu() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  if (loading) return null;

  if (!user) {
    return (
      <Link
        href="/prijava"
        className="font-headline text-sm tracking-widest text-on-surface-variant uppercase hover:text-primary"
      >
        Prijava
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3">
      {user.role === "admin" && (
        <Link
          href="/admin/modeli"
          className="font-label text-xs tracking-wider text-secondary uppercase hover:underline"
        >
          Modeli
        </Link>
      )}
      <Link
        href="/profil"
        title={user.email}
        className="max-w-48 truncate font-label text-xs tracking-wider text-primary hover:underline"
      >
        {user.email}
      </Link>
      <Button
        variant="secondary"
        onClick={async () => {
          await logout();
          router.push("/");
        }}
      >
        Odjava
      </Button>
    </div>
  );
}
