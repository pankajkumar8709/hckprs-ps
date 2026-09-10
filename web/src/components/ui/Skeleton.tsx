export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-lg ${className}`} />;
}

export function CardSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-2xl shadow-card p-5">
      <Skeleton className="h-10 w-10 rounded-xl" />
      <Skeleton className="h-4 w-3/4 mt-4" />
      <Skeleton className="h-3 w-1/2 mt-2" />
      <div className="flex gap-2 mt-4">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
    </div>
  );
}

export function StatSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-2xl shadow-card p-5">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-16 mt-3" />
      <Skeleton className="h-3 w-20 mt-3" />
    </div>
  );
}

export function RowSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-2xl shadow-card p-4 flex items-center gap-3">
      <Skeleton className="h-9 w-9 rounded-xl" />
      <div className="flex-1">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/4 mt-2" />
      </div>
    </div>
  );
}
