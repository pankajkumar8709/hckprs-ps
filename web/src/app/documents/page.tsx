"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import {
  FileText, UploadCloud, Search, Trash2, Share2, X, BellRing,
  Sparkles, ChevronRight, CheckCircle2, Clock, Download,
} from "lucide-react";
import AppLayout from "@/components/AppLayout";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { StatusBadge, statusTone } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton, StatSkeleton } from "@/components/ui/Skeleton";
import { StatCard, AgentTrace } from "@/components/domain";
import { useToast } from "@/components/ui/Toast";
import {
  api, ApiError, downloadDocument, type DocumentSummary, type DocumentDetail, type Reminder, type Insight,
} from "@/lib/api";

const FILTERS = ["all", "lease", "insurance", "loan_emi", "subscription", "medical", "other"];
const FILTER_LABEL: Record<string, string> = {
  all: "All", lease: "Lease", insurance: "Insurance", loan_emi: "Loan",
  subscription: "Subscription", medical: "Medical", other: "Other",
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function DocumentsPage() {
  const { toast } = useToast();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [uploading, setUploading] = useState(false);
  const [stage, setStage] = useState<string>("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [dragOver, setDragOver] = useState(false);
  const [shareEmail, setShareEmail] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const [d, r, i] = await Promise.all([
        api.listDocuments(),
        api.listReminders().catch(() => []),
        api.listInsights().catch(() => []),
      ]);
      setDocs(d); setReminders(r); setInsights(i);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Failed to load", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  async function handleFile(file: File) {
    setUploading(true);
    const stages = ["Reading document…", "Classifying…", "Extracting information…", "Validating…", "Indexing for AI search…"];
    let si = 0;
    setStage(stages[0]);
    const timer = setInterval(() => { si = Math.min(si + 1, stages.length - 1); setStage(stages[si]); }, 1200);
    try {
      const detail = await api.uploadDocument(file);
      clearInterval(timer);
      setSelected(detail);
      toast(`${file.name} processed`, "success");
      await load();
    } catch (err) {
      clearInterval(timer);
      toast(err instanceof ApiError ? err.message : "Upload failed", "error");
    } finally {
      setUploading(false);
      setStage("");
    }
  }

  async function openDoc(id: string) {
    try { setSelected(await api.getDocument(id)); }
    catch (err) { toast(err instanceof ApiError ? err.message : "Failed to open", "error"); }
  }
  async function del(id: string) {
    try {
      await api.deleteDocument(id);
      if (selected?.id === id) setSelected(null);
      toast("Document deleted", "success");
      await load();
    } catch (err) { toast(err instanceof ApiError ? err.message : "Delete failed", "error"); }
  }
  async function dl(id: string, filename: string) {
    try {
      toast("Preparing secure download…", "info");
      await downloadDocument(id, filename);   // F3.3: mint signed URL -> fetch encrypted file
    } catch (err) { toast(err instanceof ApiError ? err.message : "Download failed", "error"); }
  }
  async function share() {
    if (!selected || !shareEmail) return;
    try {
      await api.shareDocument(selected.id, shareEmail, "view");
      toast(`Shared with ${shareEmail}`, "success");
      setShareEmail("");
    } catch (err) { toast(err instanceof ApiError ? err.message : "Share failed", "error"); }
  }

  const filtered = docs.filter((d) =>
    (filter === "all" || d.doc_type === filter) &&
    d.filename.toLowerCase().includes(search.toLowerCase())
  );
  const upcoming = reminders.filter((r) => r.status === "pending").length;
  const highInsights = insights.filter((i) => i.severity === "high").length;

  return (
    <AppLayout title="Dashboard">
      <div className="p-4 sm:p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-ink tracking-tight">{greeting()} 👋</h1>
          <p className="mt-1 text-sm text-body">Here's what's happening with your documents.</p>
        </div>

        {/* Stats */}
        <div className="grid gap-4 sm:grid-cols-3 mb-8">
          {loading ? (
            <><StatSkeleton /><StatSkeleton /><StatSkeleton /></>
          ) : (
            <>
              <StatCard icon={FileText} label="Documents" value={docs.length} hint={`${docs.length} total`} />
              <StatCard icon={BellRing} label="Reminders" value={upcoming} hint={`${upcoming} upcoming`} tone="warning" />
              <StatCard icon={Sparkles} label="Insights" value={insights.length} hint={`${highInsights} high priority`} tone={highInsights ? "danger" : "brand"} />
            </>
          )}
        </div>

        {/* Upload zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); }}
          className={`rounded-2xl border-2 border-dashed p-8 text-center transition-colors mb-8 ${
            dragOver ? "border-brand bg-brand-50" : "border-border bg-surface"
          }`}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-3">
              <span className="h-10 w-10 rounded-full border-2 border-brand border-t-transparent animate-spin" />
              <p className="text-sm font-medium text-ink flex items-center gap-2">
                <Sparkles size={15} className="text-brand-600" /> {stage}
              </p>
            </div>
          ) : (
            <>
              <span className="mx-auto h-12 w-12 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center">
                <UploadCloud size={24} />
              </span>
              <p className="mt-3 font-medium text-ink">Upload a document</p>
              <p className="text-sm text-body">Drag &amp; drop here, or</p>
              <div className="mt-3">
                <Button size="md" onClick={() => fileInput.current?.click()}>Browse files</Button>
                <input ref={fileInput} type="file" hidden accept=".pdf,.txt,.md,.jpg,.jpeg,.png"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }} />
              </div>
              <p className="mt-2 text-xs text-muted">PDF · TXT · MD · Images</p>
            </>
          )}
        </div>

        {/* Documents header + search + filters */}
        <PageHeader title="Documents" subtitle="Your processed documents" />
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search documents…"
              className="w-full rounded-xl bg-surface border border-border pl-9 pr-3 py-2.5 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-ring" />
          </div>
        </div>
        <div className="flex flex-wrap gap-2 mb-5">
          {FILTERS.map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
                filter === f ? "bg-brand-50 border-indigo-200 text-brand-600 font-medium" : "bg-surface border-border text-body hover:border-ring"
              }`}>
              {FILTER_LABEL[f]}
            </button>
          ))}
        </div>

        {/* Document cards */}
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <CardSkeleton /><CardSkeleton /><CardSkeleton />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={FileText} title="No documents yet"
            description="Upload your first document and let AI turn it into actionable information."
            action={<Button onClick={() => fileInput.current?.click()}>Upload Document</Button>} />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((d) => {
              const remCount = reminders.filter((r) => r.document_id === d.id).length;
              return (
                <button key={d.id} onClick={() => openDoc(d.id)}
                  className="text-left bg-surface border border-border rounded-2xl shadow-card p-5 transition-all hover:-translate-y-0.5 hover:shadow-card-hover hover:border-ring group">
                  <div className="flex items-start justify-between">
                    <span className="h-10 w-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                      <FileText size={19} />
                    </span>
                    <StatusBadge tone={statusTone(d.upload_status)}>{d.upload_status}</StatusBadge>
                  </div>
                  <h3 className="mt-3 font-medium text-ink truncate">{d.filename}</h3>
                  <div className="mt-1 flex items-center gap-2">
                    <StatusBadge tone="brand">{d.doc_type}</StatusBadge>
                    <span className="text-xs text-muted">{new Date(d.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="mt-3 flex items-center gap-3 text-xs text-body">
                    {remCount > 0 && <span className="flex items-center gap-1"><BellRing size={13} /> {remCount}</span>}
                    <span className="ml-auto flex items-center gap-1 text-brand-600 group-hover:gap-1.5 transition-all">Open <ChevronRight size={14} /></span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail drawer */}
      {selected && (
        <div className="fixed inset-0 z-40">
          <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={() => setSelected(null)} />
          <aside className="absolute right-0 top-0 h-full w-full max-w-md bg-surface border-l border-border shadow-card-hover overflow-y-auto animate-fade-up">
            <div className="sticky top-0 glass border-b border-border px-5 h-14 flex items-center justify-between">
              <span className="font-semibold text-ink truncate">{selected.filename}</span>
              <button onClick={() => setSelected(null)} className="text-muted hover:text-ink" aria-label="Close"><X size={18} /></button>
            </div>
            <div className="p-5">
              <div className="flex items-center gap-2">
                <StatusBadge tone="brand">{selected.doc_type}</StatusBadge>
                <StatusBadge tone={statusTone(selected.upload_status)}>{selected.upload_status}</StatusBadge>
              </div>

              <h4 className="mt-5 text-sm font-medium text-body">Extracted information</h4>
              {selected.extracted_fields.length === 0 ? (
                <p className="text-sm text-muted mt-2">No fields extracted.</p>
              ) : (
                <div className="mt-2 space-y-2">
                  {selected.extracted_fields.map((f) => (
                    <div key={f.id} className="flex items-start gap-2 text-sm">
                      <StatusBadge tone="neutral">{f.field_type}</StatusBadge>
                      <div>
                        <div className="text-muted text-xs">{f.field_name}</div>
                        <div className="text-ink">{f.field_value}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {selected.agent_trace?.length > 0 && (
                <details className="mt-5 group" open>
                  <summary className="text-sm font-medium text-body cursor-pointer select-none flex items-center gap-1.5">
                    <Sparkles size={14} className="text-brand-600" /> How this was extracted
                  </summary>
                  <div className="mt-3"><AgentTrace steps={selected.agent_trace} /></div>
                </details>
              )}

              <h4 className="mt-6 text-sm font-medium text-body">Share</h4>
              <div className="mt-2 flex gap-2">
                <input value={shareEmail} onChange={(e) => setShareEmail(e.target.value)} placeholder="user@example.com"
                  className="flex-1 rounded-xl bg-canvas border border-border px-3 py-2 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-ring" />
                <Button size="sm" variant="secondary" onClick={share}><Share2 size={15} /> Share</Button>
              </div>

              <div className="mt-8 flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={() => dl(selected.id, selected.filename)}><Download size={15} /> Download</Button>
                <Button variant="danger" size="sm" onClick={() => del(selected.id)}><Trash2 size={15} /> Delete document</Button>
              </div>
            </div>
          </aside>
        </div>
      )}
    </AppLayout>
  );
}
