import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      <div className="h-14 w-14 rounded-2xl bg-brand-50 flex items-center justify-center text-brand-600">
        <Icon size={26} strokeWidth={1.75} />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-ink">{title}</h3>
      {description && (
        <p className="mt-1.5 text-sm text-body max-w-sm">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
