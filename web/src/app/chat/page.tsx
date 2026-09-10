"use client";
import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import AppLayout from "@/components/AppLayout";
import { api, ApiError, type ChatResponse } from "@/lib/api";

interface Bubble {
  role: "user" | "assistant";
  content: string;
  citations?: { document_id: string; filename: string }[];
  intent?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState<string | undefined>();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res: ChatResponse = await api.chat(text, convId);
      setConvId(res.conversation_id);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.message.content || "",
          citations: res.citations,
          intent: res.intent,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: err instanceof ApiError ? err.message : "Something went wrong.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppLayout>
      <div className="flex flex-col h-screen">
        <header className="px-6 py-4 border-b border-border">
          <h1 className="font-semibold">Chat</h1>
          <p className="text-xs text-muted">Ask about your documents — answers are grounded in your uploads.</p>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-muted text-sm mt-10 text-center">
              Try “When does my lease end?” or “What reminders do I have?”
            </div>
          )}
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`max-w-2xl ${m.role === "user" ? "ml-auto" : ""}`}
            >
              <div
                className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-accent text-white"
                    : "bg-panel border border-border"
                }`}
              >
                {m.content}
              </div>
              {m.role === "assistant" && m.citations && m.citations.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {m.citations.map((c) => (
                    <span key={c.document_id} className="text-xs px-2 py-0.5 rounded-full bg-panel2 border border-border text-muted">
                      from: {c.filename}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
          {loading && <div className="text-sm text-muted">Thinking…</div>}
          <div ref={endRef} />
        </div>

        <form onSubmit={send} className="p-4 border-t border-border flex gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question…"
            className="flex-1 rounded-lg bg-panel2 border border-border px-4 py-2.5 outline-none focus:border-accent"
          />
          <button
            type="submit" disabled={loading}
            className="px-5 rounded-lg bg-accent hover:bg-accent2 disabled:opacity-60 transition-colors font-medium"
          >
            Ask
          </button>
        </form>
      </div>
    </AppLayout>
  );
}
