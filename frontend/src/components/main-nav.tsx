"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  label: string;
  href: string;
  /** false = stran še ni implementirana; povezava je prikazana, a onemogočena. */
  ready: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { label: "Moje analize", href: "/analize", ready: false },
  { label: "V živo", href: "/", ready: true },
  { label: "Napredek", href: "/napredek", ready: false },
  { label: "Ekipa", href: "/ekipa", ready: false },
];

const BASE = "py-2 font-headline text-sm uppercase tracking-widest transition-colors";

export function MainNav() {
  const pathname = usePathname();

  return (
    <nav className="hidden items-center gap-6 md:flex">
      {NAV_ITEMS.map((item) => {
        if (!item.ready) {
          return (
            <span
              key={item.href}
              aria-disabled
              title="Kmalu"
              className={`${BASE} cursor-not-allowed text-muted/60`}
            >
              {item.label}
            </span>
          );
        }

        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={
              active
                ? `${BASE} border-b-2 border-primary font-bold text-primary`
                : `${BASE} text-on-surface-variant hover:text-primary`
            }
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
