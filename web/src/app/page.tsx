"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Sparkles, FileSearch, ScanText, ShieldCheck, BellRing, Lightbulb,
  MessagesSquare, Share2, Crown, ArrowRight, CheckCircle2, Lock,
  Upload, Tags, ListChecks, Brain,
} from "lucide-react";
import PublicHeader from "@/components/PublicHeader";

const features = [
  { icon: Tags, title: "AI Classification", desc: "Automatically understands what each document is — lease, insurance, loan, and more." },
  { icon: ScanText, title: "Intelligent Extraction", desc: "Pulls key dates, amounts, parties and a summary in a single pass." },
  { icon: ShieldCheck, title: "Deterministic Validation", desc: "Every extracted fact is verified against the source text before it's saved." },
  { icon: BellRing, title: "Automatic Reminders", desc: "Deadlines become reminders automatically — zero manual entry." },
  { icon: Lightbulb, title: "Cross-Document Insights", desc: "Spots clashing dates and renewal risks across everything you upload." },
  { icon: MessagesSquare, title: "RAG Document Chat", desc: "Ask questions in plain language, grounded only in your own documents." },
  { icon: Share2, title: "Secure Sharing", desc: "Share documents with view/edit permissions and optional expiry." },
  { icon: Crown, title: "Premium Plans", desc: "Start free, upgrade for unlimited documents and advanced insights." },
];

const pipeline = [
  { icon: Upload, label: "Upload" },
  { icon: Tags, label: "Classify" },
  { icon: ScanText, label: "Extract" },
  { icon: ShieldCheck, label: "Validate" },
  { icon: BellRing, label: "Remind" },
  { icon: Brain, label: "Understand" },
];

const security = [
  { icon: Lock, title: "User isolation", desc: "Every query is scoped to your user ID at the database level." },
  { icon: ShieldCheck, title: "Server-side access control", desc: "Document access is enforced on the server — never trusting the client." },
  { icon: Share2, title: "Scoped, expirable sharing", desc: "Grants are permission-bound and can expire." },
  { icon: CheckCircle2, title: "Validated before persistence", desc: "No hallucinated fact is ever stored." },
  { icon: FileSearch, title: "No cross-user RAG leakage", desc: "Retrieval filters by user at the SQL layer, not the prompt." },
];

const fade = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function Landing() {
  return (
    <div className="min-h-screen bg-hero-gradient">
      <PublicHeader />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-16 pb-12 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 text-xs font-medium text-brand-600 bg-brand-50 border border-indigo-100 rounded-full px-3 py-1">
            <Sparkles size={13} /> AI Document Intelligence
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.05 }}
            className="mt-4 text-4xl sm:text-5xl font-bold text-ink tracking-tight leading-[1.1]">
            Your documents become <span className="bg-brand-gradient bg-clip-text text-transparent">intelligent</span>, searchable, actionable knowledge.
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.12 }}
            className="mt-5 text-lg text-body max-w-lg">
            Upload a document and LifeOS classifies it, extracts the key facts, verifies them, tracks the deadlines, and answers your questions.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.19 }}
            className="mt-8 flex flex-wrap gap-3">
            <Link href="/signup" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-gradient text-white font-medium shadow-soft hover:shadow-card-hover hover:brightness-105 transition-all">
              Get Started <ArrowRight size={17} />
            </Link>
            <Link href="/about" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-border bg-surface text-ink hover:border-ring transition-colors">
              Explore Features
            </Link>
          </motion.div>
        </div>

        {/* Animated pipeline visual */}
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6, delay: 0.15 }}
          className="relative">
          <div className="bg-surface border border-border rounded-2xl shadow-card p-5 animate-float">
            <div className="flex items-center gap-2 text-sm font-medium text-ink">
              <FileSearch size={16} className="text-brand-600" /> insurance_policy.pdf
            </div>
            <div className="mt-4 space-y-2.5">
              {["AI Classification", "Data Extraction", "Validation", "Reminder Created"].map((s, i) => (
                <motion.div key={s} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + i * 0.15 }}
                  className="flex items-center gap-2 text-sm text-body">
                  <CheckCircle2 size={16} className="text-success" /> {s}
                </motion.div>
              ))}
            </div>
          </div>
          <div className="mx-auto my-2 h-6 w-px bg-border" />
          <div className="bg-surface border border-border rounded-2xl shadow-card p-5">
            <div className="text-sm font-medium text-ink flex items-center gap-2">
              <Lightbulb size={16} className="text-brand-600" /> Intelligent Insights
            </div>
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2 text-sm text-warning bg-warning-50 border border-amber-200 rounded-lg px-3 py-2">
                <BellRing size={15} /> Renewal approaching
              </div>
              <div className="flex items-center gap-2 text-sm text-danger bg-danger-50 border border-red-200 rounded-lg px-3 py-2">
                <ShieldCheck size={15} /> Deadline conflict
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold text-ink tracking-tight">Everything your documents need</h2>
          <p className="mt-3 text-body">A complete document intelligence pipeline, built and working today.</p>
        </div>
        <motion.div variants={{ show: { transition: { staggerChildren: 0.06 } } }} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.15 }}
          className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <motion.div key={f.title} variants={fade}
                className="group bg-surface border border-border rounded-2xl shadow-card p-5 transition-all duration-200 hover:-translate-y-1 hover:shadow-card-hover hover:border-ring">
                <span className="h-10 w-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center transition-transform group-hover:scale-110">
                  <Icon size={20} />
                </span>
                <h3 className="mt-4 font-semibold text-ink">{f.title}</h3>
                <p className="mt-1.5 text-sm text-body">{f.desc}</p>
              </motion.div>
            );
          })}
        </motion.div>
      </section>

      {/* How it works */}
      <section className="bg-surface border-y border-border py-16">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-ink tracking-tight">How it works</h2>
          <p className="mt-3 text-body">Six stages, fully automated.</p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            {pipeline.map((p, i) => {
              const Icon = p.icon;
              return (
                <motion.div key={p.label} className="flex items-center gap-3"
                  initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }} transition={{ delay: i * 0.08 }}>
                  <div className="flex flex-col items-center gap-2">
                    <span className="h-12 w-12 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center">
                      <Icon size={22} />
                    </span>
                    <span className="text-sm font-medium text-ink">{p.label}</span>
                  </div>
                  {i < pipeline.length - 1 && (
                    <ArrowRight size={18} className="text-muted hidden sm:block" />
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Security */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-medium text-brand-600 bg-brand-50 border border-indigo-100 rounded-full px-3 py-1">
              <Lock size={13} /> Secure by design
            </div>
            <h2 className="mt-4 text-3xl font-bold text-ink tracking-tight">Your documents stay yours</h2>
            <p className="mt-3 text-body max-w-md">
              Isolation isn't a promise in the prompt — it's enforced in the database and on the server, on every request.
            </p>
          </div>
          <div className="space-y-3">
            {security.map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.title} className="flex gap-3 bg-surface border border-border rounded-xl p-4 shadow-card">
                  <span className="h-9 w-9 shrink-0 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
                    <Icon size={17} />
                  </span>
                  <div>
                    <div className="font-medium text-ink text-sm">{s.title}</div>
                    <div className="text-sm text-body mt-0.5">{s.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-8 text-center text-sm text-muted">
        LifeOS — AI Document Intelligence
      </footer>
    </div>
  );
}
