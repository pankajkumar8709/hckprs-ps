"use client";
import Link from "next/link";
import { Sparkles } from "lucide-react";

export default function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 glass border-b border-border">
      <div className="max-w-6xl mx-auto flex items-center justify-between px-6 h-16">
        <Link href="/" className="flex items-center gap-2.5 font-semibold text-ink">
          <span className="h-8 w-8 rounded-xl bg-brand-gradient flex items-center justify-center text-white">
            <Sparkles size={17} />
          </span>
          LifeOS
        </Link>
        <nav className="flex items-center gap-2 text-sm">
          <Link href="/about" className="px-3 py-2 text-body hover:text-ink transition-colors">
            Features
          </Link>
          <Link href="/login" className="px-4 py-2 rounded-xl border border-border text-ink hover:border-ring hover:bg-subtle transition-colors">
            Login
          </Link>
          <Link href="/signup" className="px-4 py-2 rounded-xl bg-brand-gradient text-white font-medium shadow-soft hover:shadow-card-hover hover:brightness-105 transition-all">
            Get Started
          </Link>
        </nav>
      </div>
    </header>
  );
}
