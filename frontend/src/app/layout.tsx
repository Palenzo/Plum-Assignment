import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import { BackendStatusBadge } from "@/components/BackendStatusBadge";
import "./globals.css";

const display = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});
const sans = IBM_Plex_Sans({
  variable: "--font-plex",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});
const mono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Plum OPD — Claim Adjudication",
  description: "Submit an OPD claim and get a clear, explained decision in seconds.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="border-b border-border">
          <div className="flex w-full items-center justify-between px-6 py-4 sm:px-8 lg:px-12">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-ink font-display text-base font-semibold">p</span>
              <span className="font-display text-lg font-medium tracking-tight">Plum OPD</span>
            </Link>
            <div className="flex items-center gap-5 sm:gap-6">
              <nav className="flex items-center gap-6 text-sm text-ink-muted">
                <Link href="/" className="transition-colors hover:text-ink">Submit a claim</Link>
                <Link href="/review" className="transition-colors hover:text-ink">Review</Link>
                <Link href="/claims" className="transition-colors hover:text-ink">Claims</Link>
                <Link href="/admin" className="transition-colors hover:text-ink">Admin</Link>
              </nav>
              <BackendStatusBadge />
            </div>
          </div>
        </header>
        <main className="w-full flex-1 px-6 py-10 sm:px-8 sm:py-12 lg:px-12">{children}</main>
        <footer className="border-t border-border">
          <div className="w-full px-6 py-5 text-sm text-ink-faint sm:px-8 lg:px-12">
            Decisions are made by a deterministic policy engine. AI reads the documents; the rules decide.
          </div>
        </footer>
      </body>
    </html>
  );
}
