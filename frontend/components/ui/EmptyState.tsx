"use client";

import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  message?: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({
  message = "표시할 데이터가 없습니다.",
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl"
        style={{ background: "var(--border-soft)" }}>
        <Inbox className="h-5 w-5" style={{ color: "var(--text-muted)" }} />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium" style={{ color: "var(--text-main)" }}>{message}</p>
        {description && (
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{description}</p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
