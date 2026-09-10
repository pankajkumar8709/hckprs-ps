"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Bell, BellRing, Sparkles, AlertTriangle } from "lucide-react";
import { api, type NotificationItem } from "@/lib/api";

const SEEN_KEY = "lifeos_notifs_seen_at";

export function NotificationBell() {
  const router = useRouter();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const computeUnread = useCallback((list: NotificationItem[]) => {
    const seen = Number(window.localStorage.getItem(SEEN_KEY) || 0);
    return list.filter((n) => new Date(n.created_at).getTime() > seen).length;
  }, []);

  const load = useCallback(async () => {
    try {
      const res = await api.getNotifications();
      setItems(res.items);
      setUnread(computeUnread(res.items));
    } catch { /* ignore */ }
  }, [computeUnread]);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000); // poll every 60s
    return () => clearInterval(t);
  }, [load]);

  // Close on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      // Opening marks all current notifications as seen.
      window.localStorage.setItem(SEEN_KEY, String(Date.now()));
      setUnread(0);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button onClick={toggle} aria-label="Notifications"
        className="relative h-9 w-9 rounded-lg flex items-center justify-center text-body hover:bg-subtle hover:text-ink transition-colors">
        {unread > 0 ? <BellRing size={19} /> : <Bell size={19} />}
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 min-w-4 px-1 rounded-full bg-danger text-white text-[10px] font-semibold flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-surface border border-border rounded-2xl shadow-card-hover overflow-hidden z-50 animate-fade-up">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <span className="font-semibold text-ink text-sm">Notifications</span>
            <span className="text-xs text-muted">{items.length}</span>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted">
                <Sparkles size={22} className="mx-auto mb-2 text-brand-600" />
                You're all caught up.
              </div>
            ) : (
              items.map((n) => {
                const Icon = n.kind === "insight" ? AlertTriangle : BellRing;
                const tone =
                  n.severity === "high" ? "text-danger bg-danger-50"
                  : n.severity === "medium" ? "text-warning bg-warning-50"
                  : "text-brand-600 bg-brand-50";
                return (
                  <button key={n.id}
                    onClick={() => { setOpen(false); router.push(n.link); }}
                    className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-subtle transition-colors border-b border-border last:border-0">
                    <span className={`h-8 w-8 shrink-0 rounded-lg flex items-center justify-center ${tone}`}>
                      <Icon size={16} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-ink truncate">{n.title}</span>
                      <span className="block text-xs text-body mt-0.5 line-clamp-2">{n.message}</span>
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
