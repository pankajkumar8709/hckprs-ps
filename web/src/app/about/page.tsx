"use client";
import { motion } from "framer-motion";
import PublicHeader from "@/components/PublicHeader";

const phase1 = [
  { title: "Document upload", desc: "Upload PDFs, text, or scanned images. Text is extracted automatically (with OCR fallback for scans)." },
  { title: "AI extraction", desc: "A single-shot LLM pass pulls a document's type, key dates, amounts, parties and a plain-language summary." },
  { title: "Ask your documents", desc: "Ask questions in plain language and get answers grounded only in your own uploaded documents." },
];

const phase2 = [
  { title: "Multi-document-type support", desc: "A classification agent labels each document (lease, insurance, loan, subscription, medical, other) with a confidence score." },
  { title: "Verified extraction pipeline", desc: "A two-agent pipeline extracts fields, then a validator checks every date and amount against the source text and rejects anything it can't verify." },
  { title: "Automatic reminders", desc: "Deadlines found in your documents become reminders automatically — no manual entry." },
  { title: "Cross-document insights", desc: "Spots clashing due dates and upcoming renewal risks across all your documents." },
  { title: "Document sharing", desc: "Share a document with another user, view-only or editable, with an optional expiry." },
];

const item = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

function Group({ label, tag, features }: { label: string; tag: string; features: { title: string; desc: string }[] }) {
  return (
    <div className="mb-12">
      <div className="flex items-center gap-3 mb-5">
        <h2 className="text-2xl font-semibold">{label}</h2>
        <span className="text-xs px-2 py-1 rounded-full border border-border text-accent2">{tag}</span>
      </div>
      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
        transition={{ staggerChildren: 0.08 }}
        className="grid gap-4 sm:grid-cols-2"
      >
        {features.map((f) => (
          <motion.div key={f.title} variants={item} className="rounded-xl border border-border bg-panel p-5">
            <h3 className="font-medium">{f.title}</h3>
            <p className="mt-1.5 text-sm text-muted">{f.desc}</p>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}

export default function About() {
  return (
    <div className="min-h-screen">
      <PublicHeader />
      <section className="max-w-4xl mx-auto px-6 py-14">
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-3xl sm:text-4xl font-bold"
        >
          What LifeOS Agent does today
        </motion.h1>
        <p className="mt-3 text-muted max-w-2xl">
          Everything below is built and working right now against the live backend.
          This is the real feature set — not a roadmap.
        </p>
        <div className="mt-10">
          <Group label="The core loop" tag="Phase 1" features={phase1} />
          <Group label="Productized" tag="Phase 2" features={phase2} />
        </div>
      </section>
    </div>
  );
}
