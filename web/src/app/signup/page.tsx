"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sparkles, ArrowLeft } from "lucide-react";
import { api, setTokens, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.register(email, password, fullName || undefined);
      const res = await api.login(email, password);
      setTokens(res.access_token, res.refresh_token);
      router.replace("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-hero-gradient flex items-center justify-center px-6">
      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
        className="w-full max-w-sm">
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-body hover:text-ink mb-4">
          <ArrowLeft size={15} /> Home
        </Link>
        <div className="bg-surface border border-border rounded-2xl shadow-card p-7">
          <span className="h-10 w-10 rounded-xl bg-brand-gradient flex items-center justify-center text-white">
            <Sparkles size={19} />
          </span>
          <h1 className="mt-4 text-2xl font-bold text-ink tracking-tight">Create your account</h1>
          <p className="text-sm text-body mt-1">Start understanding your documents.</p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm text-body mb-1">Full name (optional)</label>
              <input id="name" value={fullName} onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-xl bg-canvas border border-border px-3.5 py-2.5 text-ink outline-none focus:border-brand focus:ring-2 focus:ring-ring transition"
                placeholder="Jane Doe" />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm text-body mb-1">Email</label>
              <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl bg-canvas border border-border px-3.5 py-2.5 text-ink outline-none focus:border-brand focus:ring-2 focus:ring-ring transition"
                placeholder="you@example.com" />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm text-body mb-1">Password</label>
              <input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl bg-canvas border border-border px-3.5 py-2.5 text-ink outline-none focus:border-brand focus:ring-2 focus:ring-ring transition"
                placeholder="At least 8 characters" />
            </div>
            {error && (
              <p className="text-sm text-danger bg-danger-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
            )}
            <Button type="submit" size="lg" disabled={loading} className="w-full">
              {loading ? "Creating…" : "Sign up"}
            </Button>
          </form>
          <p className="mt-5 text-sm text-body text-center">
            Already have an account? <Link href="/login" className="text-brand-600 font-medium hover:underline">Log in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
