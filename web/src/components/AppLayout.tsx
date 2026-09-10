"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useRequireAuth, logout } from "@/lib/auth";

const nav = [
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/documents", label: "Documents", icon: "📄" },
  { href: "/reminders", label: "Reminders", icon: "⏰" },
  { href: "/insights", label: "Insights", icon: "💡" },
  { href: "/shared", label: "Shared with me", icon: "🤝" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const checking = useRequireAuth();
  const pathname = usePathname();
  const router = useRouter();

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted">
        Loading…
      </div>
    );
  }

  function onLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 border-r border-border bg-panel flex flex-col">
        <Link href="/chat" className="flex items-center gap-2 font-bold text-lg px-5 py-5 border-b border-border">
          <span className="inline-block h-6 w-6 rounded-md bg-accent" />
          LifeOS
        </Link>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => {
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  active ? "bg-accent text-white" : "text-muted hover:bg-panel2 hover:text-white"
                }`}
              >
                <span>{n.icon}</span>
                {n.label}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={onLogout}
          className="m-3 px-3 py-2.5 rounded-lg text-sm border border-border hover:border-red-500 hover:text-red-400 transition-colors text-left"
        >
          ⎋ Log out
        </button>
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
