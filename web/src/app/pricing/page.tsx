"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check, Crown, Sparkles, Zap, Building2, CreditCard, Lock, ShieldCheck, X,
} from "lucide-react";
import AppLayout from "@/components/AppLayout";
import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/components/ui/Toast";
import { api, ApiError, type PlanInfo } from "@/lib/api";

type Plan = {
  id: string;
  name: string;
  icon: any;
  monthly: number;
  yearly: number; // per-month when billed yearly
  tagline: string;
  features: string[];
  highlight?: boolean;
  premium: boolean; // flips the backend to "premium" on purchase
};

const PLANS: Plan[] = [
  {
    id: "free", name: "Free", icon: Sparkles, monthly: 0, yearly: 0,
    tagline: "For trying LifeOS out",
    features: ["Up to 10 documents", "AI extraction & Q&A", "Reminders & insights", "Community support"],
    premium: false,
  },
  {
    id: "plus", name: "Plus", icon: Zap, monthly: 9, yearly: 7,
    tagline: "For staying on top of life admin",
    features: ["Up to 100 documents", "Priority AI insights", "Calendar (.ics) export", "Email support"],
    premium: true,
  },
  {
    id: "pro", name: "Pro", icon: Crown, monthly: 19, yearly: 15,
    tagline: "For power users",
    features: ["Unlimited documents", "Advanced cross-doc insights", "Document sharing", "Priority support", "Early access to new AI features"],
    highlight: true, premium: true,
  },
  {
    id: "business", name: "Business", icon: Building2, monthly: 49, yearly: 39,
    tagline: "For teams & households",
    features: ["Everything in Pro", "Team workspaces", "Audit-log exports", "Role-based sharing", "Dedicated support"],
    premium: true,
  },
];

export default function PricingPage() {
  const { toast } = useToast();
  const router = useRouter();
  const [yearly, setYearly] = useState(false);
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [checkout, setCheckout] = useState<Plan | null>(null);

  useEffect(() => { api.getPlan().then(setPlan).catch(() => {}); }, []);

  const isPremium = plan?.plan_tier === "premium";

  return (
    <AppLayout title="Plans & Pricing">
      <div className="p-4 sm:p-6 max-w-6xl mx-auto">
        <PageHeader title="Plans & Pricing" subtitle="Choose the plan that fits your life. Cancel anytime." />

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <span className={`text-sm ${!yearly ? "text-ink font-medium" : "text-muted"}`}>Monthly</span>
          <button
            onClick={() => setYearly(!yearly)}
            className="relative h-6 w-11 rounded-full bg-subtle transition-colors"
            aria-label="Toggle yearly billing"
          >
            <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-brand-gradient transition-transform ${yearly ? "translate-x-5" : "translate-x-0.5"}`} />
          </button>
          <span className={`text-sm ${yearly ? "text-ink font-medium" : "text-muted"}`}>
            Yearly <span className="text-emerald-600 font-medium">(save ~20%)</span>
          </span>
        </div>

        {/* Plan grid */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((p) => {
            const Icon = p.icon;
            const price = yearly ? p.yearly : p.monthly;
            const isCurrent = (p.id === "free" && !isPremium) || (p.premium && isPremium);
            return (
              <div
                key={p.id}
                className={`relative rounded-2xl border p-5 flex flex-col ${
                  p.highlight ? "border-brand-400 shadow-lg ring-2 ring-brand-100" : "border-border shadow-card"
                } bg-surface`}
              >
                {p.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-gradient text-white text-xs font-semibold px-3 py-1">
                    Most popular
                  </span>
                )}
                <div className="flex items-center gap-2">
                  <span className="h-9 w-9 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                    <Icon size={18} />
                  </span>
                  <h3 className="font-semibold text-ink">{p.name}</h3>
                </div>
                <p className="mt-2 text-xs text-muted h-8">{p.tagline}</p>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-ink">${price}</span>
                  <span className="text-sm text-muted">/mo</span>
                </div>
                {yearly && p.monthly > 0 && (
                  <p className="text-xs text-muted mt-1">billed ${price * 12}/year</p>
                )}
                <ul className="mt-4 space-y-2 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-body">
                      <Check size={15} className="text-emerald-600 mt-0.5 shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
                <button
                  disabled={isCurrent}
                  onClick={() => p.premium && setCheckout(p)}
                  className={`mt-5 w-full rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                    isCurrent
                      ? "bg-subtle text-muted cursor-default"
                      : p.highlight
                      ? "bg-brand-gradient text-white hover:opacity-90"
                      : "border border-border text-ink hover:bg-subtle"
                  }`}
                >
                  {isCurrent ? "Current plan" : p.id === "free" ? "Free forever" : `Choose ${p.name}`}
                </button>
              </div>
            );
          })}
        </div>

        <p className="text-center text-xs text-muted mt-8 flex items-center justify-center gap-1.5">
          <ShieldCheck size={13} /> Demo only — no real charge is made. This simulates a checkout flow.
        </p>
      </div>

      {checkout && (
        <CheckoutModal
          plan={checkout}
          yearly={yearly}
          onClose={() => setCheckout(null)}
          onSuccess={async () => {
            try {
              const p = await api.upgrade();     // REAL backend flip to premium (F2.9)
              setPlan(p);
              setCheckout(null);
              toast(`Welcome to ${checkout.name}! Your plan is now active.`, "success");
              router.push("/documents");
            } catch (err) {
              toast(err instanceof ApiError ? err.message : "Upgrade failed", "error");
            }
          }}
        />
      )}
    </AppLayout>
  );
}

/** Fake payment modal — collects card-looking fields, simulates processing,
 *  then calls onSuccess (which performs the real /account/upgrade). No data leaves
 *  the browser; nothing is charged. */
function CheckoutModal({
  plan, yearly, onClose, onSuccess,
}: {
  plan: Plan; yearly: boolean; onClose: () => void; onSuccess: () => void;
}) {
  const [card, setCard] = useState("");
  const [exp, setExp] = useState("");
  const [cvc, setCvc] = useState("");
  const [name, setName] = useState("");
  const [processing, setProcessing] = useState(false);
  const price = yearly ? plan.yearly * 12 : plan.monthly;
  const period = yearly ? "year" : "month";

  const valid = card.replace(/\s/g, "").length >= 12 && exp.length >= 4 && cvc.length >= 3 && name.trim().length > 1;

  function fmtCard(v: string) {
    return v.replace(/\D/g, "").slice(0, 16).replace(/(.{4})/g, "$1 ").trim();
  }
  function fmtExp(v: string) {
    const d = v.replace(/\D/g, "").slice(0, 4);
    return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
  }

  async function pay() {
    setProcessing(true);
    await new Promise((r) => setTimeout(r, 1400)); // simulate gateway
    onSuccess();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={() => !processing && onClose()} />
      <div className="relative w-full max-w-md rounded-2xl bg-surface border border-border shadow-card p-6 animate-fade-up">
        <button onClick={() => !processing && onClose()} className="absolute right-4 top-4 text-muted hover:text-ink"><X size={18} /></button>
        <div className="flex items-center gap-2 mb-1">
          <CreditCard size={20} className="text-brand-600" />
          <h3 className="font-semibold text-ink">Checkout — {plan.name}</h3>
        </div>
        <p className="text-sm text-body mb-4">
          You'll be charged <span className="font-semibold text-ink">${price}</span> per {period}.
        </p>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted">Cardholder name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe"
              className="mt-1 w-full rounded-xl border border-border bg-app px-3 py-2 text-sm text-ink outline-none focus:border-brand-400" />
          </div>
          <div>
            <label className="text-xs text-muted">Card number</label>
            <input value={card} onChange={(e) => setCard(fmtCard(e.target.value))} placeholder="4242 4242 4242 4242" inputMode="numeric"
              className="mt-1 w-full rounded-xl border border-border bg-app px-3 py-2 text-sm text-ink outline-none focus:border-brand-400 font-mono" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted">Expiry</label>
              <input value={exp} onChange={(e) => setExp(fmtExp(e.target.value))} placeholder="MM/YY" inputMode="numeric"
                className="mt-1 w-full rounded-xl border border-border bg-app px-3 py-2 text-sm text-ink outline-none focus:border-brand-400 font-mono" />
            </div>
            <div>
              <label className="text-xs text-muted">CVC</label>
              <input value={cvc} onChange={(e) => setCvc(e.target.value.replace(/\D/g, "").slice(0, 4))} placeholder="123" inputMode="numeric"
                className="mt-1 w-full rounded-xl border border-border bg-app px-3 py-2 text-sm text-ink outline-none focus:border-brand-400 font-mono" />
            </div>
          </div>
        </div>

        <button
          onClick={pay}
          disabled={!valid || processing}
          className="mt-5 w-full rounded-xl bg-brand-gradient text-white px-4 py-2.5 text-sm font-medium hover:opacity-90 disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {processing ? "Processing payment…" : <><Lock size={15} /> Pay ${price}</>}
        </button>
        <p className="text-center text-[11px] text-muted mt-3 flex items-center justify-center gap-1">
          <ShieldCheck size={11} /> Demo checkout — no real payment is processed. Try card 4242 4242 4242 4242.
        </p>
      </div>
    </div>
  );
}
