"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Bell, BellRing, Sparkles, AlertTriangle, X, CheckCheck } from "lucide-react";
import { api, type NotificationItem } from "@/lib/api";

const SEEN_KEY = "lifeos_notifs_seen_at";
const DISMISSED_KEY = "lifeos_notifs_dismissed"; // JSON array of dismissed ids

function readDismissed(): string[] {
  try { return JSON.parse(window.localStorage.getItem(DISMISSED_KEY) || "[]"); }
  catch { return []; }
}
function writeDismissed(ids: string[]) {
  window.localStorage.setItem(DISMISSED_KEY, JSON.stringify(ids));
}

export function NotificationBell() {
  const router = useRouter();
  const [raw, setRaw] = useState<NotificationItem[]>([]);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const items = raw.filter((n) => !dismissed.includes(n.id));

  const computeUnread = useCallback((list: NotificationItem[], dis: string[]) => {
    const seen = Number(window.localStorage.getItem(SEEN_KEY) || 0);
    return list.filter((n) => !dis.includes(n.id) && new Date(n.created_at).getTime() > seen).length;
  }, []);

  const load = useCallback(async () => {
    try {
      const res = await api.getNotifications();
      const dis = readDismissed();
      setRaw(res.items);
      setDismissed(dis);
      setUnread(computeUnread(res.items, dis));
    } catch { /* ignore */ }
  }, [computeUnread]);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

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
      window.localStorage.setItem(SEEN_KEY, String(Date.now()));
      setUnread(0);
    }
  }

  function dismissOne(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    const dis = Array.from(new Set([...readDismissed(), id]));
    writeDismissed(dis);
    setDismissed(dis);
    setUnread(computeUnread(raw, dis));
  }

  function clearAll() {
    const dis = Array.from(new Set([...readDismissed(), ...raw.map((n) => n.id)]));
    writeDismissed(dis);
    setDismissed(dis);
    setUnread(0);
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
            {items.length > 0 && (
              <button onClick={clearAll}
                className="text-xs text-muted hover:text-brand-600 flex items-center gap-1 transition-colors">
                <CheckCheck size={13} /> Clear all
              </button>
            )}
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
                  <div key={n.id}
                    onClick={() => { setOpen(false); router.push(n.link); }}
                    className="group w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-subtle transition-colors border-b border-border last:border-0 cursor-pointer">
                    <span className={`h-8 w-8 shrink-0 rounded-lg flex items-center justify-center ${tone}`}>
                      <Icon size={16} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-ink truncate">{n.title}</span>
                      <span className="block text-xs text-body mt-0.5 line-clamp-2">{n.message}</span>
                    </span>
                    <button onClick={(e) => dismissOne(n.id, e)} aria-label="Dismiss notification"
                      className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger shrink-0 transition-opacity mt-0.5">
                      <X size={15} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
