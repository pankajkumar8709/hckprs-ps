"use client";
import Link from "next/link";

export default function PublicHeader() {
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between px-6 py-4 border-b border-border bg-bg/80 backdrop-blur">
      <Link href="/" className="flex items-center gap-2 font-bold text-lg">
        <span className="inline-block h-6 w-6 rounded-md bg-accent" />
        LifeOS <span className="text-accent2">Agent</span>
      </Link>
      <nav className="flex items-center gap-3 text-sm">
        <Link href="/about" className="text-muted hover:text-white transition-colors px-3 py-2">
          Features
        </Link>
        <Link
          href="/login"
          className="px-4 py-2 rounded-lg border border-border hover:border-accent transition-colors"
        >
          Login
        </Link>
        <Link
          href="/signup"
          className="px-4 py-2 rounded-lg bg-accent hover:bg-accent2 transition-colors font-medium"
        >
          Sign Up
        </Link>
      </nav>
    </header>
  );
}
