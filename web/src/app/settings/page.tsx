"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield, LogIn, Upload, Eye, Trash2, Share2, UserX, Crown,
  Activity, AlertTriangle, FileText, Clock,
} from "lucide-react";
import AppLayout from "@/components/AppLayout";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { RowSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { logout } from "@/lib/auth";
import { api, ApiError, type AuditLogEntry, type PlanInfo } from "@/lib/api";

// Map each backend audit action to an icon + human label + tone.
const ACTIONS: Record<string, { icon: any; label: string; tone: string }> = {
  login: { icon: LogIn, label: "Signed in", tone: "text-brand-600 bg-brand-50" },
  "document.upload": { icon: Upload, label: "Uploaded a document", tone: "text-emerald-600 bg-emerald-50" },
  "document.access": { icon: Eye, label: "Opened a document", tone: "text-body bg-subtle" },
  "document.download": { icon: FileText, label: "Downloaded a document", tone: "text-body bg-subtle" },
  "document.delete": { icon: Trash2, label: "Deleted a document", tone: "text-danger bg-danger-50" },
  "share.create": { icon: Share2, label: "Shared a document", tone: "text-amber-600 bg-warning-50" },
  "account.delete": { icon: UserX, label: "Account deletion", tone: "text-danger bg-danger-50" },
};

function actionMeta(a: string) {
  return ACTIONS[a] || { icon: Activity, label: a.replace(/[._]/g, " "), tone: "text-body bg-subtle" };
}

function timeAgo(iso: string): string {
  const d = new Date(iso).getTime();
  const s = Math.floor((Date.now() - d) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

export default function SettingsPage() {
  const { toast } = useToast();
  const router = useRouter();
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [log, setLog] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // Delete-account modal state (F3.8).
  const [showDelete, setShowDelete] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [p, l] = await Promise.all([api.getPlan(), api.getAuditLog()]);
        setPlan(p);
        setLog(l);
      } catch (err) {
        toast(err instanceof ApiError ? err.message : "Failed to load settings", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  async function handleDelete() {
    if (confirmText !== "DELETE") return;
    setDeleting(true);
    try {
      await api.deleteAccount();
      toast("Your account and all data were permanently deleted.", "success");
      logout();
      router.replace("/signup");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Deletion failed", "error");
      setDeleting(false);
    }
  }

  return (
    <AppLayout title="Settings">
      <div className="p-4 sm:p-6 max-w-3xl mx-auto">
        <PageHeader title="Settings" subtitle="Your account, activity, and privacy controls" />

        {/* ---------- Account / Plan ---------- */}
        <section className="rounded-2xl border border-border bg-surface shadow-card p-5 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Crown size={18} className="text-brand-600" />
            <h2 className="font-semibold text-ink">Account plan</h2>
          </div>
          {loading ? (
            <RowSkeleton />
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-body">Current plan</p>
                <p className="text-lg font-semibold text-ink capitalize">{plan?.plan_tier ?? "free"}</p>
                <p className="text-xs text-muted mt-1">
                  {plan?.document_limit == null
                    ? "Unlimited documents"
                    : `Up to ${plan.document_limit} documents`}
                </p>
              </div>
              {plan?.plan_tier !== "premium" && (
                <button
                  onClick={() => router.push("/pricing")}
                  className="rounded-xl bg-brand-gradient text-white text-sm font-medium px-4 py-2 hover:opacity-90"
                >
                  View plans
                </button>
              )}
            </div>
          )}
        </section>

        {/* ---------- Activity log (F3.7) ---------- */}
        <section className="rounded-2xl border border-border bg-surface shadow-card p-5 mb-6">
          <div className="flex items-center gap-2 mb-1">
            <Shield size={18} className="text-brand-600" />
            <h2 className="font-semibold text-ink">Activity log</h2>
          </div>
          <p className="text-xs text-muted mb-4">
            A record of security-relevant actions on your account (last 200 events).
          </p>
          {loading ? (
            <div className="space-y-3"><RowSkeleton /><RowSkeleton /><RowSkeleton /></div>
          ) : log.length === 0 ? (
            <EmptyState icon={Activity} title="No activity yet" description="Your sign-ins and document actions will appear here." />
          ) : (
            <ul className="divide-y divide-border">
              {log.map((e) => {
                const m = actionMeta(e.action);
                const Icon = m.icon;
                return (
                  <li key={e.id} className="flex items-center gap-3 py-3">
                    <span className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 ${m.tone}`}>
                      <Icon size={16} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-ink truncate">{m.label}</p>
                      {e.ip_address && <p className="text-xs text-muted">IP {e.ip_address}</p>}
                    </div>
                    <span className="text-xs text-muted flex items-center gap-1 shrink-0">
                      <Clock size={12} /> {timeAgo(e.created_at)}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* ---------- Danger zone (F3.8) ---------- */}
        <section className="rounded-2xl border border-red-200 bg-danger-50 shadow-card p-5">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={18} className="text-danger" />
            <h2 className="font-semibold text-danger">Danger zone</h2>
          </div>
          <p className="text-sm text-body mb-4">
            Delete your account and <strong>all</strong> of your data — documents, files,
            AI embeddings, reminders, insights, chats, and activity history. This action is
            permanent and cannot be undone.
          </p>
          <button
            onClick={() => { setConfirmText(""); setShowDelete(true); }}
            className="inline-flex items-center gap-2 rounded-xl bg-danger text-white text-sm font-medium px-4 py-2 hover:opacity-90"
          >
            <Trash2 size={16} /> Delete my account
          </button>
        </section>
      </div>

      {/* Delete confirmation modal */}
      {showDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={() => !deleting && setShowDelete(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-surface border border-border shadow-card p-6 animate-fade-up">
            <div className="flex items-center gap-2 mb-2">
              <UserX size={20} className="text-danger" />
              <h3 className="font-semibold text-ink">Delete your account?</h3>
            </div>
            <p className="text-sm text-body mb-4">
              This permanently erases everything tied to your account and cannot be reversed.
              Type <span className="font-mono font-semibold text-danger">DELETE</span> to confirm.
            </p>
            <input
              autoFocus
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DELETE"
              className="w-full rounded-xl border border-border bg-app px-3 py-2 text-sm text-ink outline-none focus:border-brand-400 mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDelete(false)}
                disabled={deleting}
                className="rounded-xl border border-border px-4 py-2 text-sm text-body hover:bg-subtle disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={confirmText !== "DELETE" || deleting}
                className="rounded-xl bg-danger text-white px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-40"
              >
                {deleting ? "Deleting…" : "Permanently delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
