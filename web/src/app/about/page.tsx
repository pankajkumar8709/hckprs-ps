"use client";
import { motion } from "framer-motion";
import {
  Upload, Tags, ScanText, ShieldCheck, BellRing, Lightbulb,
  MessagesSquare, Share2,
} from "lucide-react";
import PublicHeader from "@/components/PublicHeader";

const phase1 = [
  { icon: Upload, title: "Document upload", desc: "Upload PDFs, text, or scanned images — text is extracted automatically with OCR fallback." },
  { icon: ScanText, title: "AI extraction", desc: "A single LLM pass pulls document type, key dates, amounts, parties and a summary." },
  { icon: MessagesSquare, title: "Ask your documents", desc: "Plain-language answers grounded only in your own uploads — it refuses when it doesn't know." },
];
const phase2 = [
  { icon: Tags, title: "Multi-document-type support", desc: "A classification agent labels each document with a confidence score." },
  { icon: ShieldCheck, title: "Verified extraction pipeline", desc: "A validator checks every date and amount against the source and rejects anything unverifiable." },
  { icon: BellRing, title: "Automatic reminders", desc: "Deadlines become reminders automatically — no manual entry." },
  { icon: Lightbulb, title: "Cross-document insights", desc: "Spots clashing due dates and upcoming renewal risks across all documents." },
  { icon: Share2, title: "Document sharing", desc: "Share view-only or editable, with an optional expiry." },
];

function Grid({ items }: { items: { icon: any; title: string; desc: string }[] }) {
  return (
    <motion.div variants={{ show: { transition: { staggerChildren: 0.06 } } }} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}
      className="grid gap-4 sm:grid-cols-2">
      {items.map((f) => {
        const Icon = f.icon;
        return (
          <motion.div key={f.title} variants={{ hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }}
            className="bg-surface border border-border rounded-2xl shadow-card p-5 transition-all hover:-translate-y-0.5 hover:shadow-card-hover">
            <span className="h-10 w-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
              <Icon size={19} />
            </span>
            <h3 className="mt-3 font-semibold text-ink">{f.title}</h3>
            <p className="mt-1.5 text-sm text-body">{f.desc}</p>
          </motion.div>
        );
      })}
    </motion.div>
  );
}

export default function About() {
  return (
    <div className="min-h-screen bg-hero-gradient">
      <PublicHeader />
      <section className="max-w-4xl mx-auto px-6 py-14">
        <motion.h1 initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="text-3xl sm:text-4xl font-bold text-ink tracking-tight">
          What LifeOS does today
        </motion.h1>
        <p className="mt-3 text-body max-w-2xl">
          Everything below is built and working against the live backend — the real feature set, not a roadmap.
        </p>

        <div className="mt-10">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-xl font-semibold text-ink">The core loop</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-600 border border-indigo-100">Phase 1</span>
          </div>
          <Grid items={phase1} />
        </div>

        <div className="mt-12">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-xl font-semibold text-ink">Productized</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-600 border border-indigo-100">Phase 2</span>
          </div>
          <Grid items={phase2} />
        </div>
      </section>
    </div>
  );
}
