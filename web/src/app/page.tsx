"use client";
import Link from "next/link";
import { motion } from "framer-motion";
import PublicHeader from "@/components/PublicHeader";

const steps = [
  { icon: "📄", title: "Upload", desc: "Drop in a lease, policy, or bill — PDF, text, or a scan." },
  { icon: "🧠", title: "Understand", desc: "AI agents classify it, pull the key dates & amounts, and verify them against the source." },
  { icon: "✅", title: "Act", desc: "Get automatic reminders, cross-document insights, and answers you can ask in plain language." },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.15 } },
};
const item = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function Landing() {
  return (
    <div className="min-h-screen">
      <PublicHeader />

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="text-4xl sm:text-6xl font-bold leading-tight"
        >
          Your documents, <span className="text-accent2">understood.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
          className="mt-5 text-lg sm:text-xl text-muted max-w-2xl mx-auto"
        >
          LifeOS Agent reads your leases, policies and bills, tracks every deadline
          for you, and answers questions about them in plain language.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: "easeOut" }}
          className="mt-9 flex items-center justify-center gap-4"
        >
          <Link
            href="/signup"
            className="px-6 py-3 rounded-xl bg-accent hover:bg-accent2 transition-colors font-medium"
          >
            Get started free
          </Link>
          <Link
            href="/about"
            className="px-6 py-3 rounded-xl border border-border hover:border-accent transition-colors"
          >
            See what it does
          </Link>
        </motion.div>
      </section>

      {/* Core loop */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
          className="grid gap-5 sm:grid-cols-3"
        >
          {steps.map((s, i) => (
            <motion.div
              key={s.title}
              variants={item}
              className="relative rounded-2xl border border-border bg-panel p-6"
            >
              <div className="text-3xl">{s.icon}</div>
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs font-mono text-accent2">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="text-lg font-semibold">{s.title}</h3>
              </div>
              <p className="mt-2 text-sm text-muted">{s.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>
    </div>
  );
}
