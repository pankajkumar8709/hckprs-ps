"use client";
import { useEffect, useState, useCallback } from "react";
import { BellRing, CheckCircle2, FileText, CalendarPlus, Plus, X } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { RowSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError, downloadReminderIcs, type Reminder } from "@/lib/api";

function bucket(due: string | null): string {
  if (!due) return "Later";
  const days = Math.floor((new Date(due).getTime() - Date.now()) / 86400000);
  if (days < 0) return "Overdue";
  if (days === 0) return "Today";
  if (days <= 7) return "This week";
  return "Later";
}
const ORDER = ["Overdue", "Today", "This week", "Later", "Completed"];
function urgencyTone(due: string | null) {
  if (!due) return "neutral" as const;
  const days = (new Date(due).getTime() - Date.now()) / 86400000;
  if (days < 7) return "danger" as const;
  if (days < 30) return "warning" as const;
  return "neutral" as const;
}

export default function RemindersPage() {
  const { toast } = useToast();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"all" | "pending" | "completed">("all");
  const [showForm, setShowForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDate, setNewDate] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try { setReminders(await api.listReminders()); }
    catch (err) { toast(err instanceof ApiError ? err.message : "Failed to load", "error"); }
    finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  async function createTask(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      await api.createReminder(newTitle.trim(), newDate || null);
      toast("Task created", "success");
      setNewTitle(""); setNewDate(""); setShowForm(false);
      await load();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not create task", "error");
    } finally { setCreating(false); }
  }

  async function markDone(id: string) {
    try {
      await api.updateReminder(id, "done");
      toast("Reminder completed", "success");
      await load();
    } catch (err) { toast(err instanceof ApiError ? err.message : "Update failed", "error"); }
  }

  async function addToCalendar(r: Reminder) {
    try {
      const fname = (r.title || "reminder").replace(/[^a-z0-9]+/gi, "_").slice(0, 50) + ".ics";
      await downloadReminderIcs(r.id, fname, 7);
      toast("Calendar file downloaded — open it to add the reminder", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Calendar export failed", "error");
    }
  }

  const view = reminders.filter((r) =>
    tab === "all" ? true : tab === "pending" ? r.status === "pending" : r.status !== "pending"
  );
  const groups: Record<string, Reminder[]> = {};
  for (const r of view) {
    const g = r.status !== "pending" ? "Completed" : bucket(r.due_date);
    (groups[g] ||= []).push(r);
  }

  return (
    <AppLayout title="Reminders">
      <div className="p-4 sm:p-6 max-w-4xl mx-auto">
        <PageHeader title="Reminders" subtitle="Automatically created from dates in your documents"
          actions={<Button size="md" onClick={() => setShowForm((v) => !v)}><Plus size={16} /> New Task</Button>} />

        {showForm && (
          <form onSubmit={createTask} className="mb-6 bg-surface border border-border rounded-2xl shadow-card p-4 flex flex-col sm:flex-row gap-3 items-stretch sm:items-end animate-fade-up">
            <div className="flex-1">
              <label htmlFor="task-title" className="block text-xs text-body mb-1">Task</label>
              <input id="task-title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} required
                placeholder="e.g. Renew car insurance"
                className="w-full rounded-xl bg-canvas border border-border px-3 py-2.5 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label htmlFor="task-date" className="block text-xs text-body mb-1">Due date (optional)</label>
              <input id="task-date" type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)}
                className="rounded-xl bg-canvas border border-border px-3 py-2.5 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-ring" />
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="md" disabled={creating}>{creating ? "Adding…" : "Add task"}</Button>
              <Button type="button" variant="ghost" size="md" onClick={() => setShowForm(false)}><X size={16} /></Button>
            </div>
          </form>
        )}

        <div className="flex gap-2 mb-6">
          {(["all", "pending", "completed"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`text-sm px-3 py-1.5 rounded-lg border capitalize transition-colors ${
                tab === t ? "bg-brand-50 border-indigo-200 text-brand-600 font-medium" : "bg-surface border-border text-body hover:border-ring"}`}>
              {t}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-3"><RowSkeleton /><RowSkeleton /><RowSkeleton /></div>
        ) : view.length === 0 ? (
          <EmptyState icon={BellRing} title="You're all caught up" description="No reminders to show here." />
        ) : (
          <div className="space-y-8">
            {ORDER.filter((g) => groups[g]?.length).map((g) => (
              <div key={g}>
                <h3 className="text-sm font-semibold text-body mb-3">{g}</h3>
                <div className="space-y-2">
                  {groups[g].map((r) => (
                    <div key={r.id} className="bg-surface border border-border rounded-2xl shadow-card p-4 flex items-center justify-between gap-4">
                      <div className="flex items-start gap-3 min-w-0">
                        <span className="h-9 w-9 shrink-0 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                          <BellRing size={17} />
                        </span>
                        <div className="min-w-0">
                          <div className="font-medium text-ink truncate">{r.title}</div>
                          <div className="mt-1 flex items-center gap-2 flex-wrap">
                            <StatusBadge tone={r.status === "pending" ? urgencyTone(r.due_date) : "success"}>
                              {r.due_date ? new Date(r.due_date).toLocaleDateString() : "no date"}
                            </StatusBadge>
                            <span className="text-xs text-muted capitalize">{r.status}</span>
                          </div>
                        </div>
                      </div>
                      {r.status === "pending" && (
                        <div className="flex items-center gap-2 shrink-0">
                          {r.due_date && (
                            <Button size="sm" variant="ghost" onClick={() => addToCalendar(r)} title="Add to calendar with a 7-day reminder">
                              <CalendarPlus size={15} /> <span className="hidden sm:inline">Calendar</span>
                            </Button>
                          )}
                          <Button size="sm" variant="secondary" onClick={() => markDone(r.id)}>
                            <CheckCircle2 size={15} /> Complete
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
