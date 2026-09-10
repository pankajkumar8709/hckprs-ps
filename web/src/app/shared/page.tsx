"use client";
import { useEffect, useState } from "react";
import { Users2, FileText, X, ChevronRight } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError, type DocumentSummary, type DocumentDetail } from "@/lib/api";

export default function SharedPage() {
  const { toast } = useToast();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);

  useEffect(() => {
    (async () => {
      try { setDocs(await api.sharedWithMe()); }
      catch (err) { toast(err instanceof ApiError ? err.message : "Failed to load", "error"); }
      finally { setLoading(false); }
    })();
  }, [toast]);

  async function open(id: string) {
    try { setSelected(await api.getDocument(id)); }
    catch (err) { toast(err instanceof ApiError ? err.message : "Failed to open", "error"); }
  }

  return (
    <AppLayout title="Shared with me">
      <div className="p-4 sm:p-6 max-w-5xl mx-auto">
        <PageHeader title="Shared with me" subtitle="Documents other users have shared with you" />
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><CardSkeleton /><CardSkeleton /></div>
        ) : docs.length === 0 ? (
          <EmptyState icon={Users2} title="Nothing shared yet" description="Documents shared with you will appear here." />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {docs.map((d) => (
              <button key={d.id} onClick={() => open(d.id)}
                className="text-left bg-surface border border-border rounded-2xl shadow-card p-5 transition-all hover:-translate-y-0.5 hover:shadow-card-hover hover:border-ring group">
                <div className="flex items-start justify-between">
                  <span className="h-10 w-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center"><FileText size={19} /></span>
                  <StatusBadge tone="brand">{d.doc_type}</StatusBadge>
                </div>
                <h3 className="mt-3 font-medium text-ink truncate">{d.filename}</h3>
                <span className="mt-3 flex items-center gap-1 text-xs text-brand-600 group-hover:gap-1.5 transition-all">Open <ChevronRight size={14} /></span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 z-40">
          <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={() => setSelected(null)} />
          <aside className="absolute right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border overflow-y-auto animate-fade-up">
            <div className="sticky top-0 glass border-b border-border px-5 h-14 flex items-center justify-between">
              <span className="font-semibold text-ink truncate">{selected.filename}</span>
              <button onClick={() => setSelected(null)} className="text-muted hover:text-ink" aria-label="Close"><X size={18} /></button>
            </div>
            <div className="p-5">
              <StatusBadge tone="brand">{selected.doc_type}</StatusBadge>
              <h4 className="mt-5 text-sm font-medium text-body">Extracted information</h4>
              <div className="mt-2 space-y-2">
                {selected.extracted_fields.map((f) => (
                  <div key={f.id} className="flex items-start gap-2 text-sm">
                    <StatusBadge tone="neutral">{f.field_type}</StatusBadge>
                    <div><div className="text-muted text-xs">{f.field_name}</div><div className="text-ink">{f.field_value}</div></div>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}
    </AppLayout>
  );
}
