import Link from "next/link";

import { ApiStatus } from "@/components/api-status";
import { MainNav } from "@/components/main-nav";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-outline/60 bg-surface/95 shadow-[0_4px_25px_rgb(0_0_0/0.7)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 md:px-8">
        <div className="flex items-center gap-6 lg:gap-10">
          <Link href="/" className="group flex items-center select-none">
            <span className="mr-2.5 flex size-7 rotate-45 items-center justify-center border border-primary bg-primary/20 shadow-[0_0_12px_rgb(240_191_92/0.4)] transition-transform duration-500 group-hover:rotate-90">
              <span className="size-2 bg-primary" />
            </span>
            <span className="font-headline text-xl font-bold tracking-[0.18em] text-primary uppercase">
              Rift_Help
            </span>
          </Link>
          <MainNav />
        </div>
        <ApiStatus />
      </div>
    </header>
  );
}
