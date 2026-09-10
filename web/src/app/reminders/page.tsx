"use client";
import { useEffect, useState, useCallback } from "react";
import AppLayout from "@/components/AppLayout";
import { api, ApiError, type Reminder } from "@/lib/api";

function urgency(due: string | null): string {
  if (!due) return "border-border text-muted";
  const days = (new Date(due).getTime() - Date.now()) / 86400000;
  if (days < 7) return "border-red-700 text-red-400";
  if (days < 30) return "border-yellow-700 text-yellow-400";
  return "border-border text-muted";
}

export default function RemindersPage() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setReminders(await api.listReminders());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load reminders");
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function markDone(id: string) {
    try {
      await api.updateReminder(id, "done");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  }

  return (
    <AppLayout>
      <div className="h-screen overflow-y-auto p-6 max-w-3xl">
        <h1 className="font-semibold">Reminders</h1>
        <p className="text-xs text-muted">Automatically created from dates found in your documents.</p>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        <div className="mt-5 space-y-2">
          {reminders.length === 0 && <p className="text-sm text-muted">No reminders yet.</p>}
          {reminders.map((r) => (
            <div key={r.id} className="rounded-xl border border-border bg-panel p-4 flex items-center justify-between gap-4">
              <div>
                <div className="font-medium text-sm">{r.title}</div>
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <span className={`px-2 py-0.5 rounded-full border ${urgency(r.due_date)}`}>
                    {r.due_date ? new Date(r.due_date).toLocaleDateString() : "no date"}
                  </span>
                  <span className="text-muted">{r.status}</span>
                </div>
              </div>
              {r.status === "pending" && (
                <button onClick={() => markDone(r.id)} className="text-xs px-3 py-1.5 rounded-lg border border-border hover:border-green-600 hover:text-green-400">
                  Mark done
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
