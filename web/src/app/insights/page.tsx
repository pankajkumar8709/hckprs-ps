"use client";
import { useEffect, useState } from "react";
import { Sparkles, AlertTriangle, TrendingUp, Info } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { RowSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError, type Insight } from "@/lib/api";

const sev: Record<string, { ring: string; badge: string; icon: any; label: string }> = {
  high: { ring: "border-red-200 bg-danger-50", badge: "bg-danger text-white", icon: AlertTriangle, label: "High priority" },
  medium: { ring: "border-amber-200 bg-warning-50", badge: "bg-warning text-white", icon: TrendingUp, label: "Medium" },
  low: { ring: "border-border bg-surface", badge: "bg-subtle text-body", icon: Info, label: "Low" },
};

export default function InsightsPage() {
  const { toast } = useToast();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setInsights(await api.listInsights(true)); }
      catch (err) { toast(err instanceof ApiError ? err.message : "Failed to load", "error"); }
      finally { setLoading(false); }
    })();
  }, [toast]);

  return (
    <AppLayout title="Insights">
      <div className="p-4 sm:p-6 max-w-4xl mx-auto">
        <PageHeader title="Intelligent Insights" subtitle="AI-powered analysis across your documents" />
        {loading ? (
          <div className="space-y-3"><RowSkeleton /><RowSkeleton /></div>
        ) : insights.length === 0 ? (
          <EmptyState icon={Sparkles} title="Everything looks good" description="No conflicts or upcoming risks detected across your documents." />
        ) : (
          <div className="space-y-4">
            {insights.map((ins) => {
              const s = sev[ins.severity] || sev.low;
              const Icon = s.icon;
              return (
                <div key={ins.id} className={`rounded-2xl border shadow-card p-5 ${s.ring}`}>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${s.badge}`}>
                      <Icon size={12} /> {s.label}
                    </span>
                    <span className="text-xs uppercase tracking-wide text-body">{ins.type.replace(/_/g, " ")}</span>
                  </div>
                  <p className="mt-3 text-ink">{ins.description}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
