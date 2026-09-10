"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { api, setTokens, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(email, password);
      setTokens(res.access_token, res.refresh_token);
      router.replace("/chat");
    } catch (err) {
      // Surface the REAL backend message (e.g. "Invalid credentials").
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <motion.form
        onSubmit={onSubmit}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-sm rounded-2xl border border-border bg-panel p-7"
      >
        <Link href="/" className="text-sm text-muted hover:text-white">← Home</Link>
        <h1 className="mt-3 text-2xl font-bold">Welcome back</h1>
        <p className="text-sm text-muted mt-1">Log in to your LifeOS account.</p>

        <label className="block mt-6 text-sm">Email</label>
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded-lg bg-panel2 border border-border px-3 py-2 outline-none focus:border-accent"
          placeholder="you@example.com"
        />
        <label className="block mt-4 text-sm">Password</label>
        <input
          type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-lg bg-panel2 border border-border px-3 py-2 outline-none focus:border-accent"
          placeholder="••••••••"
        />

        {error && (
          <p className="mt-4 text-sm text-red-400 bg-red-950/40 border border-red-900 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit" disabled={loading}
          className="mt-6 w-full rounded-lg bg-accent hover:bg-accent2 disabled:opacity-60 transition-colors py-2.5 font-medium"
        >
          {loading ? "Logging in…" : "Log in"}
        </button>
        <p className="mt-4 text-sm text-muted text-center">
          No account?{" "}
          <Link href="/signup" className="text-accent2 hover:underline">Sign up</Link>
        </p>
      </motion.form>
    </div>
  );
}
