"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, FileText, Bell, Sparkles, MessageSquare,
  Users2, Crown, LogOut, ChevronLeft, X, Settings,
} from "lucide-react";
import { logout } from "@/lib/auth";
import { api } from "@/lib/api";

const nav = [
  { href: "/documents", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/reminders", label: "Reminders", icon: Bell },
  { href: "/insights", label: "Insights", icon: Sparkles },
  { href: "/chat", label: "AI Assistant", icon: MessageSquare },
  { href: "/shared", label: "Shared with me", icon: Users2 },
];

// Note: no new routes — "Dashboard" and "Documents" both point at /documents,
// which renders the dashboard + document workspace.
const navUnique = [
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/reminders", label: "Reminders", icon: Bell },
  { href: "/insights", label: "Insights", icon: Sparkles },
  { href: "/chat", label: "AI Assistant", icon: MessageSquare },
  { href: "/shared", label: "Shared with me", icon: Users2 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({
  collapsed, setCollapsed, mobileOpen, setMobileOpen,
}: {
  collapsed: boolean; setCollapsed: (v: boolean) => void;
  mobileOpen: boolean; setMobileOpen: (v: boolean) => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [plan, setPlan] = useState<string>("free");

  useEffect(() => {
    api.getPlan?.().then((p) => setPlan(p.plan_tier)).catch(() => {});
  }, []);

  const width = collapsed ? "w-[76px]" : "w-64";

  const content = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-16 border-b border-border">
        <Link href="/" onClick={() => setMobileOpen(false)} className="flex items-center gap-2.5 font-semibold text-ink">
          <div className="h-8 w-8 rounded-xl bg-brand-gradient flex items-center justify-center text-white shrink-0">
            <Sparkles size={17} />
          </div>
          {!collapsed && (
            <span className="font-semibold text-ink tracking-tight">LifeOS</span>
          )}
        </Link>
        <button
          onClick={() => setMobileOpen(false)}
          className="ml-auto lg:hidden text-muted hover:text-ink"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navUnique.map((n) => {
          const active = pathname === n.href;
          const Icon = n.icon;
          return (
            <Link
              key={n.href}
              href={n.href}
              onClick={() => setMobileOpen(false)}
              title={collapsed ? n.label : undefined}
              className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
                active
                  ? "bg-brand-50 text-brand-600 font-medium"
                  : "text-body hover:bg-subtle hover:text-ink"
              }`}
            >
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-r-full bg-brand-gradient" />
              )}
              <Icon size={19} className="shrink-0" />
              {!collapsed && <span>{n.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Premium + profile */}
      <div className="p-3 border-t border-border space-y-2">
        {plan !== "premium" && !collapsed && (
          <Link
            href="/pricing"
            onClick={() => setMobileOpen(false)}
            className="block rounded-xl p-3 bg-brand-gradient text-white"
          >
            <div className="flex items-center gap-2 text-sm font-medium">
              <Crown size={16} /> Upgrade to Premium
            </div>
            <p className="text-xs text-indigo-100 mt-1">
              Unlimited docs & advanced insights
            </p>
          </Link>
        )}
        <button
          onClick={() => { logout(); router.replace("/login"); }}
          title={collapsed ? "Log out" : undefined}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-body hover:bg-subtle hover:text-danger transition-colors"
        >
          <LogOut size={19} className="shrink-0" />
          {!collapsed && <span>Log out</span>}
        </button>
      </div>

      {/* Collapse toggle (desktop) */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="hidden lg:flex items-center justify-center h-9 border-t border-border text-muted hover:text-ink"
        aria-label="Toggle sidebar"
      >
        <ChevronLeft
          size={16}
          className={`transition-transform ${collapsed ? "rotate-180" : ""}`}
        />
      </button>
    </div>
  );

  return (
    <>
      {/* Desktop */}
      <aside
        className={`hidden lg:flex ${width} shrink-0 bg-surface border-r border-border transition-all duration-300`}
      >
        {content}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-ink/30 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 h-full w-64 bg-surface border-r border-border animate-fade-up">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
