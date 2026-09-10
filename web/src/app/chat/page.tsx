"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, Send, Search, Plus, MessageSquare, History, X, Trash2, PanelRightClose, PanelRightOpen } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import { CitationCard } from "@/components/domain";
import { AIMessage } from "@/components/AIMessage";
import { api, chatStream, type Conversation } from "@/lib/api";

interface Bubble {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: { document_id: string; filename: string }[];
}

const SUGGESTIONS = [
  "What deadlines are near?",
  "Remind me to renew insurance next Friday",
  "What is my insurance renewal date?",
  "Are there any conflicts?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Bubble[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("Searching your documents…");
  const [convId, setConvId] = useState<string | undefined>();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);
  const [loadingConv, setLoadingConv] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const loadConversations = useCallback(async () => {
    try { setConversations(await api.listConversations()); } catch { /* ignore */ }
  }, []);
  useEffect(() => { loadConversations(); }, [loadConversations]);

  function newChat() {
    setConvId(undefined);
    setMessages([]);
    setHistoryOpen(false);
  }

  async function deleteConv(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      if (convId === id) newChat();
      await loadConversations();
    } catch { /* ignore */ }
  }

  async function clearAll() {
    if (!confirm("Delete all chat history? This cannot be undone.")) return;
    try {
      await api.clearConversations();
      newChat();
      await loadConversations();
    } catch { /* ignore */ }
  }

  async function openConversation(id: string) {
    setLoadingConv(true);
    setHistoryOpen(false);
    try {
      const msgs = await api.getMessages(id);
      setConvId(id);
      setMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role === "user" ? "user" : "assistant",
          content: m.content || "",
        }))
      );
    } catch { /* ignore */ } finally { setLoadingConv(false); }
  }

  async function sendText(text: string) {
    if (!text.trim() || loading) return;
    setInput("");
    const assistantId = `a-${Date.now()}`;
    const isNew = !convId;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    const stages = ["Searching your documents…", "Retrieving relevant information…", "Preparing answer…"];
    let si = 0; setStage(stages[0]);
    const timer = setInterval(() => { si = Math.min(si + 1, stages.length - 1); setStage(stages[si]); }, 900);

    let acc = "";
    let citations: { document_id: string; filename: string }[] = [];
    let bubbleAdded = false;
    const addBubbleOnce = () => {
      if (bubbleAdded) return;
      bubbleAdded = true;
      clearInterval(timer); setLoading(false);
      setMessages((m) => [...m, { id: assistantId, role: "assistant", content: "", citations }]);
    };
    const updateBubble = () => {
      setMessages((m) => m.map((b) => (b.id === assistantId ? { ...b, content: acc, citations } : b)));
    };

    await chatStream(text, convId, {
      onMeta: (meta) => { setConvId(meta.conversation_id); citations = meta.citations || []; },
      onDelta: (chunk) => { addBubbleOnce(); acc += chunk; updateBubble(); },
      onDone: () => { clearInterval(timer); setLoading(false); addBubbleOnce(); updateBubble();
        if (isNew) loadConversations(); },
      onError: (msg) => { clearInterval(timer); setLoading(false);
        setMessages((m) => [...m, { role: "assistant", content: msg }]); },
    });
  }

  const HistoryList = (
    <div className="flex flex-col h-full">
      {/* Aligned header (same height as chat header: h-[68px]) */}
      <div className="h-[68px] shrink-0 px-4 flex items-center border-b border-border">
        <button onClick={newChat}
          className="w-full flex items-center gap-2 justify-center rounded-xl bg-brand-gradient text-white text-sm font-medium py-2.5 shadow-soft hover:shadow-card-hover transition-all">
          <Plus size={16} /> New chat
        </button>
      </div>
      {/* Scrollable list */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        <div className="px-2 pb-1 flex items-center justify-between">
          <span className="text-xs font-semibold text-muted uppercase tracking-wide">Recent chats</span>
          {conversations.length > 0 && (
            <button onClick={clearAll}
              className="text-xs text-muted hover:text-danger flex items-center gap-1 transition-colors">
              <Trash2 size={12} /> Clear all
            </button>
          )}
        </div>
        {conversations.length === 0 && (
          <p className="px-2 py-3 text-sm text-muted">No conversations yet.</p>
        )}
        {conversations.map((c) => (
          <div key={c.id}
            className={`group w-full rounded-lg px-3 py-2 text-sm transition-colors flex items-start gap-2.5 cursor-pointer ${
              convId === c.id ? "bg-brand-50 text-brand-600" : "text-body hover:bg-subtle hover:text-ink"
            }`}
            onClick={() => openConversation(c.id)}>
            <MessageSquare size={15} className="mt-0.5 shrink-0" />
            <span className="min-w-0 flex-1">
              <span className="block truncate leading-tight">{c.title || "Untitled chat"}</span>
              <span className="block text-xs text-muted mt-0.5">{new Date(c.created_at).toLocaleDateString()}</span>
            </span>
            <button onClick={(e) => deleteConv(c.id, e)} aria-label="Delete conversation"
              className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger shrink-0 transition-opacity mt-0.5">
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <AppLayout title="AI Assistant">
      <div className="flex h-[calc(100vh-4rem)]">
        {/* Chat column */}
        <div className="flex-1 min-w-0 flex flex-col bg-canvas">
          {/* Chat header */}
          <div className="h-[68px] shrink-0 px-5 sm:px-6 flex items-center gap-3 border-b border-border bg-surface">
            <span className="h-9 w-9 rounded-xl bg-brand-gradient text-white flex items-center justify-center"><Sparkles size={18} /></span>
            <div className="min-w-0">
              <h1 className="font-semibold text-ink leading-tight">AI Assistant</h1>
              <p className="text-xs text-body truncate">Ask questions about your documents</p>
            </div>
            {/* History toggle (right side) */}
            <button
              onClick={() => { setHistoryCollapsed((v) => !v); setHistoryOpen(true); }}
              className="ml-auto flex items-center gap-1.5 text-sm text-body border border-border rounded-lg px-3 py-1.5 hover:border-ring hover:text-ink transition-colors"
              aria-label="Toggle chat history"
            >
              {historyCollapsed ? <PanelRightOpen size={16} /> : <PanelRightClose size={16} />}
              <span className="hidden sm:inline">History</span>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
            <div className="max-w-3xl mx-auto space-y-5">
              {loadingConv && <p className="text-center text-sm text-muted">Loading conversation…</p>}

              {messages.length === 0 && !loading && !loadingConv && (
                <div className="text-center py-10">
                  <span className="mx-auto h-14 w-14 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center"><Sparkles size={26} /></span>
                  <h2 className="mt-4 text-lg font-semibold text-ink">Your document assistant</h2>
                  <p className="mt-1 text-sm text-body">Ask anything about your documents.</p>
                  <div className="mt-6 grid gap-2 sm:grid-cols-2 max-w-lg mx-auto">
                    {SUGGESTIONS.map((s) => (
                      <button key={s} onClick={() => sendText(s)}
                        className="text-left text-sm bg-surface border border-border rounded-xl px-4 py-3 text-body hover:border-ring hover:shadow-card transition-all">
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={m.id || i} className="flex justify-end">
                    <div className="max-w-[80%] bg-brand-gradient text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm">{m.content}</div>
                  </div>
                ) : (
                  <div key={m.id || i} className="flex justify-start">
                    <div className="max-w-[85%] bg-surface border border-border rounded-2xl rounded-bl-md shadow-card p-4">
                      <div className="flex items-center gap-1.5 text-xs font-medium text-brand-600 mb-2"><Sparkles size={13} /> AI Assistant</div>
                      <AIMessage text={m.content} />
                      {m.citations && m.citations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-border">
                          <div className="text-xs text-muted mb-1.5">Sources</div>
                          <div className="flex flex-wrap gap-1.5">
                            {m.citations.map((c) => <CitationCard key={c.document_id} filename={c.filename} />)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )
              )}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-surface border border-border rounded-2xl rounded-bl-md shadow-card px-4 py-3 flex items-center gap-2 text-sm text-body">
                    <Search size={15} className="text-brand-600 animate-pulse" /> {stage}
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>
          </div>

          {/* Composer */}
          <div className="border-t border-border bg-surface p-4">
            <form onSubmit={(e) => { e.preventDefault(); sendText(input); }} className="max-w-3xl mx-auto flex gap-3">
              <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask anything about your documents…"
                className="flex-1 rounded-xl bg-canvas border border-border px-4 py-3 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-ring" />
              <button type="submit" disabled={loading || !input.trim()}
                className="h-12 w-12 shrink-0 rounded-xl bg-brand-gradient text-white flex items-center justify-center shadow-soft hover:shadow-card-hover disabled:opacity-50 transition-all" aria-label="Send">
                <Send size={18} />
              </button>
            </form>
          </div>
        </div>

        {/* History panel — RIGHT side, collapsible (desktop) */}
        <div className={`hidden md:flex shrink-0 border-l border-border bg-surface overflow-hidden transition-all duration-300 ${historyCollapsed ? "w-0 border-l-0" : "w-72"}`}>
          <div className="w-72">{HistoryList}</div>
        </div>

        {/* History drawer — right, mobile */}
        {historyOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={() => setHistoryOpen(false)} />
            <div className="absolute right-0 top-0 h-full w-72 bg-surface border-l border-border animate-fade-up">{HistoryList}</div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
