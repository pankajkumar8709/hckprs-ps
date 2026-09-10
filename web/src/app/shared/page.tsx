"use client";
import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { api, ApiError, type DocumentSummary, type DocumentDetail } from "@/lib/api";

export default function SharedPage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setDocs(await api.sharedWithMe());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load shared documents");
      }
    })();
  }, []);

  async function open(id: string) {
    try {
      setSelected(await api.getDocument(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to open document");
    }
  }

  return (
    <AppLayout>
      <div className="h-screen grid grid-cols-2">
        <div className="border-r border-border overflow-y-auto p-6">
          <h1 className="font-semibold">Shared with me</h1>
          <p className="text-xs text-muted">Documents other users have shared with you.</p>
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          <div className="mt-4 space-y-2">
            {docs.length === 0 && <p className="text-sm text-muted">Nothing shared with you yet.</p>}
            {docs.map((d) => (
              <button key={d.id} onClick={() => open(d.id)}
                className={`w-full text-left rounded-xl border p-3 transition-colors ${
                  selected?.id === d.id ? "border-accent bg-panel2" : "border-border bg-panel hover:border-accent2"}`}>
                <div className="font-medium text-sm truncate">{d.filename}</div>
                <span className="mt-1 inline-block px-2 py-0.5 rounded-full border border-border text-muted text-xs uppercase">{d.doc_type}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-y-auto p-6">
          {!selected ? (
            <p className="text-sm text-muted mt-10 text-center">Select a shared document to view it.</p>
          ) : (
            <div>
              <h2 className="font-semibold">{selected.filename}</h2>
              <h3 className="mt-5 text-sm font-medium text-muted">Extracted fields</h3>
              <ul className="mt-2 space-y-1.5">
                {selected.extracted_fields.map((f) => (
                  <li key={f.id} className="text-sm flex gap-2">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-panel2 border border-border text-accent2">{f.field_type}</span>
                    <span className="text-muted">{f.field_name}:</span>
                    <span>{f.field_value}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
