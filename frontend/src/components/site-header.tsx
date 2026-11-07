import Link from "next/link";

import { ApiStatus } from "@/components/api-status";

export function SiteHeader() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-4">
        <Link href="/" className="font-semibold tracking-wide text-accent">
          RIFT_HELP
        </Link>
        <div className="flex items-center gap-6">
          <nav className="flex gap-6 text-sm text-muted">
            <Link href="/" className="hover:text-foreground">
              Analiza
            </Link>
          </nav>
          <ApiStatus />
        </div>
      </div>
    </header>
  );
}
