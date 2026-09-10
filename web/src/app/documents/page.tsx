"use client";
import { useEffect, useState, useCallback } from "react";
import AppLayout from "@/components/AppLayout";
import {
  api, ApiError, type DocumentSummary, type DocumentDetail,
} from "@/lib/api";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shareEmail, setShareEmail] = useState("");
  const [shareMsg, setShareMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDocs(await api.listDocuments());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load documents");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const detail = await api.uploadDocument(file);
      await load();
      setSelected(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function openDoc(id: string) {
    setShareMsg(null);
    try {
      setSelected(await api.getDocument(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to open document");
    }
  }

  async function del(id: string) {
    try {
      await api.deleteDocument(id);
      if (selected?.id === id) setSelected(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
    }
  }

  async function share() {
    if (!selected || !shareEmail) return;
    setShareMsg(null);
    try {
      await api.shareDocument(selected.id, shareEmail, "view");
      setShareMsg(`Shared with ${shareEmail}`);
      setShareEmail("");
    } catch (err) {
      setShareMsg(err instanceof ApiError ? err.message : "Share failed");
    }
  }

  return (
    <AppLayout>
      <div className="h-screen grid grid-cols-2">
        {/* Left: list + upload */}
        <div className="border-r border-border overflow-y-auto p-6">
          <div className="flex items-center justify-between">
            <h1 className="font-semibold">Documents</h1>
            <label className="text-sm px-3 py-2 rounded-lg bg-accent hover:bg-accent2 cursor-pointer transition-colors">
              {uploading ? "Uploading…" : "+ Upload"}
              <input type="file" hidden accept=".pdf,.txt,.md,.jpg,.jpeg,.png" onChange={onUpload} disabled={uploading} />
            </label>
          </div>
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          <div className="mt-4 space-y-2">
            {docs.length === 0 && <p className="text-sm text-muted">No documents yet. Upload one to start.</p>}
            {docs.map((d) => (
              <button
                key={d.id}
                onClick={() => openDoc(d.id)}
                className={`w-full text-left rounded-xl border p-3 transition-colors ${
                  selected?.id === d.id ? "border-accent bg-panel2" : "border-border bg-panel hover:border-accent2"
                }`}
              >
                <div className="font-medium text-sm truncate">{d.filename}</div>
                <div className="mt-1 flex gap-2 text-xs">
                  <span className="px-2 py-0.5 rounded-full border border-border text-muted uppercase">{d.doc_type}</span>
                  <span className={`px-2 py-0.5 rounded-full border ${
                    d.upload_status === "done" ? "border-green-700 text-green-400"
                    : d.upload_status === "failed" ? "border-red-700 text-red-400"
                    : "border-border text-muted"}`}>{d.upload_status}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right: detail */}
        <div className="overflow-y-auto p-6">
          {!selected ? (
            <p className="text-sm text-muted mt-10 text-center">Select a document to view its extracted fields and agent trace.</p>
          ) : (
            <div>
              <div className="flex items-start justify-between gap-4">
                <h2 className="font-semibold">{selected.filename}</h2>
                <button onClick={() => del(selected.id)} className="text-xs px-2 py-1 rounded-lg border border-border hover:border-red-500 hover:text-red-400">Delete</button>
              </div>

              {/* Extracted fields */}
              <h3 className="mt-5 text-sm font-medium text-muted">Extracted fields</h3>
              {selected.extracted_fields.length === 0 ? (
                <p className="text-sm text-muted mt-2">No fields extracted.</p>
              ) : (
                <ul className="mt-2 space-y-1.5">
                  {selected.extracted_fields.map((f) => (
                    <li key={f.id} className="text-sm flex gap-2">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-panel2 border border-border text-accent2">{f.field_type}</span>
                      <span className="text-muted">{f.field_name}:</span>
                      <span>{f.field_value}</span>
                    </li>
                  ))}
                </ul>
              )}

              {/* Agent trace (F2.2) */}
              {selected.agent_trace?.length > 0 && (
                <details className="mt-5">
                  <summary className="text-sm font-medium text-muted cursor-pointer">How this was extracted (agent trace)</summary>
                  <ol className="mt-2 space-y-2">
                    {selected.agent_trace.map((s, i) => (
                      <li key={i} className="text-xs rounded-lg bg-panel2 border border-border p-2 font-mono">
                        {JSON.stringify(s)}
                      </li>
                    ))}
                  </ol>
                </details>
              )}

              {/* Share (F2.8) */}
              <h3 className="mt-6 text-sm font-medium text-muted">Share</h3>
              <div className="mt-2 flex gap-2">
                <input
                  value={shareEmail} onChange={(e) => setShareEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="flex-1 rounded-lg bg-panel2 border border-border px-3 py-2 text-sm outline-none focus:border-accent"
                />
                <button onClick={share} className="text-sm px-3 rounded-lg bg-accent hover:bg-accent2">Share</button>
              </div>
              {shareMsg && <p className="mt-2 text-xs text-muted">{shareMsg}</p>}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
