"use client";
import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { FileText } from "lucide-react";
import { Card } from "@/components/ui/Card";

/** Animated counting number. Respects reduced motion by jumping to value. */
export function Counter({ value, duration = 900 }: { value: number; duration?: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce || value === 0) { setN(value); return; }
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      setN(Math.round(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{n}</>;
}

export function StatCard({
  icon: Icon, label, value, hint, tone = "brand",
}: {
  icon: LucideIcon; label: string; value: number; hint?: string;
  tone?: "brand" | "warning" | "danger";
}) {
  const toneCls = {
    brand: "bg-brand-50 text-brand-600",
    warning: "bg-warning-50 text-warning",
    danger: "bg-danger-50 text-danger",
  }[tone];
  return (
    <Card hover className="animate-fade-up">
      <div className="flex items-start justify-between">
        <span className="text-sm text-body">{label}</span>
        <span className={`h-9 w-9 rounded-xl flex items-center justify-center ${toneCls}`}>
          <Icon size={18} />
        </span>
      </div>
      <div className="mt-3 text-3xl font-semibold text-ink tabular-nums">
        <Counter value={value} />
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </Card>
  );
}

/** Visual multi-agent trace (F2.2). steps: [{agent, action, ...}]. */
export function AgentTrace({ steps }: { steps: Array<Record<string, unknown>> }) {
  if (!steps?.length) return null;
  return (
    <ol className="relative ml-2 space-y-3 border-l-2 border-border pl-5">
      {steps.map((s, i) => {
        const agent = String(s.agent ?? "Step");
        const rejected = Number((s as any).rejected ?? 0);
        const accepted = (s as any).accepted;
        return (
          <li key={i} className="relative">
            <span className="absolute -left-[27px] top-0.5 h-4 w-4 rounded-full bg-brand-gradient ring-4 ring-surface" />
            <div className="text-sm font-medium text-ink">{agent}</div>
            <div className="text-xs text-body mt-0.5 space-x-2">
              {accepted !== undefined && <span>{String(accepted)} accepted</span>}
              {rejected > 0 && (
                <span className="text-danger">{rejected} rejected</span>
              )}
              {(s as any).doc_type && <span>type: {String((s as any).doc_type)}</span>}
              {(s as any).fields_found !== undefined && (
                <span>{String((s as any).fields_found)} fields</span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function CitationCard({
  filename, onOpen,
}: { filename: string; onOpen?: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="inline-flex items-center gap-2 text-xs bg-subtle border border-border rounded-lg px-2.5 py-1.5 text-body hover:border-ring hover:text-ink transition-colors"
    >
      <FileText size={14} className="text-brand-600" />
      {filename}
    </button>
  );
}
