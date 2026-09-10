type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

const tones: Record<Tone, string> = {
  neutral: "bg-subtle text-body border-border",
  brand: "bg-brand-50 text-brand-600 border-indigo-100",
  success: "bg-success-50 text-success border-green-200",
  warning: "bg-warning-50 text-warning border-amber-200",
  danger: "bg-danger-50 text-danger border-red-200",
};

export function StatusBadge({
  tone = "neutral",
  children,
  className = "",
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

// Map upload_status -> tone
export function statusTone(status: string): Tone {
  if (status === "done") return "success";
  if (status === "failed") return "danger";
  if (status === "processing" || status === "pending") return "warning";
  return "neutral";
}

// Map insight/reminder severity -> tone
export function severityTone(sev: string): Tone {
  if (sev === "high") return "danger";
  if (sev === "medium") return "warning";
  return "neutral";
}
