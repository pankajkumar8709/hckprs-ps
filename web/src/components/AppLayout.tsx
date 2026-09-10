"use client";
import { useState } from "react";
import { Menu, Search } from "lucide-react";
import { useRequireAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { NotificationBell } from "@/components/NotificationBell";

export default function AppLayout({
  children,
  title,
}: {
  children: React.ReactNode;
  title?: string;
}) {
  const checking = useRequireAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas text-muted">
        <div className="flex items-center gap-2">
          <span className="h-4 w-4 rounded-full border-2 border-brand border-t-transparent animate-spin" />
          Loading…
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-canvas">
      <Sidebar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top bar */}
        <header className="h-16 shrink-0 border-b border-border bg-surface/80 glass sticky top-0 z-30 flex items-center gap-3 px-4 sm:px-6">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden text-body hover:text-ink"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          {title && (
            <span className="font-semibold text-ink lg:hidden">{title}</span>
          )}
          <div className="flex items-center gap-2 ml-auto">
            <span className="hidden md:inline text-muted text-sm mr-1">Document Intelligence</span>
            <NotificationBell />
          </div>
        </header>
        <main className="flex-1 min-w-0 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}
