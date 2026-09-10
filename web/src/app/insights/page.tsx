"use client";
import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api, ApiError, type Insight } from "@/lib/api";

const sevColor: Record<string, string> = {
  high: "border-red-700 text-red-400",
  medium: "border-yellow-700 text-yellow-400",
  low: "border-border text-muted",
};

export default function InsightsPage() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setInsights(await api.listInsights(true)); // refresh to reflect current state
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load insights");
      }
    })();
  }, []);

  return (
    <AppLayout>
      <div className="h-screen overflow-y-auto p-6 max-w-3xl">
        <h1 className="font-semibold">Insights</h1>
        <p className="text-xs text-muted">Cross-document patterns — clashing dates and upcoming renewal risks.</p>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        <div className="mt-5 space-y-3">
          {insights.length === 0 && <p className="text-sm text-muted">No insights yet. Upload a few documents with dates.</p>}
          {insights.map((ins) => (
            <div key={ins.id} className="rounded-xl border border-border bg-panel p-4">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full border ${sevColor[ins.severity] || sevColor.low}`}>{ins.severity}</span>
                <span className="text-xs uppercase tracking-wide text-accent2">{ins.type.replace("_", " ")}</span>
              </div>
              <p className="mt-2 text-sm">{ins.description}</p>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
