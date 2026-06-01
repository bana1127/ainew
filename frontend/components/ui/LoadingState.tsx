"use client";

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "불러오는 중..." }: LoadingStateProps) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-16">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-t-transparent"
        style={{ borderColor: "var(--border-soft)", borderTopColor: "var(--primary)" }} />
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>{message}</p>
    </div>
  );
}
