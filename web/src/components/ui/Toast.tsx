"use client";
import { createContext, useContext, useCallback, useState } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

type Tone = "success" | "error" | "info";
interface Toast { id: number; tone: Tone; message: string; }

const ToastCtx = createContext<{
  toast: (message: string, tone?: Tone) => void;
}>({ toast: () => {} });

export function useToast() {
  return useContext(ToastCtx);
}

const icons = { success: CheckCircle2, error: AlertCircle, info: Info };
const toneCls = {
  success: "border-green-200 text-success",
  error: "border-red-200 text-danger",
  info: "border-indigo-100 text-brand-600",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, tone: Tone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, tone, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  return (
    <ToastCtx.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-full max-w-sm px-4 sm:px-0">
        {toasts.map((t) => {
          const Icon = icons[t.tone];
          return (
            <div
              key={t.id}
              role="status"
              className={`glass border ${toneCls[t.tone]} rounded-xl shadow-card-hover px-4 py-3 flex items-start gap-3 animate-fade-up`}
            >
              <Icon size={18} className="mt-0.5 shrink-0" />
              <p className="text-sm text-ink flex-1">{t.message}</p>
              <button
                aria-label="Dismiss"
                onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))}
                className="text-muted hover:text-ink"
              >
                <X size={16} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastCtx.Provider>
  );
}
