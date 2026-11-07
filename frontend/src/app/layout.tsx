import type { Metadata } from "next";
import { Be_Vietnam_Pro, Cinzel, Space_Mono } from "next/font/google";

import { AmbientGlow } from "@/components/ambient-glow";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

/* Pisave iz konceptov: Cinzel za naslove, Be Vietnam Pro za besedilo, Space Mono za številke. */
const cinzel = Cinzel({
  variable: "--font-cinzel",
  subsets: ["latin", "latin-ext"],
  weight: ["500", "600", "700"],
});

const beVietnamPro = Be_Vietnam_Pro({
  variable: "--font-be-vietnam-pro",
  subsets: ["latin", "latin-ext"],
  weight: ["300", "400", "500", "600", "700"],
});

const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "RIFT_HELP",
  description: "Taktični pomočnik za League of Legends: build, rune in matchup glede na nasprotno ekipo.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="sl"
      className={`${cinzel.variable} ${beVietnamPro.variable} ${spaceMono.variable} h-full antialiased`}
    >
      <body className="relative flex min-h-full flex-col overflow-x-hidden">
        <AmbientGlow />
        <SiteHeader />
        <main className="relative z-10 mx-auto w-full max-w-[1440px] flex-1 px-4 py-10 md:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
