import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
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
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-ink font-display text-base font-semibold">p</span>
              <span className="font-display text-lg font-medium tracking-tight">Plum OPD</span>
            </Link>
            <nav className="flex items-center gap-6 text-sm text-ink-muted">
              <Link href="/" className="transition-colors hover:text-ink">Submit a claim</Link>
              <Link href="/claims" className="transition-colors hover:text-ink">Claims</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10 sm:py-14">{children}</main>
        <footer className="border-t border-border">
          <div className="mx-auto w-full max-w-5xl px-6 py-5 text-sm text-ink-faint">
            Decisions are made by a deterministic policy engine. AI reads the documents; the rules decide.
          </div>
        </footer>
      </body>
    </html>
  );
}
